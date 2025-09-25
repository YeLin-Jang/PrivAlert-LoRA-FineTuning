import { useState } from "react";
import { analyzeContent } from "@/api";

export default function UploadForm() {
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [imageFiles, setImageFiles] = useState<File[]>([]);
  const [text, setText] = useState("");
  const [blurFingers, setBlurFingers] = useState(true);
  const [showFaces, setShowFaces] = useState(false);
  const [showAnalysisPrompt, setShowAnalysisPrompt] = useState(false);
  const [showClearTextPrompt, setShowClearTextPrompt] = useState(false);
  const [contentEditableRef, setContentEditableRef] = useState<HTMLDivElement | null>(null);

  // 파일 삭제 함수
  const removeFile = (index: number) => {
    setImageFiles(prev => {
      const newFiles = prev.filter((_, i) => i !== index);
      
      // contentEditable 영역에서도 이미지 제거
      clearContentEditableImages();
      
      // 텍스트에 내용이 있으면 사용자에게 확인
      if (text.trim()) {
        setShowClearTextPrompt(true);
      }
      
      // 파일이 모두 삭제되고 텍스트도 없으면 프롬프트 숨김
      if (newFiles.length === 0 && !text.trim()) {
        setShowAnalysisPrompt(false);
      }
      return newFiles;
    });
  };

  // 모든 파일 삭제 함수
  const clearAllFiles = () => {
    setImageFiles([]);
    
    // contentEditable 영역에서도 이미지 제거
    clearContentEditableImages();
    
    // 텍스트에 내용이 있으면 사용자에게 확인
    if (text.trim()) {
      setShowClearTextPrompt(true);
    }
    
    // 파일이 모두 삭제되고 텍스트도 없으면 프롬프트 숨김
    if (!text.trim()) {
      setShowAnalysisPrompt(false);
    }
  };

  // 텍스트 초기화 확인 함수
  const handleClearTextConfirm = () => {
    setText("");
    setShowClearTextPrompt(false);
    setShowAnalysisPrompt(false);
    
    // contentEditable 영역도 초기화
    if (contentEditableRef) {
      contentEditableRef.innerHTML = "";
    }
  };

  // 텍스트 초기화 취소 함수
  const handleClearTextCancel = () => {
    setShowClearTextPrompt(false);
  };

  // contentEditable 영역에서 이미지 제거 함수
  const clearContentEditableImages = () => {
    if (contentEditableRef) {
      // 모든 img 태그 제거
      const images = contentEditableRef.querySelectorAll('img');
      images.forEach(img => img.remove());
      
      // 텍스트 내용 업데이트
      const textContent = contentEditableRef.textContent || "";
      setText(textContent);
    }
  };

  // 클립보드 붙여넣기 처리
  const handlePaste = async (e: React.ClipboardEvent) => {
    console.log("붙여넣기 이벤트 발생!");
    
    const items = e.clipboardData.items;
    console.log("클립보드 아이템 수:", items.length);
    
    const newImages: File[] = [];

    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      console.log(`아이템 ${i}:`, item.type);
      
      if (item.type.indexOf('image') !== -1) {
        // 이미지 파일 처리
        const file = item.getAsFile();
        if (file) {
          console.log("이미지 파일 발견:", file.name, file.size);
          newImages.push(file);
        }
      }
    }

    // 이미지만 별도로 관리
    if (newImages.length > 0) {
      setImageFiles(prev => [...prev, ...newImages]);
      setShowAnalysisPrompt(true);
    }

    // 텍스트는 contentEditable이 자동으로 처리하므로 별도 처리 불필요
    console.log("붙여넣기 완료 - 이미지:", newImages.length, "개");
  };


  async function handleAnalyze() {
    console.log("분석 시작 - 이미지:", imageFiles.length, "텍스트:", text.length);
    setLoading(true);
    setShowAnalysisPrompt(false); // 분석 시작 시 프롬프트 숨김
    try {
      // 모든 이미지를 분석
      const analysisResult = await analyzeContent(imageFiles, text, blurFingers, showFaces);
      console.log("분석 결과:", analysisResult);
      setResult(analysisResult);
    } catch (error: any) {
      console.error("분석 중 오류:", error);
      // 백엔드에서 반환된 에러 메시지 사용
      const errorMessage = error.response?.data?.error || "분석 중 오류가 발생했습니다";
      setResult({ success: false, error: errorMessage });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: "20px", maxWidth: "800px", margin: "0 auto" }}>
      <h2>PrivAlert - 개인정보 탐지 시스템</h2>
      
      {/* 통합 입력 폼 */}
      <div style={{ marginBottom: "20px" }}>
        <h3>📝 콘텐츠 입력</h3>
        <p style={{ 
          fontSize: "14px", 
          color: "#666", 
          marginBottom: "15px",
          fontStyle: "italic"
        }}>
          💡 <strong>Ctrl+V</strong>로 이미지와 텍스트를 한번에 붙여넣기 하세요!
        </p>
        
        {/* 간단한 텍스트 입력 영역 */}
        <div style={{ marginBottom: "20px" }}>
          <label style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
            📝 콘텐츠 입력 (텍스트 + 이미지)
          </label>
          <div
            ref={setContentEditableRef}
            contentEditable="true"
            suppressContentEditableWarning={true}
            onPaste={handlePaste}
            onInput={(e) => {
              const content = e.currentTarget.textContent || "";
              setText(content);
              if (content.trim()) {
                setShowAnalysisPrompt(true);
              }
            }}
            style={{
              width: "100%",
              minHeight: "200px",
              padding: "15px",
              border: "2px solid #ddd",
              borderRadius: "8px",
              fontSize: "14px",
              lineHeight: "1.5",
              outline: "none",
              backgroundColor: "#fff",
              resize: "vertical"
            }}
            placeholder="여기에 텍스트를 입력하거나 Ctrl+V로 이미지와 텍스트를 붙여넣으세요..."
          />
          <p style={{ margin: "5px 0 0 0", fontSize: "12px", color: "#666" }}>
            💡 한글, Word처럼 텍스트와 이미지를 함께 입력할 수 있습니다
          </p>
        </div>

        {/* 기존 입력 방식 (보조) */}
        <details style={{ marginBottom: "15px" }}>
          <summary style={{ cursor: "pointer", fontWeight: "bold", marginBottom: "10px" }}>
            📁 또는 파일 선택으로 입력하기
          </summary>
          
          {/* 이미지 업로드 */}
          <div style={{ marginBottom: "15px" }}>
            <label style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
              이미지 파일 추가 - 여러 장 선택 가능 (기존 파일에 추가됨)
            </label>
            <input 
              type="file" 
              accept="image/*"
              multiple
              onChange={(e) => {
                const newFiles = Array.from(e.target.files || []);
                setImageFiles(prev => [...prev, ...newFiles]);
                // 파일 입력 초기화 (같은 파일 다시 선택 가능하도록)
                e.target.value = '';
                // 분석 프롬프트 표시
                if (newFiles.length > 0) {
                  setShowAnalysisPrompt(true);
                }
              }}
              disabled={loading}
              style={{ 
                width: "100%", 
                padding: "8px", 
                border: "1px solid #ddd",
                borderRadius: "5px"
              }}
            />
          </div>

          {/* 텍스트 입력 */}
          <div style={{ marginBottom: "15px" }}>
            <label style={{ display: "block", marginBottom: "5px", fontWeight: "bold" }}>
              텍스트 입력
            </label>
            <textarea
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                // 텍스트 입력 시 분석 프롬프트 표시/숨김
                if (e.target.value.trim()) {
                  setShowAnalysisPrompt(true);
                } else if (imageFiles.length === 0) {
                  setShowAnalysisPrompt(false);
                }
              }}
              placeholder="분석할 텍스트를 입력하세요..."
              rows={4}
              style={{ 
                width: "100%", 
                padding: "8px", 
                border: "1px solid #ddd",
                borderRadius: "5px",
                resize: "vertical"
              }}
            />
          </div>
        </details>

        {/* 선택된 파일 표시 */}
        {imageFiles.length > 0 && (
          <div style={{ marginBottom: "15px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <p style={{ color: "green", fontSize: "14px", margin: "0" }}>
                ✅ 선택된 파일 ({imageFiles.length}개):
              </p>
              <button
                onClick={clearAllFiles}
                style={{
                  padding: "4px 8px",
                  fontSize: "12px",
                  backgroundColor: "#dc3545",
                  color: "white",
                  border: "none",
                  borderRadius: "3px",
                  cursor: "pointer"
                }}
              >
                모두 삭제
              </button>
            </div>
            <div style={{ 
              maxHeight: "150px", 
              overflowY: "auto", 
              border: "1px solid #eee", 
              padding: "10px",
              backgroundColor: "#f9f9f9",
              borderRadius: "5px"
            }}>
              {imageFiles.map((file, index) => (
                <div key={index} style={{ 
                  display: "flex", 
                  justifyContent: "space-between", 
                  alignItems: "center",
                  padding: "8px",
                  margin: "5px 0",
                  backgroundColor: "white",
                  border: "1px solid #ddd",
                  borderRadius: "3px"
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: "14px", fontWeight: "bold", marginBottom: "2px" }}>
                      {index + 1}. {file.name}
                    </div>
                    <div style={{ fontSize: "12px", color: "#666" }}>
                      {(file.size / 1024 / 1024).toFixed(2)}MB
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    style={{
                      padding: "4px 8px",
                      fontSize: "12px",
                      backgroundColor: "#ffc107",
                      color: "#212529",
                      border: "none",
                      borderRadius: "3px",
                      cursor: "pointer",
                      marginLeft: "10px"
                    }}
                    title="이 파일 삭제"
                  >
                    ✕ 삭제
                  </button>
                </div>
              ))}
            </div>
            {imageFiles.length > 1 && (
              <p style={{ color: "green", fontSize: "12px", margin: "5px 0" }}>
                ✅ {imageFiles.length}개 이미지 모두 분석됩니다!
              </p>
            )}
          </div>
        )}

        {/* 분석 프롬프트 */}
        {showAnalysisPrompt && (
          <div style={{
            padding: "15px",
            backgroundColor: "#fff3cd",
            border: "1px solid #ffeaa7",
            borderRadius: "8px",
            marginBottom: "15px",
            textAlign: "center"
          }}>
            <div style={{ fontSize: "20px", marginBottom: "8px" }}>✅</div>
            <p style={{ margin: "0 0 10px 0", fontWeight: "bold", color: "#856404" }}>
              붙여넣기 완료!
            </p>
            <p style={{ margin: "0", fontSize: "14px", color: "#856404" }}>
              아래 분석 버튼을 눌러서 분석을 시작하세요
            </p>
          </div>
        )}

        {/* 텍스트 초기화 확인 다이얼로그 */}
        {showClearTextPrompt && (
          <div style={{
            padding: "15px",
            backgroundColor: "#f8d7da",
            border: "1px solid #f5c6cb",
            borderRadius: "8px",
            marginBottom: "15px",
            textAlign: "center"
          }}>
            <div style={{ fontSize: "20px", marginBottom: "8px" }}>⚠️</div>
            <p style={{ margin: "0 0 10px 0", fontWeight: "bold", color: "#721c24" }}>
              파일을 삭제했습니다!
            </p>
            <p style={{ margin: "0 0 15px 0", fontSize: "14px", color: "#721c24" }}>
              텍스트 영역에 내용이 있습니다. 텍스트도 함께 초기화하시겠습니까?
            </p>
            <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
              <button
                onClick={handleClearTextConfirm}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#dc3545",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "14px"
                }}
              >
                네, 초기화
              </button>
              <button
                onClick={handleClearTextCancel}
                style={{
                  padding: "8px 16px",
                  backgroundColor: "#6c757d",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "14px"
                }}
              >
                아니오, 유지
              </button>
            </div>
          </div>
        )}

        {/* 분석 버튼 */}
        <button 
          onClick={handleAnalyze} 
          disabled={loading || (imageFiles.length === 0 && !text.trim())}
          style={{
            width: "100%",
            padding: "12px",
            backgroundColor: loading ? "#ccc" : (showAnalysisPrompt ? "#28a745" : "#007bff"),
            color: "white",
            border: "none",
            borderRadius: "5px",
            fontSize: "16px",
            cursor: loading ? "not-allowed" : "pointer",
            boxShadow: showAnalysisPrompt ? "0 2px 8px rgba(40, 167, 69, 0.3)" : "none",
            transform: showAnalysisPrompt ? "scale(1.02)" : "scale(1)",
            transition: "all 0.2s ease"
          }}
        >
          {loading ? "분석 중..." : (showAnalysisPrompt ? "🔍 분석 시작하기" : "🔍 통합 분석 시작")}
        </button>
        
        <p style={{ 
          fontSize: "12px", 
          color: "#666", 
          marginTop: "10px",
          textAlign: "center"
        }}>
          💡 이미지와 텍스트를 함께 입력하면 더 정확한 분석이 가능합니다
        </p>
      </div>

      {/* 옵션 설정 */}
      <div style={{ marginBottom: "20px" }}>
        <h3>분석 옵션</h3>
        <label>
          <input
            type="checkbox"
            checked={blurFingers}
            onChange={(e) => setBlurFingers(e.target.checked)}
          />
          손가락 블러 처리
        </label>
        <br />
        <label>
          <input
            type="checkbox"
            checked={showFaces}
            onChange={(e) => setShowFaces(e.target.checked)}
          />
          얼굴 상세 표시 (체크 해제시 개수만 표시)
        </label>
      </div>

      {/* 로딩 상태 */}
      {loading && <div>분석 중...</div>}

      {/* 결과 표시 */}
      {result && (
        <div style={{ marginTop: "20px" }}>
          <h3>분석 결과</h3>
          
          {result.success ? (
    <div>
              {/* 요약 */}
              <div style={{ 
                padding: "15px", 
                backgroundColor: "#f0f0f0", 
                borderRadius: "5px",
                marginBottom: "20px"
              }}>
                <h4>📊 요약</h4>
                <p>{result.summary?.message || "분석 완료"}</p>
                <ul>
                  <li>얼굴: {result.summary?.faces_detected || 0}개</li>
                  <li>손가락: {result.summary?.fingers_detected || 0}개</li>
                  <li>종교 관련 텍스트: {result.summary?.religious_content_detected ? "발견됨" : "없음"}</li>
                </ul>
              </div>

              {/* 좌우 분할 레이아웃 */}
              <div style={{ 
                display: "flex", 
                gap: "20px", 
                marginBottom: "20px",
                minHeight: "400px"
              }}>
                {/* 왼쪽: 분석 전 (원본 콘텐츠) */}
                <div style={{ 
                  flex: "1", 
                  padding: "20px", 
                  backgroundColor: "#f8f9fa", 
                  borderRadius: "8px",
                  border: "2px solid #e9ecef"
                }}>
                  <h4 style={{ margin: "0 0 15px 0", color: "#495057" }}>📝 분석 전</h4>
                  
                  {/* 입력된 콘텐츠 (텍스트 + 이미지 순서대로) */}
                  <div style={{ fontSize: "14px", lineHeight: "1.5" }}>
                    {text.split('\n').map((line, lineIndex) => (
                      <div key={lineIndex} style={{ marginBottom: "10px" }}>
                        {line}
                      </div>
                    ))}
                  </div>
                  
                  {/* 입력된 이미지들 */}
                  {imageFiles.length > 0 && (
                    <div style={{ marginTop: "15px" }}>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                        {imageFiles.map((file, index) => (
                          <div key={index} style={{ 
                            width: "150px", 
                            height: "150px", 
                            border: "2px solid #dee2e6",
                            borderRadius: "5px",
                            overflow: "hidden",
                            backgroundColor: "white"
                          }}>
                            <img 
                              src={URL.createObjectURL(file)}
                              alt={`원본 이미지 ${index + 1}`}
                              style={{ 
                                width: "100%", 
                                height: "100%", 
                                objectFit: "cover" 
                              }}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 오른쪽: 분석 후 (처리된 콘텐츠) */}
                <div style={{ 
                  flex: "1", 
                  padding: "20px", 
                  backgroundColor: "#fff", 
                  borderRadius: "8px",
                  border: "2px solid #007bff"
                }}>
                  <h4 style={{ margin: "0 0 15px 0", color: "#007bff" }}>🔍 분석 후</h4>
                  
                  {/* 필터링된 텍스트 (민감 단어 강조) */}
                  {result.text_analysis && (
                    <div style={{ marginBottom: "20px" }}>
                      <h5 style={{ margin: "0 0 10px 0", fontSize: "16px", color: "#495057" }}>📝 분석된 텍스트</h5>
                      <div style={{ 
                        padding: "15px", 
                        backgroundColor: "#fff3cd", 
                        border: "1px solid #ffeaa7",
                        borderRadius: "5px",
                        fontSize: "14px",
                        lineHeight: "1.5"
                      }}>
                        {result.text_analysis.detected_words && result.text_analysis.detected_words.length > 0 ? (
                          // 민감 단어가 있는 경우 강조 표시
                          (() => {
                            let text = result.text_analysis.original_text;
                            let highlightedText = [];
                            let lastIndex = 0;
                            
                            // 감지된 단어들을 위치 순으로 정렬
                            const sortedWords = result.text_analysis.detected_words.sort((a, b) => a.start - b.start);
                            
                            sortedWords.forEach((word, wordIndex) => {
                              // 원본 텍스트에서 해당 부분 찾기
                              const wordText = text.slice(word.start, word.end);
                              
                              // 감지된 단어 전 텍스트 추가
                              if (word.start > lastIndex) {
                                highlightedText.push(text.slice(lastIndex, word.start));
                              }
                              
                              // 감지된 단어 강조 표시
                              highlightedText.push(
                                <span 
                                  key={wordIndex}
                                  style={{
                                    backgroundColor: "#ff6b6b",
                                    color: "white",
                                    fontWeight: "bold",
                                    padding: "2px 4px",
                                    borderRadius: "3px"
                                  }}
                                >
                                  {wordText}
                                </span>
                              );
                              
                              lastIndex = word.end;
                            });
                            
                            // 남은 텍스트 추가
                            if (lastIndex < text.length) {
                              highlightedText.push(text.slice(lastIndex));
                            }
                            
                            return highlightedText;
                          })()
                        ) : (
                          // 민감 단어가 없는 경우 그대로 표시
                          result.text_analysis.original_text
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* 얼굴 검출 결과 */}
                  {result.face_detection && (
                    <div style={{ marginBottom: "20px" }}>
                      <h5 style={{ margin: "0 0 10px 0", fontSize: "16px", color: "#495057" }}>👤 얼굴 검출</h5>
                      <p style={{ margin: "0 0 10px 0", fontSize: "14px", color: "#6c757d" }}>{result.face_detection.message}</p>
                      
                      {/* 분석된 이미지들 */}
                      {result.face_detection.images && result.face_detection.images.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                          {result.face_detection.images.map((img: any, index: number) => (
                            <div key={index} style={{ 
                              width: "150px", 
                              height: "150px", 
                              border: "2px solid #007bff", 
                              borderRadius: "8px",
                              backgroundColor: "#f8f9ff",
                              overflow: "hidden",
                              position: "relative"
                            }}>
                              {img.result_image_url && (
                                <img 
                                  src={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}${img.result_image_url}`}
                                  alt={`얼굴 검출 결과 ${img.image_index}`}
                                  style={{ 
                                    width: "100%", 
                                    height: "100%", 
                                    objectFit: "cover"
                                  }}
                                />
                              )}
                              <div style={{ 
                                position: "absolute", 
                                bottom: "0", 
                                left: "0", 
                                right: "0", 
                                backgroundColor: "rgba(0, 123, 255, 0.8)", 
                                color: "white", 
                                padding: "5px", 
                                fontSize: "12px", 
                                textAlign: "center"
                              }}>
                                {img.count}개 얼굴
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 손가락 검출 결과 */}
                  {result.hand_detection && (
                    <div style={{ marginBottom: "20px" }}>
                      <h5 style={{ margin: "0 0 10px 0", fontSize: "16px", color: "#495057" }}>✋ 손가락 검출</h5>
                      <p style={{ margin: "0 0 10px 0", fontSize: "14px", color: "#6c757d" }}>{result.hand_detection.message}</p>
                      
                      {/* 분석된 이미지들 */}
                      {result.hand_detection.images && result.hand_detection.images.length > 0 && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
                          {result.hand_detection.images.map((img: any, index: number) => (
                            <div key={index} style={{ 
                              width: "150px", 
                              height: "150px", 
                              border: "2px solid #28a745", 
                              borderRadius: "8px",
                              backgroundColor: "#f8fff9",
                              overflow: "hidden",
                              position: "relative"
                            }}>
                              {img.result_image_url && (
                                <img 
                                  src={`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}${img.result_image_url}`}
                                  alt={`손가락 검출 결과 ${img.image_index}`}
                                  style={{ 
                                    width: "100%", 
                                    height: "100%", 
                                    objectFit: "cover"
                                  }}
                                />
                              )}
                              <div style={{ 
                                position: "absolute", 
                                bottom: "0", 
                                left: "0", 
                                right: "0", 
                                backgroundColor: "rgba(40, 167, 69, 0.8)", 
                                color: "white", 
                                padding: "5px", 
                                fontSize: "12px", 
                                textAlign: "center"
                              }}>
                                {img.count}개 손가락
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 민감 텍스트 경고 */}
                  {result.text_analysis && result.text_analysis.religious_content_detected && (
                    <div style={{ marginBottom: "20px" }}>
                      <div style={{ 
                        padding: "15px", 
                        backgroundColor: "#f8d7da", 
                        border: "1px solid #f5c6cb",
                        borderRadius: "5px",
                        color: "#721c24"
                      }}>
                        <div style={{ display: "flex", alignItems: "center", marginBottom: "10px" }}>
                          <span style={{ fontSize: "20px", marginRight: "8px" }}>⚠️</span>
                          <strong>종교 관련 민감 텍스트가 발견되었습니다!</strong>
                        </div>
                        <div style={{ fontSize: "14px" }}>
                          <strong>감지된 단어:</strong> {result.text_analysis.detected_words?.map((w: any) => w.word).join(", ")}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div style={{ color: "red" }}>
              오류: {result.error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
