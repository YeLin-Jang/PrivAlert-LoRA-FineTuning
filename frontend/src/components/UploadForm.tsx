import React, { useState, useRef } from 'react';
import { analyzeContent } from '../api';
import type { AnalysisResult } from '../types';

export default function UploadForm() {
  const [files, setFiles] = useState<File[]>([]);
  const [text, setText] = useState('');
  const [blurFingers, setBlurFingers] = useState(true);
  const [showFaces, setShowFaces] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showResultModal, setShowResultModal] = useState(false);
  const [editorImageCount, setEditorImageCount] = useState(0);
  const editorRef = useRef<HTMLDivElement>(null);

  // 민감 정보 탐지 옵션
  const [detectionOptions, setDetectionOptions] = useState({
    face: true,           // 얼굴 (지원됨)
    fingerprint: true,    // 지문/손가락 (지원됨)
    religion: true,       // 종교 (지원됨)
    // 아래는 준비 중
    name: false,          // 이름
    address: false,       // 주소
    workplace: false,     // 직장
    school: false,        // 학교
    phone: false,         // 전화번호
    email: false,         // 이메일
    idNumber: false,      // 주민등록번호
    passport: false,      // 여권번호
    driverLicense: false, // 운전면허번호
    account: false,       // 계좌번호
    ipAddress: false,     // IP주소
    postalCode: false     // 우편번호
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const toggleDetectionOption = (option: keyof typeof detectionOptions) => {
    setDetectionOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }));
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const items = e.clipboardData.items;
    
    // HTML 형태의 복사 내용이 있는지 먼저 확인
    let hasHtml = false;
    let htmlContent = '';
    
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.type === 'text/html') {
        hasHtml = true;
        item.getAsString((html) => {
          htmlContent = html;
          processHtmlContent(htmlContent);
        });
        break;
      }
    }
    
    // HTML이 없으면 기존 방식으로 처리
    if (!hasHtml) {
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        
        if (item.type.indexOf('image') !== -1) {
          const file = item.getAsFile();
          if (file) {
            processImageFile(file);
          }
        } else if (item.type.indexOf('text') !== -1) {
          item.getAsString((text) => {
            processTextContent(text);
          });
        }
      }
    }
    
    // 붙여넣기 후 텍스트 업데이트
    setTimeout(() => {
      if (editorRef.current) {
        const textContent = editorRef.current.innerText;
        setText(textContent);
        const editorImages = editorRef.current.querySelectorAll('img').length;
        setEditorImageCount(editorImages);
      }
    }, 100);
  };

  const processHtmlContent = (html: string) => {
    if (!editorRef.current) return;
    
    // HTML을 파싱하여 텍스트와 이미지를 분리
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    // 이미지 태그들을 찾아서 처리
    const images = tempDiv.querySelectorAll('img');
    images.forEach((img, index) => {
      if (img.src.startsWith('data:')) {
        // Data URL을 File로 변환
        const base64Data = img.src.split(',')[1];
        const mimeType = img.src.split(',')[0].split(':')[1].split(';')[0];
        const byteCharacters = atob(base64Data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const file = new File([byteArray], `pasted-image-${index}.${mimeType.split('/')[1]}`, { type: mimeType });
        
        // 파일 목록에 추가
        setFiles(prev => [...prev, file]);
        
        // 이미지 스타일 적용
        img.style.maxWidth = '100%';
        img.style.height = 'auto';
        img.style.margin = '10px 0';
        img.style.borderRadius = '8px';
        img.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        img.style.display = 'block';
      }
    });
    
    // HTML 내용을 에디터에 삽입
    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      range.deleteContents();
      
      // HTML 노드들을 삽입
      while (tempDiv.firstChild) {
        range.insertNode(tempDiv.firstChild);
      }
      
      range.setStartAfter(range.endContainer);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
    } else {
      editorRef.current.appendChild(tempDiv);
    }
  };

  const processImageFile = (file: File) => {
    // 파일 목록에 추가
    setFiles(prev => [...prev, file]);
    
    // 에디터에 이미지 삽입
    const reader = new FileReader();
    reader.onload = (event) => {
      if (editorRef.current) {
        const img = document.createElement('img');
        img.src = event.target?.result as string;
        img.style.maxWidth = '100%';
        img.style.height = 'auto';
        img.style.margin = '10px 0';
        img.style.borderRadius = '8px';
        img.style.boxShadow = '0 2px 8px rgba(0,0,0,0.1)';
        img.style.display = 'block';
        
        // 커서 위치에 이미지 삽입
        const selection = window.getSelection();
        if (selection && selection.rangeCount > 0) {
          const range = selection.getRangeAt(0);
          range.deleteContents();
          range.insertNode(img);
          range.setStartAfter(img);
          range.collapse(true);
          selection.removeAllRanges();
          selection.addRange(range);
        } else {
          editorRef.current.appendChild(img);
        }
        
        // 줄바꿈 추가
        const br = document.createElement('br');
        if (selection && selection.rangeCount > 0) {
          const range = selection.getRangeAt(0);
          range.insertNode(br);
          range.setStartAfter(br);
          range.collapse(true);
          selection.removeAllRanges();
          selection.addRange(range);
        } else {
          editorRef.current.appendChild(br);
        }
      }
    };
    reader.readAsDataURL(file);
  };

  const processTextContent = (text: string) => {
    if (!editorRef.current) return;
    
    // 커서 위치에 텍스트 삽입
    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      range.deleteContents();
      
      // 텍스트를 HTML로 변환하여 서식 유지
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = text.replace(/\n/g, '<br>');
      
      // 텍스트 노드들을 삽입
      while (tempDiv.firstChild) {
        range.insertNode(tempDiv.firstChild);
      }
      
      range.setStartAfter(range.endContainer);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
    } else {
      // 텍스트를 HTML로 변환하여 서식 유지
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = text.replace(/\n/g, '<br>');
      editorRef.current.appendChild(tempDiv);
    }
  };

  const handleEditorInput = () => {
    if (editorRef.current) {
      const textContent = editorRef.current.innerText;
      setText(textContent);
      
      // 에디터의 이미지 개수 업데이트
      const editorImages = editorRef.current.querySelectorAll('img').length;
      setEditorImageCount(editorImages);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Ctrl+A: 전체 선택
    if (e.ctrlKey && e.key === 'a') {
      e.preventDefault();
      if (editorRef.current) {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(editorRef.current);
        selection?.removeAllRanges();
        selection?.addRange(range);
        
        // 선택된 내용을 시각적으로 표시
        editorRef.current.style.backgroundColor = '#f0f0f0';
        setTimeout(() => {
          if (editorRef.current) {
            editorRef.current.style.backgroundColor = '';
          }
        }, 200);
      }
    }
    
    // Ctrl+C: 복사 (개선된 복사 기능)
    if (e.ctrlKey && e.key === 'c') {
      if (editorRef.current) {
        const selection = window.getSelection();
        if (selection && selection.toString().length > 0) {
          // 선택된 내용이 있으면 브라우저 기본 복사 동작을 허용
          return;
        } else {
          // 선택된 내용이 없으면 전체 내용을 클립보드에 복사
          e.preventDefault();
          const range = document.createRange();
          range.selectNodeContents(editorRef.current);
          selection?.removeAllRanges();
          selection?.addRange(range);
          
          // 복사 실행
          document.execCommand('copy');
          
          // 선택 해제
          selection?.removeAllRanges();
        }
      }
    }
    
    // Ctrl+V: 붙여넣기 (이미 handlePaste에서 처리됨)
    if (e.ctrlKey && e.key === 'v') {
      // 브라우저 기본 붙여넣기 동작을 허용 (handlePaste에서 처리)
      return;
    }
  };

  const extractImagesFromEditor = (): File[] => {
    if (!editorRef.current) return [];
    
    const images = editorRef.current.querySelectorAll('img');
    const imageFiles: File[] = [];
    
    images.forEach((img, index) => {
      // 이미지가 로드되었는지 확인
      if (img.complete && img.naturalWidth > 0) {
        try {
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          if (ctx) {
            canvas.width = img.naturalWidth;
            canvas.height = img.naturalHeight;
            ctx.drawImage(img, 0, 0);
            
            canvas.toBlob((blob) => {
              if (blob) {
                const file = new File([blob], `pasted-image-${index}.png`, { type: 'image/png' });
                imageFiles.push(file);
              }
            }, 'image/png');
          }
        } catch (error) {
          console.warn('이미지 변환 중 오류:', error);
        }
      }
    });
    
    return imageFiles;
  };

  const handleAnalyze = async () => {
    if (!editorRef.current) {
      setError('에디터를 찾을 수 없습니다.');
      return;
    }

    // 에디터에서 텍스트 추출
    const editorText = editorRef.current.innerText || '';
    
    // 에디터에서 이미지 추출
    const editorImages = extractImagesFromEditor();
    
    // 모든 파일 합치기 (업로드된 파일 + 에디터의 이미지)
    const allFiles = [...files, ...editorImages];

    if (allFiles.length === 0 && !editorText.trim()) {
      setError('텍스트를 입력하거나 이미지를 붙여넣어주세요.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      console.log('분석 시작:', { allFiles: allFiles.length, editorText: editorText.length });
      const analysisResult = await analyzeContent(allFiles, editorText, blurFingers, showFaces);
      console.log('분석 결과:', analysisResult);
      setResult(analysisResult);
      setShowResultModal(true);
      console.log('모달 표시:', true);
    } catch (err) {
      console.error('분석 오류:', err);
      setError(err instanceof Error ? err.message : '분석 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setText('');
    setResult(null);
    setError(null);
    setShowResultModal(false);
    setBlurFingers(true);
    setShowFaces(true);
    setEditorImageCount(0);
    
    // 탐지 옵션 초기화
    setDetectionOptions({
      face: true,
      fingerprint: true,
      religion: true,
      name: false,
      address: false,
      workplace: false,
      school: false,
      phone: false,
      email: false,
      idNumber: false,
      passport: false,
      driverLicense: false,
      account: false,
      ipAddress: false,
      postalCode: false
    });
    
    // 에디터 초기화
    if (editorRef.current) {
      editorRef.current.innerHTML = '';
      editorRef.current.focus();
    }
  };

  return (
    <div className="container">
      <header className="header">
        <h1>PrivAlert</h1>
        <p className="subtitle">개인정보 보호 분석 시스템</p>
      </header>

      <main className="main-content">
        <div className="input-section">
          <div className="input-group">
            <label className="input-label">통합 분석 입력</label>
            <div className="document-editor">
              <div className="editor-toolbar">
                <div className="toolbar-group">
                  <button 
                    className="toolbar-button"
                    onClick={() => document.getElementById('file-upload')?.click()}
                    disabled={loading}
                    title="이미지 파일 추가"
                  >
                    📁 이미지 추가
                  </button>
                  <button 
                    className="toolbar-button"
                    onClick={() => editorRef.current?.focus()}
                    disabled={loading}
                    title="텍스트 입력"
                  >
                    ✏️ 텍스트 입력
                  </button>
                  <button 
                    className="toolbar-button"
                    onClick={() => {
                      if (editorRef.current) {
                        const selection = window.getSelection();
                        const range = document.createRange();
                        range.selectNodeContents(editorRef.current);
                        selection?.removeAllRanges();
                        selection?.addRange(range);
                      }
                    }}
                    disabled={loading}
                    title="전체 선택 (Ctrl+A)"
                  >
                    🔍 전체 선택
                  </button>
                </div>
              </div>
              
              <input
                type="file"
                multiple
                accept="image/*"
                onChange={handleFileChange}
                disabled={loading}
                className="file-input"
                id="file-upload"
              />
              
              <div className="editor-content">
                <div 
                  ref={editorRef}
                  className="rich-editor"
                  contentEditable
                  onPaste={handlePaste}
                  onInput={handleEditorInput}
                  onKeyDown={handleKeyDown}
                  onClick={() => editorRef.current?.focus()}
                  suppressContentEditableWarning={true}
                  data-placeholder="여기에 텍스트를 입력하거나 이미지를 붙여넣어주세요!"
                />
              </div>
              
              <div className="editor-footer">
                <div className="editor-stats">
                  <span className="text-counter">
                    글자 수: {editorRef.current?.innerText?.length || 0}/10000
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">민감 정보 탐지 옵션</label>
            <div className="options-grid">
              {/* 지원되는 기능들 */}
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.face}
                  onChange={() => toggleDetectionOption('face')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">얼굴</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.fingerprint}
                  onChange={() => toggleDetectionOption('fingerprint')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">지문/손가락</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.religion}
                  onChange={() => toggleDetectionOption('religion')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">종교</span>
              </label>
              
              {/* 준비 중인 기능들 */}
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.name}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">이름</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.address}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">주소/우편번호</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.workplace}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">직장 정보</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.school}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">학교 정보</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.phone}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">전화번호</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.email}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">이메일</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.idNumber}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">주민등록번호</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.passport}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">여권번호</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.driverLicense}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">운전면허번호</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.account}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">계좌번호</span>
              </label>
              <label className="option-item disabled">
                <input
                  type="checkbox"
                  checked={detectionOptions.ipAddress}
                  disabled={true}
                  className="option-checkbox"
                />
                <span className="option-text">IP주소</span>
              </label>
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">처리 옵션</label>
            <div className="options-grid">
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={blurFingers}
                  onChange={(e) => setBlurFingers(e.target.checked)}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">손가락 블러 처리</span>
                <span className="option-desc">감지된 손가락을 블러 처리합니다</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={showFaces}
                  onChange={(e) => setShowFaces(e.target.checked)}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">얼굴 상세 표시</span>
                <span className="option-desc">감지된 얼굴의 위치를 상세히 표시합니다</span>
              </label>
            </div>
          </div>
        </div>

        <div className="action-section">
          <button 
            onClick={handleAnalyze} 
            disabled={loading || (files.length === 0 && !text.trim())}
            className="analyze-button"
          >
            {loading ? (
              <>
                <div className="spinner"></div>
                분석 중...
              </>
            ) : (
              <>
                🔍 분석 시작
              </>
            )}
          </button>
          <button 
            onClick={handleReset} 
            disabled={loading}
            className="reset-button"
          >
            🗑️ 초기화
          </button>
        </div>
      </main>

      {/* 오류 메시지 */}
      {error && (
        <div className="error">
          <p>오류: {error}</p>
        </div>
      )}

      {/* 결과 모달 */}
      {showResultModal && result && (
        <div className="modal-overlay" onClick={() => setShowResultModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🔍 통합 분석 결과</h2>
              <button 
                className="modal-close"
                onClick={() => setShowResultModal(false)}
              >
                ✕
              </button>
            </div>
            
            <div className="modal-body">
              <div className="result-summary">
                <div className="summary-card">
                  <h3>📊 분석 요약</h3>
                  <div className="summary-stats">
                    <div className="stat-item">
                      <span className="stat-label">얼굴 감지</span>
                      <span className="stat-value">{result.summary.faces_detected}개</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">손가락 감지</span>
                      <span className="stat-value">{result.summary.fingers_detected}개</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">민감한 텍스트</span>
                      <span className={`stat-value ${result.summary.sensitive_text_found ? 'detected' : 'safe'}`}>
                        {result.summary.sensitive_text_found ? '발견됨' : '없음'}
                      </span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">종교적 내용</span>
                      <span className={`stat-value ${result.summary.religious_content_detected ? 'detected' : 'safe'}`}>
                        {result.summary.religious_content_detected ? '발견됨' : '없음'}
                      </span>
                    </div>
                  </div>
                  <div className="summary-message">
                    <p>{result.summary.message}</p>
                  </div>
                </div>

                {/* 텍스트 분석 결과 */}
                {result.text_analysis && (
                  <div className="text-analysis-card">
                    <h3>📝 텍스트 분석</h3>
                    <div className="text-content">
                      <div className="text-section">
                        <h4>원본 텍스트</h4>
                        <p className="text-preview">{result.text_analysis.original_text}</p>
                      </div>
                      <div className="text-section">
                        <h4>필터링된 텍스트</h4>
                        <p className="text-preview">{result.text_analysis.filtered_text}</p>
                      </div>
                      
                      {result.text_analysis.detected_words.length > 0 && (
                        <div className="detected-words-section">
                          <h4>🚨 감지된 민감 단어</h4>
                          <div className="words-list">
                            {result.text_analysis.detected_words.map((word, index) => (
                              <div key={index} className="word-item">
                                <span className="word-text">"{word.word}"</span>
                                <span className="word-religion">({word.religion})</span>
                                {word.replacement && (
                                  <span className="word-replacement">→ "{word.replacement}"</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 이미지 결과 */}
                {result.face_detection && result.face_detection.images.length > 0 && (
                  <div className="image-results-card">
                    <h3>👤 얼굴 감지 결과</h3>
                    <div className="image-results">
                      {result.face_detection.images.map((img, index) => (
                        <div key={index} className="image-result-item">
                          <p className="image-info">{img.filename}: {img.count}개 얼굴 감지</p>
                          {img.result_image_url && (
                            <img src={img.result_image_url} alt={`얼굴 감지 결과 ${index + 1}`} />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {result.hand_detection && result.hand_detection.images.length > 0 && (
                  <div className="image-results-card">
                    <h3>👋 손가락 감지 결과</h3>
                    <div className="image-results">
                      {result.hand_detection.images.map((img, index) => (
                        <div key={index} className="image-result-item">
                          <p className="image-info">{img.filename}: {img.count}개 손가락 감지</p>
                          {img.result_image_url && (
                            <img src={img.result_image_url} alt={`손가락 감지 결과 ${index + 1}`} />
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="modal-footer">
              <button 
                className="modal-button primary"
                onClick={() => setShowResultModal(false)}
              >
                확인
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
