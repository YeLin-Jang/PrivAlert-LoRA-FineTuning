import React, { useState, useRef, useEffect } from 'react';
import { analyzeContent, analyzeVideo, suggestEducation } from '../services/api';
import type { AnalysisResult, SanitizedItem, DetectionOptions } from '../types';
import { validateTextLength, validateFileCount } from '../utils/validation';
import { UPLOAD_LIMITS, ERROR_MESSAGES, API_CONFIG } from '../constants';
import { DetectionOptionsPanel } from './DetectionOptionsPanel';
import { FileUploader } from './FileUploader';
import CommonHeader from './CommonHeader';
import { 
  secureFilesCleanup, 
  secureTextCleanup, 
  secureURLCleanup,
  secureLog 
} from '../utils/security';
import '../App.css';

export default function UploadForm() {
  const [files, setFiles] = useState<File[]>([]);
  const [text, setText] = useState('');
  const [blurFingers, setBlurFingers] = useState(false);
  const [showFaces, setShowFaces] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showResultModal, setShowResultModal] = useState(false);
  const [showEduPanel, setShowEduPanel] = useState(false);
  const [eduItems, setEduItems] = useState<any[] | null>(null);
  const [revisedSentence, setRevisedSentence] = useState<string | null>(null);
  const [eduLoading, setEduLoading] = useState(false);
  const editorRef = useRef<HTMLDivElement>(null);

  // 민감 정보 탐지 옵션 (초기 상태: 모두 비활성화)
  const [detectionOptions, setDetectionOptions] = useState<DetectionOptions>({
    face: false,
    fingerprint: false,
    phone: false,
    rrn: false,
    passport: false,
    ip_address: false,
    email: false,
    account: false,
    school: false,
    workplace: false,
    name: false,
    address: false,
  });

  // 비디오 파일 상태
  const [videoFile, setVideoFile] = useState<File | null>(null);
  
  // 보안: 컴포넌트 언마운트 시 민감 데이터 정리
  useEffect(() => {
    return () => {
      // 컴포넌트 언마운트 시 모든 민감 데이터 정리
      secureFilesCleanup([...files]);
      if (videoFile) {
        secureFilesCleanup([videoFile]);
      }
      // 결과 데이터도 정리
      if (result) {
        setResult(null);
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      
      // 파일 개수 검증
      const allFiles = [...files, ...newFiles];
      const countCheck = validateFileCount(allFiles);
      if (!countCheck.isValid) {
        setError(countCheck.error || ERROR_MESSAGES.TOO_MANY_FILES);
        return;
      }
      
      setFiles(prev => [...prev, ...newFiles]);
      
      // 선택된 파일들을 에디터에 표시
      newFiles.forEach((file) => {
        if (file.type.startsWith('image/')) {
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
        }
      });
      
      // 파일 입력 필드 초기화 (같은 파일을 다시 선택할 수 있도록)
      e.target.value = '';
    }
  };

  const toggleDetectionOption = (option: keyof DetectionOptions) => {
    setDetectionOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }));
  };

  // 모두 체크/해제 함수들
  const selectAllOptions = () => {
    setDetectionOptions(prev => {
      const newOptions = { ...prev };
      Object.keys(newOptions).forEach(key => {
        newOptions[key as keyof DetectionOptions] = true;
      });
      return newOptions;
    });
  };

  const deselectAllOptions = () => {
    setDetectionOptions(prev => {
      const newOptions = { ...prev };
      Object.keys(newOptions).forEach(key => {
        newOptions[key as keyof DetectionOptions] = false;
      });
      return newOptions;
    });
  };

  // 비디오 분석 핸들러
  const handleVideoAnalyze = async () => {
    if (!videoFile) {
      setError('비디오 파일을 선택해주세요.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const videoResult = await analyzeVideo(videoFile, true, true, 1.0);
      // 비디오 분석 결과를 통합 분석 결과 형식으로 변환
      const convertedResult: AnalysisResult = {
        summary: {
          faces_detected: videoResult.summary?.total_faces_detected || 0,
          fingers_detected: videoResult.summary?.total_fingers_detected || 0,
          sensitive_text_found: videoResult.summary?.frames_with_sensitive_content > 0 || false,
          message: `비디오 분석 완료: ${videoResult.summary?.total_frames_processed || 0}개 프레임 처리`,
        },
      };
      
      // 비디오 분석 결과를 별도로 저장
      (convertedResult as any).video_analysis = videoResult;
      setResult(convertedResult);
      setShowResultModal(true);
      
      // 보안: 분석 완료 후 원본 비디오 파일 메모리에서 정리
      secureFilesCleanup([videoFile]);
    } catch (err: any) {
      secureLog('비디오 분석 오류:', err);
      setError(err.message || ERROR_MESSAGES.SERVER_ERROR);
      
      // 오류 발생 시에도 민감 데이터 정리
      secureFilesCleanup([videoFile]);
    } finally {
      setLoading(false);
    }
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
    
    // 텍스트 길이 검증
    const textCheck = validateTextLength(editorText);
    if (!textCheck.isValid) {
      setError(textCheck.error || ERROR_MESSAGES.TEXT_TOO_LONG);
      return;
    }
    
    // 에디터에서 이미지 추출
    const editorImages = extractImagesFromEditor();
    
    // 모든 파일 합치기 (업로드된 파일 + 에디터의 이미지)
    const allFiles = [...files, ...editorImages];

    // 파일 개수 검증
    const countCheck = validateFileCount(allFiles);
    if (!countCheck.isValid) {
      setError(countCheck.error || ERROR_MESSAGES.TOO_MANY_FILES);
      return;
    }

    if (allFiles.length === 0 && !editorText.trim()) {
      setError('텍스트를 입력하거나 이미지를 붙여넣어주세요.');
      return;
    }
    
    // 최대 5개 제한
    const limitedFiles = allFiles.slice(0, UPLOAD_LIMITS.MAX_FILES);
    const limitedText = editorText.substring(0, UPLOAD_LIMITS.MAX_TEXT_LENGTH);

    setLoading(true);
    setError(null);

    try {
      secureLog('분석 시작:', { files: limitedFiles.length, text: limitedText.length });
      const analysisResult = await analyzeContent(limitedFiles, limitedText, blurFingers, showFaces, detectionOptions as DetectionOptions);
      
      // 보안: 분석 완료 후 원본 파일 메모리에서 정리
      // 분석이 성공적으로 완료되었으므로 원본 파일은 더 이상 필요하지 않음
      secureFilesCleanup([...limitedFiles]);
      
      setResult(analysisResult);
      setShowResultModal(true);
      // 교육 패널 자동 로딩 (마스킹 텍스트와 카테고리 기반)
      try {
        const masked = analysisResult?.text_analysis?.masked_text || '';
        const cats = (analysisResult as any)?.text_analysis?.structured_data?.categories || {};
        setEduLoading(true);
        const edu = await suggestEducation(masked, cats, 'ko', 'educational');
        setEduItems(edu?.items || []);
        setRevisedSentence(edu?.revised_sentence || null);
        setShowEduPanel(true);
      } catch (e) {
        secureLog('교육 제안 로딩 실패', e);
      } finally {
        setEduLoading(false);
      }
    } catch (err) {
      secureLog('분석 오류:', err);
      setError(err instanceof Error ? err.message : '분석 중 오류가 발생했습니다.');
      
      // 오류 발생 시에도 민감 데이터 정리
      secureFilesCleanup([...limitedFiles]);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    // 보안: 민감 데이터 명시적 정리
    secureFilesCleanup([...files]);
    if (videoFile) {
      secureFilesCleanup([videoFile]);
    }
    
    // 텍스트 데이터 정리
    const cleanedText = secureTextCleanup(text);
    
    setFiles([]);
    setText(cleanedText);
    setVideoFile(null);
    setResult(null);
    setError(null);
    setShowResultModal(false);
    setShowEduPanel(false);
    setEduItems(null);
    setRevisedSentence(null);
    setEduLoading(false);
    setBlurFingers(false);
    setShowFaces(false);
    
    // 탐지 옵션 초기화 (모두 비활성화)
    setDetectionOptions({
      face: false,
      fingerprint: false,
      phone: false,
      rrn: false,
      passport: false,
      ip_address: false,
      email: false,
      account: false,
      school: false,
      name: false,
      address: false,
      workplace: false
    });
    
    // 에디터 초기화
    if (editorRef.current) {
      editorRef.current.innerHTML = '';
      editorRef.current.focus();
    }
  };

  return (
    <div className="container">
      <CommonHeader />
      
      {/* 비디오 업로드 섹션 */}
      <section className="video-upload-section">
        <h2>🎬 비디오 분석</h2>
        <FileUploader
          files={videoFile ? [videoFile] : []}
          onFilesChange={(files) => setVideoFile(files[0] || null)}
          accept="video/*"
          multiple={false}
          maxFiles={1}
          isVideo={true}
        />
        {videoFile && (
          <button
            type="button"
            onClick={handleVideoAnalyze}
            disabled={loading}
            className="analyze-button"
          >
            {loading ? '분석 중...' : '비디오 분석 시작'}
          </button>
        )}
      </section>

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
                    글자 수: {editorRef.current?.innerText?.length || 0}/{UPLOAD_LIMITS.MAX_TEXT_LENGTH}
                  </span>
                  {files.length > 0 && (
                    <span className="file-counter">
                      파일: {files.length}/{UPLOAD_LIMITS.MAX_FILES}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="input-group">
            <DetectionOptionsPanel
              detectionOptions={detectionOptions}
              onToggle={toggleDetectionOption}
              onSelectAll={selectAllOptions}
              onDeselectAll={deselectAllOptions}
            />
            
            {/* 하위 옵션들 - 별도 섹션으로 분리 */}
            {(detectionOptions.face || detectionOptions.fingerprint) && (
              <div className="sub-options-section">
                <label className="input-label">처리 옵션</label>
                <div className="sub-options-grid">
                  {detectionOptions.face && (
                    <label className="option-item">
                      <input
                        type="checkbox"
                        checked={showFaces}
                        onChange={(e) => setShowFaces(e.target.checked)}
                        disabled={loading}
                        className="option-checkbox"
                      />
                      <span className="option-text">얼굴 감지 결과 표시</span>
                    </label>
                  )}
                  {detectionOptions.fingerprint && (
                    <label className="option-item">
                      <input
                        type="checkbox"
                        checked={blurFingers}
                        onChange={(e) => setBlurFingers(e.target.checked)}
                        disabled={loading}
                        className="option-checkbox"
                      />
                      <span className="option-text">손가락 감지 결과 표시</span>
                    </label>
                  )}
                </div>
              </div>
            )}
          </div>

        </div>

        <div className="action-section">
          <button 
                  onClick={handleAnalyze} 
            disabled={loading || (files.length === 0 && !text.trim() && !videoFile)}
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
              {/* 비디오 분석 결과 */}
              {(result as any).video_analysis && (
                <div className="video-analysis-card">
                  <h3>🎬 비디오 분석 결과</h3>
                  <div className="video-info">
                    <p><strong>비디오 정보:</strong></p>
                    <ul>
                      <li>해상도: {(result as any).video_analysis.video_info?.width} x {(result as any).video_analysis.video_info?.height}</li>
                      <li>길이: {((result as any).video_analysis.video_info?.duration || 0).toFixed(1)}초</li>
                      <li>FPS: {((result as any).video_analysis.video_info?.fps || 0).toFixed(1)}</li>
                      <li>처리된 프레임: {(result as any).video_analysis.summary?.total_frames_processed || 0}개</li>
                    </ul>
                  </div>
                  
                  {(result as any).video_analysis.audio_transcription && (
                    <div className="audio-transcription-section">
                      <h4>🎤 음성 인식 결과</h4>
                      <p className="transcription-text">
                        {(result as any).video_analysis.audio_transcription.text}
                      </p>
                      {(result as any).video_analysis.audio_text_analysis?.has_sensitive_content && (
                        <div className="sensitive-content-warning">
                          ⚠️ 음성 인식 텍스트에서 민감 정보가 감지되었습니다
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div className="video-summary-stats">
                    <div className="stat-item">
                      <span className="stat-label">감지된 얼굴</span>
                      <span className="stat-value">{(result as any).video_analysis.summary?.total_faces_detected || 0}개</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">감지된 손가락</span>
                      <span className="stat-value">{(result as any).video_analysis.summary?.total_fingers_detected || 0}개</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">민감 정보 포함 프레임</span>
                      <span className="stat-value">{(result as any).video_analysis.summary?.frames_with_sensitive_content || 0}개</span>
                    </div>
                  </div>
                  
                  {(result as any).video_analysis.frames && (result as any).video_analysis.frames.length > 0 && (
                    <div className="frames-section">
                      <h4>프레임별 분석 결과</h4>
                      <div className="frames-list">
                        {(result as any).video_analysis.frames.slice(0, 10).map((frame: any, idx: number) => (
                          <div key={idx} className="frame-item">
                            <p><strong>프레임 {frame.frame_index + 1}</strong> ({frame.timestamp.toFixed(1)}초)</p>
                            {frame.ocr && (
                              <p className="frame-ocr">OCR: {frame.ocr.text.substring(0, 50)}...</p>
                            )}
                            {frame.face && frame.face.count > 0 && (
                              <p className="frame-face">👤 얼굴 {frame.face.count}개</p>
                            )}
                            {frame.hand && frame.hand.count > 0 && (
                              <p className="frame-hand">👋 손가락 {frame.hand.count}개</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              <div className="result-summary">
                <div className="summary-card">
                  <h3>📊 분석 요약</h3>
                  <div className="summary-stats">
                    {detectionOptions.face && (
                    <div className="stat-item">
                      <span className="stat-label">얼굴 감지</span>
                      <span className="stat-value">{result.summary.faces_detected}개</span>
                    </div>
                    )}
                    {detectionOptions.fingerprint && (
                    <div className="stat-item">
                      <span className="stat-label">손가락 감지</span>
                      <span className="stat-value">{result.summary.fingers_detected}개</span>
                    </div>
                    )}
                    {detectionOptions.phone && (
                    <div className="stat-item">
                      <span className="stat-label">전화번호</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.phone?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.phone?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.rrn && (
                    <div className="stat-item">
                      <span className="stat-label">주민등록번호</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.rrn?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.rrn?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.passport && (
                    <div className="stat-item">
                      <span className="stat-label">여권번호</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.passport?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.passport?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.ip_address && (
                    <div className="stat-item">
                      <span className="stat-label">IP주소</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.ip_address?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.ip_address?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.email && (
                    <div className="stat-item">
                      <span className="stat-label">이메일</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.email?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.email?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.account && (
                    <div className="stat-item">
                      <span className="stat-label">계좌번호</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.account?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.account?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.school && (
                    <div className="stat-item">
                      <span className="stat-label">학교명</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.school?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.school?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.workplace && (
                    <div className="stat-item">
                      <span className="stat-label">직장명</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.workplace?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.workplace?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.name && (
                    <div className="stat-item">
                      <span className="stat-label">이름</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.name?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.name?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.address && (
                    <div className="stat-item">
                      <span className="stat-label">주소</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.address?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.address?.count || 0}개
                      </span>
                    </div>
                    )}
                  </div>
                </div>

                {/* OCR 텍스트 추출 결과 - 항상 표시 */}
                <div className="ocr-text-card">
                  <h3>🔍 추출된 텍스트 (OCR)</h3>
                  <div className="ocr-content">
                    {result.ocr_text && result.ocr_text.texts && result.ocr_text.texts.length > 0 ? (
                      <>
                        <p className="ocr-summary">{result.ocr_text.message}</p>
                        <div className="ocr-texts">
                          {result.ocr_text.texts.map((text, index) => (
                            <div key={index} className="ocr-text-item">
                              <h4>이미지 {index + 1}</h4>
                              <p className="ocr-text-content">{text}</p>
                            </div>
                          ))}
                        </div>
                      </>
                    ) : (
                      <p className="no-text-message">이미지에서 텍스트를 추출하지 못했습니다.</p>
                    )}
                  </div>
                </div>

                {/* EXIF/메타데이터 제거 결과 - 항상 표시 (있을 때) */}
                {result.image_sanitization && result.image_sanitization.items && result.image_sanitization.items.length > 0 && (
                  <div className="image-results-card">
                    <h3>🧹 EXIF/메타데이터 제거 결과</h3>
                    <p className="image-info">{result.image_sanitization.message}</p>
                    <div className="image-results">
                      {result.image_sanitization.items.map((it: SanitizedItem, idx: number) => (
                        <div key={idx} className="image-result-item">
                          <p className="image-info">{it.summary_ko || `${it.filename} 처리 완료`}</p>
                          <div className="result-actions">
                            <button
                              className="download-button"
                              onClick={async () => {
                                try {
                                  const API_BASE = API_CONFIG.BASE_URL;
                                  // 보안: 안전한 URL 생성
                                  const resolvedPath = (() => {
                                    if (!it.sanitized_url && it.sanitized_filename) {
                                      return `/data/image/${it.sanitized_filename}`;
                                    }
                                    if (!it.sanitized_url) return '';
                                    if (it.sanitized_url.startsWith('http')) {
                                      // 외부 URL 검증
                                      try {
                                        const url = new URL(it.sanitized_url);
                                        if (!['http:', 'https:'].includes(url.protocol)) {
                                          throw new Error('안전하지 않은 URL');
                                        }
                                        return it.sanitized_url;
                                      } catch {
                                        return '';
                                      }
                                    }
                                    if (it.sanitized_url.startsWith('/')) {
                                      return `${API_BASE}${it.sanitized_url}`;
                                    }
                                    return `${API_BASE}/data/image/${it.sanitized_url}`;
                                  })();
                                  if (!resolvedPath) throw new Error('다운로드 경로가 없습니다');
                                  
                                  // 보안: URL 검증
                                  const url = resolvedPath;
                                  if (!url.startsWith('http://') && !url.startsWith('https://') && !url.startsWith('/')) {
                                    throw new Error('안전하지 않은 URL');
                                  }
                                  const res = await fetch(url);
                                  if (!res.ok) throw new Error('다운로드 실패');
                                  const blob = await res.blob();
                                  const a = document.createElement('a');
                                  const ext = (it.report?.target_format || 'jpeg').toString().toLowerCase();
                                  const name = (it.sanitized_filename || `sanitized_${idx}.${ext === 'jpeg' ? 'jpg' : ext}`);
                                  const objectURL = URL.createObjectURL(blob);
                                  a.href = objectURL;
                                  a.download = name;
                                  document.body.appendChild(a);
                                  a.click();
                                  a.remove();
                                  // 보안: URL 즉시 해제
                                  secureURLCleanup(objectURL);
                                } catch (e) {
                                  console.error(e);
                                  alert('다운로드 중 오류가 발생했습니다.');
                                }
                              }}
                            >
                              ⬇️ 정제본 다운로드
                            </button>
                            {it.details_ko && (
                              <ul className="details-list">
                                {it.details_ko.exif && <li>EXIF: {it.details_ko.exif}</li>}
                                {it.details_ko.gps && <li>위치정보(GPS): {it.details_ko.gps}</li>}
                                {it.details_ko.format && <li>저장 포맷: {it.details_ko.format}</li>}
                                {it.details_ko.size && <li>최종 크기: {it.details_ko.size}</li>}
                              </ul>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 텍스트 분석 결과 - 항상 표시 */}
                {result.text_analysis && (
                  <div className="text-analysis-card">
                    <h3>📝 텍스트 분석 (OCR + 입력 텍스트 전체)</h3>
                    <div className="text-content">
                      {result.text_analysis.original_text ? (
                        <>
                          <div className="text-section">
                            <h4>원본 텍스트</h4>
                            <p className="text-preview">{result.text_analysis.original_text}</p>
                          </div>
                          
                          
                          {/* 정형 데이터 마스킹 결과가 원본과 다를 때만 표시 */}
                          {result.text_analysis.masked_text && result.text_analysis.masked_text !== result.text_analysis.original_text && (
                          <div className="text-section">
                            <h4>정형 데이터 마스킹된 텍스트</h4>
                            <p className="text-preview">{result.text_analysis.masked_text}</p>
                          </div>
                          )}
                        </>
                      ) : (
                        <div className="text-section">
                          <p className="no-text-message">텍스트를 발견하지 못했습니다</p>
                        </div>
                      )}
                      
                      
                      {/* 정형 데이터 탐지 결과 */}
                      {result.text_analysis.structured_data && result.text_analysis.structured_data.detected && (
                        <div className="structured-data-section">
                          <h4>📋 감지된 정형 데이터</h4>
                          <div className="structured-data-list">
                            {detectionOptions.phone && result.text_analysis.structured_data.categories.phone && (
                              <div className="category-item">
                                <h5 className="category-name">전화번호</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.phone.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.rrn && result.text_analysis.structured_data.categories.rrn && (
                              <div className="category-item">
                                <h5 className="category-name">주민등록번호</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.rrn.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.passport && result.text_analysis.structured_data.categories.passport && (
                              <div className="category-item">
                                <h5 className="category-name">여권번호</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.passport.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.ip_address && result.text_analysis.structured_data.categories.ip_address && (
                              <div className="category-item">
                                <h5 className="category-name">IP주소</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.ip_address.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.email && result.text_analysis.structured_data.categories.email && (
                              <div className="category-item">
                                <h5 className="category-name">이메일</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.email.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.account && result.text_analysis.structured_data.categories.account && (
                              <div className="category-item">
                                <h5 className="category-name">계좌번호</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.account.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.school && result.text_analysis.structured_data.categories.school && (
                              <div className="category-item">
                                <h5 className="category-name">학교명</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.school.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.workplace && result.text_analysis.structured_data.categories.workplace && (
                              <div className="category-item">
                                <h5 className="category-name">직장명</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.workplace.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                      {(item as any).score && (
                                        <span className="data-score">(신뢰도: {((item as any).score * 100).toFixed(1)}%)</span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.name && result.text_analysis.structured_data.categories.name && (
                              <div className="category-item">
                                <h5 className="category-name">이름</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.name.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[NAME]</span>
                                      <span className="data-value">"{(item as any).text}"</span>
                                      {(item as any).score && (
                                        <span className="data-score">(신뢰도: {((item as any).score * 100).toFixed(1)}%)</span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.address && result.text_analysis.structured_data.categories.address && (
                              <div className="category-item">
                                <h5 className="category-name">주소</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.address.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}


                {/* 얼굴 감지 결과 - 얼굴 감지 결과 표시 옵션이 체크되었을 때만 표시 */}
                {showFaces && result.face_detection && result.face_detection.images.length > 0 && (
                  <div className="image-results-card">
                    <h3>👤 얼굴 감지 결과</h3>
                    <div className="image-results">
                      {result.face_detection.images.map((img, index) => (
                        <div key={index} className="image-result-item">
                          <p className="image-info">{img.count}개 얼굴 감지</p>
                          {img.result_image_url && (
                            <div className="result-image-container">
                              <img 
                                src={`${API_CONFIG.BASE_URL}${img.result_image_url}`} 
                                alt={`얼굴 감지 결과 ${index + 1}`}
                                className="result-image"
                                onError={(e) => {
                                  console.error('이미지 로딩 실패:', img.result_image_url);
                                  e.currentTarget.style.display = 'none';
                                }}
                                onLoad={() => {
                                  console.log('이미지 로딩 성공:', img.result_image_url);
                                }}
                              />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 손가락 감지 결과 - 손가락 감지 결과 표시 옵션이 체크되었을 때만 표시 */}
                {blurFingers && result.hand_detection && result.hand_detection.images.length > 0 && (
                  <div className="image-results-card">
                    <h3>👋 손가락 감지 결과</h3>
                    <div className="image-results">
                      {result.hand_detection.images.map((img, index) => (
                        <div key={index} className="image-result-item">
                          <p className="image-info">{img.count}개 손가락 감지</p>
                          {img.result_image_url && (
                            <div className="result-image-container">
                              <img 
                                src={`${API_CONFIG.BASE_URL}${img.result_image_url}`} 
                                alt={`손가락 감지 결과 ${index + 1}`}
                                className="result-image"
                                onError={(e) => {
                                  console.error('이미지 로딩 실패:', img.result_image_url);
                                  e.currentTarget.style.display = 'none';
                                }}
                                onLoad={() => {
                                  console.log('이미지 로딩 성공:', img.result_image_url);
                                }}
                              />
                            </div>
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

      {/* 교육/수정 제안 사이드 패널 */}
      {showEduPanel && (
        <div className="side-panel">
          <div className="side-panel-header">
            <h3>🎓 교육/수정 제안</h3>
            <button className="side-close" onClick={() => setShowEduPanel(false)}>✕</button>
          </div>
          <div className="side-panel-body">
            {eduLoading && <p>생성 중...</p>}
            {!eduLoading && (!eduItems || eduItems.length === 0) && <p>제안 항목이 없습니다.</p>}
            {!eduLoading && eduItems && eduItems.length > 0 && (
              <div className="edu-list">
                {/* 수정 문장 - 맨 위에 한 번만 표시 */}
                {revisedSentence && (
                  <div className="edu-revised-section edu-revised-margin">
                    <div className="section-header">
                      <span className="section-icon">✏️</span>
                      <span className="section-title">수정 문장</span>
                    </div>
                    <div className="revised-sentence-box">
                      {revisedSentence}
                    </div>
                  </div>
                )}

                {eduItems.map((it, idx) => (
                  <div key={idx} className="edu-card">
                    {/* 카테고리 박스 */}
                    <div className="edu-section">
                      <div className="section-header">
                        <span className="section-icon">📋</span>
                        <span className="section-title">카테고리</span>
                      </div>
                      <div className="section-content">
                        {it.category}
                      </div>
                    </div>

                    {/* 법령 요약 박스 */}
                    <div className="edu-section">
                      <div className="section-header">
                        <span className="section-icon">⚖️</span>
                        <span className="section-title">법령 요약</span>
                      </div>
                      <div className="section-content">
                        {it.law_summary}
                      </div>
                    </div>

                    {/* 위험 시나리오 박스 */}
                    {it.risk_scenarios && it.risk_scenarios.length > 0 && (
                      <div className="edu-section">
                        <div className="section-header">
                          <span className="section-icon">⚠️</span>
                          <span className="section-title">위험 시나리오</span>
                        </div>
                        <div className="section-content">
                          <ul className="risk-list">
                            {it.risk_scenarios.map((r: string, i: number) => (
                              <li key={i} className="risk-item">• {r}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}

                    {/* 보안 팁 박스 */}
                    {it.tips && it.tips.length > 0 && (
                      <div className="edu-section">
                        <div className="section-header">
                          <span className="section-icon">💡</span>
                          <span className="section-title">보안 팁</span>
                        </div>
                        <div className="section-content">
                          <ul className="tips-list">
                            {it.tips.map((t: string, i: number) => (
                              <li key={i} className="tip-item">✅ {t}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
