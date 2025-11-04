import React, { useState, useRef } from 'react';
import { analyzeContent, suggestEducation } from '../api';
import type { AnalysisResult, SanitizedItem } from '../types';

export default function UploadForm() {
  const [files, setFiles] = useState<File[]>([]);
  const [text, setText] = useState('');
  const [blurFingers, setBlurFingers] = useState(true);
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
  const [detectionOptions, setDetectionOptions] = useState({
    face: false,          // 얼굴 (지원됨)
    fingerprint: false,   // 지문/손가락 (지원됨)
    // 정형 데이터 탐지 옵션들
    phone: false,         // 전화번호 (지원됨)
    rrn: false,           // 주민등록번호 (지원됨)
    passport: false,      // 여권번호 (지원됨)
    ip_address: false,    // IP주소 (지원됨)
    email: false,         // 이메일 (지원됨)
    account: false,       // 계좌번호 (지원됨)
    school: false,        // 학교명 (지원됨)
    // AI 기반 탐지 (지원됨)
    workplace: false,     // 직장명 (AI 모델 지원)
    // 비정형 데이터 (지원됨)
    name: false,          // 이름
    address: false,       // 주소 (지원됨)
    driverLicense: false, // 운전면허번호 (지원됨)
    postalCode: false     // 우편번호 (지원됨)
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
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

  const toggleDetectionOption = (option: keyof typeof detectionOptions) => {
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
        newOptions[key as keyof typeof newOptions] = true;
      });
      return newOptions;
    });
  };

  const deselectAllOptions = () => {
    setDetectionOptions(prev => {
      const newOptions = { ...prev };
      Object.keys(newOptions).forEach(key => {
        newOptions[key as keyof typeof newOptions] = false;
      });
      return newOptions;
    });
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
      console.log('분석 시작:', { allFiles: allFiles.length, editorText: editorText.length, detectionOptions });
      const analysisResult = await analyzeContent(allFiles, editorText, blurFingers, showFaces, detectionOptions);
      console.log('분석 결과:', analysisResult);
      
      // 얼굴 감지 결과 디버깅
      if (analysisResult.face_detection) {
        console.log('얼굴 감지 결과:', analysisResult.face_detection);
        analysisResult.face_detection.images.forEach((img, index) => {
          console.log(`얼굴 감지 이미지 ${index + 1}:`, {
            filename: img.filename,
            count: img.count,
            result_image_url: img.result_image_url,
            full_url: `http://localhost:5000${img.result_image_url}`
          });
        });
      }
      
      // 손가락 감지 결과 디버깅
      if (analysisResult.hand_detection) {
        console.log('손가락 감지 결과:', analysisResult.hand_detection);
        analysisResult.hand_detection.images.forEach((img, index) => {
          console.log(`손가락 감지 이미지 ${index + 1}:`, {
            filename: img.filename,
            count: img.count,
            result_image_url: img.result_image_url,
            full_url: `http://localhost:5000${img.result_image_url}`
          });
        });
      }
      
      // 처리 옵션 상태 디버깅
      console.log('처리 옵션 상태:', {
        showFaces,
        blurFingers,
        detectionOptions
      });
      
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
        console.warn('교육 제안 로딩 실패', e);
      } finally {
        setEduLoading(false);
      }
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
    setShowEduPanel(false);
    setEduItems(null);
    setRevisedSentence(null);
    setEduLoading(false);
    setBlurFingers(true);
    setShowFaces(true);
    
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
      workplace: false,
      driverLicense: false,
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
            <div className="option-controls">
              <button
                type="button"
                onClick={selectAllOptions}
                disabled={loading}
                className="option-button select-all"
              >
                모두 체크
              </button>
              <button
                type="button"
                onClick={deselectAllOptions}
                disabled={loading}
                className="option-button deselect-all"
              >
                모두 해제
              </button>
            </div>
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
              
              {/* 정형 데이터 탐지 옵션들 (지원됨) */}
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.phone}
                  onChange={() => toggleDetectionOption('phone')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">전화번호</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.rrn}
                  onChange={() => toggleDetectionOption('rrn')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">주민등록번호</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.passport}
                  onChange={() => toggleDetectionOption('passport')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">여권번호</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.ip_address}
                  onChange={() => toggleDetectionOption('ip_address')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">IP주소</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.email}
                  onChange={() => toggleDetectionOption('email')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">이메일</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.account}
                  onChange={() => toggleDetectionOption('account')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">계좌번호</span>
              </label>
              
              {/* AI 기반 탐지 옵션들 (지원됨) */}
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.workplace}
                  onChange={() => toggleDetectionOption('workplace')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">직장명</span>
              </label>
              
              {/* 비정형 데이터 탐지 옵션들 (지원됨) */}
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.name}
                  onChange={() => toggleDetectionOption('name')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">이름</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.address}
                  onChange={() => toggleDetectionOption('address')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">주소</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.school}
                  onChange={() => toggleDetectionOption('school')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">학교명</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.driverLicense}
                  onChange={() => toggleDetectionOption('driverLicense')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">운전면허번호</span>
              </label>
              <label className="option-item">
                <input
                  type="checkbox"
                  checked={detectionOptions.postalCode}
                  onChange={() => toggleDetectionOption('postalCode')}
                  disabled={loading}
                  className="option-checkbox"
                />
                <span className="option-text">우편번호</span>
              </label>
            </div>
            
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
                    {detectionOptions.driverLicense && (
                    <div className="stat-item">
                      <span className="stat-label">운전면허번호</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.driverLicense?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.driverLicense?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.postalCode && (
                    <div className="stat-item">
                      <span className="stat-label">우편번호</span>
                      <span className={`stat-value ${(result.text_analysis?.structured_data?.categories?.postalCode?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result.text_analysis?.structured_data?.categories?.postalCode?.count || 0}개
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
                                  const API_BASE = (import.meta as any).env?.VITE_API_BASE_URL || 'http://localhost:5000';
                                  const resolvedPath = (() => {
                                    if (!it.sanitized_url && it.sanitized_filename) {
                                      return `/data/image/${it.sanitized_filename}`;
                                    }
                                    if (!it.sanitized_url) return '';
                                    if (it.sanitized_url.startsWith('http')) return it.sanitized_url;
                                    if (it.sanitized_url.startsWith('/')) return `${API_BASE}${it.sanitized_url}`;
                                    return `${API_BASE}/data/image/${it.sanitized_url}`;
                                  })();
                                  if (!resolvedPath) throw new Error('다운로드 경로가 없습니다');
                                  const url = resolvedPath;
                                  const res = await fetch(url);
                                  if (!res.ok) throw new Error('다운로드 실패');
                                  const blob = await res.blob();
                                  const a = document.createElement('a');
                                  const ext = (it.report?.target_format || 'jpeg').toString().toLowerCase();
                                  const name = (it.sanitized_filename || `sanitized_${idx}.${ext === 'jpeg' ? 'jpg' : ext}`);
                                  a.href = URL.createObjectURL(blob);
                                  a.download = name;
                                  document.body.appendChild(a);
                                  a.click();
                                  a.remove();
                                  URL.revokeObjectURL(a.href);
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
                            {detectionOptions.driverLicense && result.text_analysis.structured_data.categories.driverLicense && (
                              <div className="category-item">
                                <h5 className="category-name">운전면허번호</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.driverLicense.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.postalCode && result.text_analysis.structured_data.categories.postalCode && (
                              <div className="category-item">
                                <h5 className="category-name">우편번호</h5>
                                <div className="category-items">
                                  {result.text_analysis.structured_data.categories.postalCode.items.map((item, index) => (
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
                                src={`http://localhost:5000${img.result_image_url}`} 
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
                                src={`http://localhost:5000${img.result_image_url}`} 
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
                  <div className="edu-revised-section" style={{ marginBottom: '20px' }}>
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
