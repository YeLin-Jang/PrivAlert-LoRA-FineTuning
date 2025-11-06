import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { analyzeContent, suggestEducation } from '../../services/api';
import type { AnalysisResult, SanitizedItem, DetectionOptions, VideoAnalysisResult } from '../../types';
import { validateTextLength } from '../../utils/validation';
import { UPLOAD_LIMITS, ERROR_MESSAGES, API_CONFIG } from '../../constants';
import { DetectionOptionsPanel } from './DetectionOptionsPanel';
import { ResultModal } from './ResultModal';
import CommonHeader from '../common/CommonHeader';
import { useUserAuth } from '../../contexts/UserAuthContext';
import { userApi } from '../../services/userApi';
import { 
  secureFilesCleanup, 
  secureTextCleanup, 
  secureURLCleanup,
  secureLog 
} from '../../utils/security';
import './UploadForm.css';

export default function UploadForm() {
  const navigate = useNavigate();
  const { isAuthenticated, loading: authLoading } = useUserAuth();
  const [files, setFiles] = useState<File[]>([]);
  const [fileUrls, setFileUrls] = useState<string[]>([]); // blob URL 저장
  const [text, setText] = useState('');
  const [blurFingers, setBlurFingers] = useState(false);
  const [showFaces, setShowFaces] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<(AnalysisResult & { video_analysis?: VideoAnalysisResult }) | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showResultModal, setShowResultModal] = useState(false);
  const [showEduPanel, setShowEduPanel] = useState(false);
  interface EducationItem {
    category?: string;
    revised_sentence_rationale?: string;
    law_summary?: string;
    law_summary_rationale?: string;
    risk_scenarios?: string[];
    risk_scenarios_rationale?: string;
    tips?: string[];
    tips_rationale?: string;
    [key: string]: unknown;
  }
  const [eduItems, setEduItems] = useState<EducationItem[] | null>(null);
  const [revisedSentence, setRevisedSentence] = useState<string | null>(null);
  const [revisedSentenceRationale, setRevisedSentenceRationale] = useState<string | null>(null);
  const [eduLoading, setEduLoading] = useState(false);

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

  // 로그인 체크 - 분석 페이지는 로그인 필수
  useEffect(() => {
    // 인증 확인이 완료된 후에만 체크
    if (authLoading) {
      return; // 로딩 중이면 대기
    }
    
    // localStorage에 user_email이 있으면 로그인 상태로 간주 (세션 쿠키 확인 중일 수 있음)
    const storedEmail = localStorage.getItem('user_email');
    const isLoggedIn = isAuthenticated || !!storedEmail;
    
    if (!isLoggedIn) {
      // 로그인 안된 상태면 로그인 페이지로 리다이렉트
      navigate('/auth/login', { 
        replace: true,
        state: { 
          redirectTo: '/analyze',
          message: '분석 페이지는 로그인이 필요합니다.'
        } 
      });
    }
  }, [isAuthenticated, authLoading, navigate]);

  // 로그인된 사용자의 필터링 설정 로드
  useEffect(() => {
    // localStorage에 user_email이 있으면 로그인 상태로 간주
    const storedEmail = localStorage.getItem('user_email');
    const isLoggedIn = isAuthenticated || !!storedEmail;
    
    if (isLoggedIn) {
      const loadUserSettings = async () => {
        try {
          const settings = await userApi.getFilteringSettings();
          if (settings && settings.detection_options) {
            // DB에서 가져온 설정으로 완전히 교체 (merge가 아닌 교체)
            // 모든 옵션을 포함하여 설정 (DB에 없는 옵션은 false로 설정)
            const allOptions = ['face', 'fingerprint', 'phone', 'rrn', 'passport', 'ip_address', 
                               'email', 'account', 'school', 'workplace', 'name', 'address'];
            const newOptions: DetectionOptions = {} as DetectionOptions;
            allOptions.forEach(option => {
              newOptions[option as keyof DetectionOptions] = settings.detection_options[option] || false;
            });
            setDetectionOptions(newOptions);
            
            // 얼굴/손가락 탐지 옵션이 활성화되면 showFaces/blurFingers도 자동 활성화
            if (newOptions.face) {
              setShowFaces(true);
            }
            if (newOptions.fingerprint) {
              setBlurFingers(true);
            }
          }
        } catch {
          // 설정 로드 실패 시 기본값 유지
          // 보안: 콘솔 로그 제거
        }
      };
      loadUserSettings();
    }
  }, [isAuthenticated]);

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
      // blob URL 정리 (메모리 누수 방지)
      fileUrls.forEach(url => {
        if (url) {
          URL.revokeObjectURL(url);
        }
      });
      // 결과 데이터도 정리
      if (result) {
        setResult(null);
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files);
      
      // 파일 타입 검증 (이미지 또는 비디오만 허용)
      const validFiles = newFiles.filter(file => {
        const fileType = file.type;
        const isImage = fileType.startsWith('image/');
        const isVideo = fileType.startsWith('video/');
        return isImage || isVideo;
      });
      
      if (validFiles.length !== newFiles.length) {
        setError('이미지 또는 비디오 파일만 업로드할 수 있습니다.');
      }
      
      // 파일 개수 검증 (최대 5개)
      const allFiles = [...files, ...validFiles];
      if (allFiles.length > 5) {
        setError('이미지/영상 파일은 최대 5개까지 업로드할 수 있습니다.');
        e.target.value = '';
        return;
      }
      
      // blob URL 생성 (이미지 미리보기용)
      // files 배열과 동일한 인덱스로 매핑 (비디오는 null)
      const newUrls = validFiles.map(file => 
        file.type.startsWith('image/') ? URL.createObjectURL(file) : ''
      );
      
      setFiles(prev => [...prev, ...validFiles]);
      setFileUrls(prev => [...prev, ...newUrls]);
      e.target.value = '';
      setError(null);
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

  const handleAnalyze = async () => {
    // 텍스트 길이 검증
    const textCheck = validateTextLength(text);
    if (!textCheck.isValid) {
      setError(textCheck.error || ERROR_MESSAGES.TEXT_TOO_LONG);
      return;
    }
    
    // 파일 개수 검증
    if (files.length > 5) {
      setError('이미지/영상 파일은 최대 5개까지 업로드할 수 있습니다.');
      return;
    }

    if (files.length === 0 && !text.trim()) {
      setError('텍스트를 입력하거나 이미지/영상 파일을 업로드해주세요.');
      return;
    }
    
    // 최대 5개 제한
    const limitedFiles = files.slice(0, UPLOAD_LIMITS.MAX_FILES);
    const limitedText = text.substring(0, UPLOAD_LIMITS.MAX_TEXT_LENGTH);

    setLoading(true);
    setError(null);

    try {
      secureLog('분석 시작:', { files: limitedFiles.length, text: limitedText.length });
      const analysisResult = await analyzeContent(limitedFiles, limitedText, blurFingers, showFaces, detectionOptions as DetectionOptions);
      
      // 보안: 분석 완료 후 원본 파일 메모리에서 정리
      secureFilesCleanup([...limitedFiles]);
      
      setResult(analysisResult);
      setShowResultModal(true);
      
      // 보안: LLM 수정 문장 저장 (로그인한 사용자만, 민감 정보가 탐지되고 수정 문장이 있을 때만)
      // 보안: 로그인하지 않은 사용자는 수정 기록을 저장하지 않음
      if (isAuthenticated && !authLoading) {
        try {
          const revisedText = analysisResult?.text_analysis?.revised_text;
          const structuredData = analysisResult?.text_analysis?.structured_data;
          const detected = structuredData?.detected;
          const categories = structuredData?.categories || {};
          
          // 민감 정보가 탐지되고 수정 문장이 있고, 원본과 다른 경우에만 저장
          if (detected && revisedText && revisedText.trim() && 
              revisedText !== analysisResult?.text_analysis?.original_text) {
            // 카테고리 키 추출 (민감 정보 종류)
            const categoryKeys = Object.keys(categories).filter(key => 
              categories[key]?.count > 0
            );
            
            // 수정 기록 저장 (백그라운드에서 실행, 실패해도 사용자 경험에 영향 없음)
            // 보안: 민감 정보는 저장하지 않고 수정 문장만 저장
            // CSRF 토큰 갱신 후 저장 시도
            const saveRevisionHistory = async () => {
              try {
                // 먼저 CSRF 토큰 갱신 시도 (없거나 만료된 경우 대비)
                await userApi.getCurrentUser();
                // CSRF 토큰 갱신 후 저장
                await userApi.createRevisionHistory(revisedText, categoryKeys);
              } catch (error: unknown) {
                // 저장 실패는 조용히 처리 (사용자에게 알리지 않음)
                // 보안: 콘솔 로그 제거
                
                // 403 에러인 경우 한 번 더 CSRF 토큰 갱신 후 재시도
                interface ErrorWithResponse {
                  response?: { status?: number };
                }
                const axiosError = error as ErrorWithResponse;
                if (axiosError?.response?.status === 403) {
                  try {
                    // CSRF 토큰 갱신
                    await userApi.getCurrentUser();
                    // 재시도
                    await userApi.createRevisionHistory(revisedText, categoryKeys);
                  } catch {
                    // 재시도 실패해도 조용히 처리
                  }
                }
              }
            };
            
            // 백그라운드에서 실행 (await 하지 않음)
            saveRevisionHistory();
          }
        } catch {
          // 저장 중 오류는 조용히 처리
          // 보안: 콘솔 로그 제거
        }
      }
      
      // 교육 패널 자동 로딩 (마스킹 텍스트와 카테고리 기반)
      // 보안: text_analysis에 통합된 텍스트(직접 입력 + OCR)가 있고, 마스킹된 텍스트나 검출된 카테고리가 있을 때만 교육 제안 요청
      try {
        // text_analysis는 이제 직접 입력 텍스트와 OCR 결과가 통합되어 있음
        const masked = analysisResult?.text_analysis?.masked_text || '';
        const structuredData = analysisResult?.text_analysis?.structured_data;
        const cats = structuredData?.categories || {};
        
        // 텍스트나 검출된 카테고리가 있을 때만 교육 제안 요청
        const hasContent = masked.trim().length > 0 || Object.keys(cats).length > 0;
        
        if (hasContent) {
          setEduLoading(true);
          try {
            const edu = await suggestEducation(masked, cats, 'ko', 'educational');
            // 응답 데이터 검증
            if (edu && (edu.items || edu.revised_sentence)) {
              setEduItems(edu.items || []);
              setRevisedSentence(edu.revised_sentence || null);
              setRevisedSentenceRationale(edu.revised_sentence_rationale || null);
              // 자동으로 패널을 열지 않음 (사용자가 직접 열도록 함)
              // setShowEduPanel(true);
            } else {
              // 응답은 받았지만 데이터가 없음
              secureLog('교육 제안 데이터 없음', { edu });
              setShowEduPanel(false);
              setEduItems([]);
              setRevisedSentence(null);
              setRevisedSentenceRationale(null);
            }
          } catch (eduError: unknown) {
            // 에러 상세 정보 로깅
            interface ErrorWithResponse {
              message?: string;
              response?: { data?: unknown; status?: number };
            }
            const axiosError = eduError as ErrorWithResponse;
            secureLog('교육 제안 로딩 실패', {
              message: axiosError?.message,
              response: axiosError?.response?.data,
              status: axiosError?.response?.status,
            });
            setShowEduPanel(false);
            setEduItems([]);
            setRevisedSentence(null);
          }
        } else {
          // 텍스트나 검출된 항목이 없으면 교육 패널 숨김
          setShowEduPanel(false);
          setEduItems([]);
          setRevisedSentence(null);
        }
      } catch (e) {
        // 예상치 못한 오류
        secureLog('교육 제안 처리 중 오류', e);
        setShowEduPanel(false);
      } finally {
        setEduLoading(false);
      }
    } catch (err) {
      secureLog('분석 오류:', err);
      // 보안: 상세한 에러 정보는 사용자에게 노출하지 않음
      // 일반화된 사용자 친화적 메시지만 표시
      setError('분석 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
      
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
    
    // blob URL 정리
    fileUrls.forEach(url => {
      if (url) {
        URL.revokeObjectURL(url);
      }
    });
    
    setFiles([]);
    setFileUrls([]);
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
    
    // 파일 입력 초기화
    const fileInput = document.getElementById('file-upload') as HTMLInputElement;
    if (fileInput) {
      fileInput.value = '';
    }
  };

  const handleImageRemove = (index: number) => {
    // blob URL 정리 (이미지 파일인 경우만)
    if (fileUrls[index] && files[index]?.type.startsWith('image/')) {
      URL.revokeObjectURL(fileUrls[index]);
    }
    
    const newFiles = files.filter((_, i) => i !== index);
    const newUrls = fileUrls.filter((_, i) => i !== index);
    
    setFiles(newFiles);
    setFileUrls(newUrls);
    secureFilesCleanup([files[index]]);
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newText = e.target.value;
    if (newText.length <= UPLOAD_LIMITS.MAX_TEXT_LENGTH) {
      setText(newText);
    }
  };

  return (
    <div className="analyze-page">
      <CommonHeader />
      
      <main className="analyze-main-content">
        {/* 브랜딩 섹션 */}
        <div className="branding-section">
          <h1 className="brand-name">PrivAlert</h1>
          <p className="brand-subtitle">당신의 개인정보 보호 분석 시스템</p>
        </div>

        {/* 텍스트 입력 섹션 */}
        <div className="text-input-section">
          <h2 className="section-title">텍스트 분석 입력</h2>
          <div className="text-input-wrapper">
            <textarea
              className="text-input"
              placeholder="이곳에 텍스트를 입력하거나 붙여넣어주세요"
              value={text}
              onChange={handleTextChange}
              disabled={loading}
              maxLength={UPLOAD_LIMITS.MAX_TEXT_LENGTH}
            />
            <div className="text-counter">
              글자수: {text.length}/{UPLOAD_LIMITS.MAX_TEXT_LENGTH}
            </div>
          </div>
        </div>

        {/* 이미지/영상 추가 섹션 */}
        <div className="image-upload-section">
          <h2 className="section-title">이미지/영상 추가하기</h2>
          <div className="image-slots">
            {Array.from({ length: 5 }).map((_, index) => {
              const file = files[index];
              const isAddButton = index === files.length;
              
              return (
                <div
                  key={index}
                  className={`image-slot ${file ? 'has-image' : ''} ${isAddButton ? 'add-button' : ''}`}
                  onClick={() => {
                    if (isAddButton && files.length < 5) {
                      document.getElementById('file-upload')?.click();
                    }
                  }}
                >
                  {file ? (
                    <>
                      {file.type.startsWith('video/') ? (
                        <div className="video-preview">
                          <div className="video-icon">🎬</div>
                          <div className="video-filename">{file.name}</div>
                        </div>
                      ) : (
                        <img
                          src={fileUrls[index] || (file.type.startsWith('image/') ? URL.createObjectURL(file) : '')}
                          alt={`업로드 ${index + 1}`}
                          className="image-preview"
                          onError={(e) => {
                            // blob URL 로드 실패 시 대체 처리
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                          }}
                        />
                      )}
                      <button
                        className="image-remove"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleImageRemove(index);
                        }}
                        type="button"
                      >
                        ×
                      </button>
                    </>
                  ) : isAddButton ? (
                    <span className="add-icon">+</span>
                  ) : null}
                </div>
              );
            })}
          </div>
          <input
            type="file"
            id="file-upload"
            accept="image/*,video/*"
            multiple
            onChange={handleFileChange}
            style={{ display: 'none' }}
            disabled={loading || files.length >= 5}
          />
        </div>

        {/* 탐지 옵션 패널 (숨김 처리) */}
        <div className="detection-options-panel" style={{ display: 'none' }}>
          <DetectionOptionsPanel
            detectionOptions={detectionOptions}
            onToggle={toggleDetectionOption}
            onSelectAll={selectAllOptions}
            onDeselectAll={deselectAllOptions}
          />
          
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
                    />
                    <span>얼굴 감지 결과 표시</span>
                  </label>
                )}
                {detectionOptions.fingerprint && (
                  <label className="option-item">
                    <input
                      type="checkbox"
                      checked={blurFingers}
                      onChange={(e) => setBlurFingers(e.target.checked)}
                      disabled={loading}
                    />
                    <span>손가락 감지 결과 표시</span>
                  </label>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 액션 버튼 */}
        <div className="action-buttons">
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={loading || (files.length === 0 && !text.trim())}
            className="analyze-button"
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                분석 중...
              </>
            ) : (
              '분석 시작'
            )}
          </button>
          <button
            type="button"
            onClick={handleReset}
            disabled={loading}
            className="reset-button"
          >
            초기화
          </button>
        </div>

        {/* 오류 메시지 */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
      </main>

      {/* 결과 모달 */}
      {showResultModal && result && (
        <ResultModal
          result={result}
          onClose={() => setShowResultModal(false)}
          detectionOptions={detectionOptions}
          blurFingers={blurFingers}
          onShowEducation={(
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            _maskedText,
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            _categories
          ) => {
            // 교육 패널 표시 로직 (사용자가 직접 버튼을 클릭할 때만 열림)
            setShowEduPanel(true);
          }}
          eduItems={eduItems}
          revisedSentenceRationale={revisedSentenceRationale}
        />
      )}
      
      {/* 기존 결과 모달 (임시로 유지 - 나중에 제거) */}
      {/* eslint-disable-next-line no-constant-binary-expression */}
      {false && showResultModal && result && (
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
              {result?.video_analysis && (() => {
                const videoAnalysis = result!.video_analysis!;
                return (
                <div className="video-analysis-card">
                  <h3>🎬 비디오 분석 결과</h3>
                  <div className="video-info">
                    <p><strong>비디오 정보:</strong></p>
                    <ul>
                      <li>해상도: {videoAnalysis.video_info?.width} x {videoAnalysis.video_info?.height}</li>
                      <li>길이: {(videoAnalysis.video_info?.duration || 0).toFixed(1)}초</li>
                      <li>FPS: {(videoAnalysis.video_info?.fps || 0).toFixed(1)}</li>
                      <li>처리된 프레임: {videoAnalysis.summary?.total_frames_processed || 0}개</li>
                    </ul>
                  </div>
                  
                  {videoAnalysis.audio_transcription && (
                    <div className="audio-transcription-section">
                      <h4>🎤 음성 인식 결과</h4>
                      <p className="transcription-text">
                        {videoAnalysis.audio_transcription?.text}
                      </p>
                      {videoAnalysis.audio_text_analysis?.has_sensitive_content && (
                        <div className="sensitive-content-warning">
                          ⚠️ 음성 인식 텍스트에서 민감 정보가 감지되었습니다
                        </div>
                      )}
                    </div>
                  )}
                  
                  <div className="video-summary-stats">
                    <div className="stat-item">
                      <span className="stat-label">감지된 얼굴</span>
                      <span className="stat-value">{videoAnalysis.summary?.total_faces_detected || 0}개</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">감지된 손가락</span>
                      <span className="stat-value">{videoAnalysis.summary?.total_fingers_detected || 0}개</span>
                    </div>
                    <div className="stat-item">
                      <span className="stat-label">민감 정보 포함 프레임</span>
                      <span className="stat-value">{videoAnalysis.summary?.frames_with_sensitive_content || 0}개</span>
                    </div>
                  </div>
                  
                  {videoAnalysis.frames && videoAnalysis.frames.length > 0 && (
                    <div className="frames-section">
                      <h4>프레임별 분석 결과</h4>
                      <div className="frames-list">
                        {videoAnalysis.frames.slice(0, 10).map((frame: VideoAnalysisResult['frames'][number], idx: number) => (
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
                );
              })()}
              
              <div className="result-summary">
                <div className="summary-card">
                  <h3>📊 분석 요약</h3>
                  <div className="summary-stats">
                    {detectionOptions.face && (
                    <div className="stat-item">
                      <span className="stat-label">얼굴 감지</span>
                      <span className="stat-value">{result?.summary?.faces_detected || 0}개</span>
                    </div>
                    )}
                    {detectionOptions.fingerprint && (
                    <div className="stat-item">
                      <span className="stat-label">손가락 감지</span>
                      <span className="stat-value">{result?.summary?.fingers_detected || 0}개</span>
                    </div>
                    )}
                    {detectionOptions.phone && (
                    <div className="stat-item">
                      <span className="stat-label">전화번호</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.phone?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.phone?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.rrn && (
                    <div className="stat-item">
                      <span className="stat-label">주민등록번호</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.rrn?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.rrn?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.passport && (
                    <div className="stat-item">
                      <span className="stat-label">여권번호</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.passport?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.passport?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.ip_address && (
                    <div className="stat-item">
                      <span className="stat-label">IP주소</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.ip_address?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.ip_address?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.email && (
                    <div className="stat-item">
                      <span className="stat-label">이메일</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.email?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.email?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.account && (
                    <div className="stat-item">
                      <span className="stat-label">계좌번호</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.account?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.account?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.school && (
                    <div className="stat-item">
                      <span className="stat-label">학교명</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.school?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.school?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.workplace && (
                    <div className="stat-item">
                      <span className="stat-label">직장명</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.workplace?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.workplace?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.name && (
                    <div className="stat-item">
                      <span className="stat-label">이름</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.name?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.name?.count || 0}개
                      </span>
                    </div>
                    )}
                    {detectionOptions.address && (
                    <div className="stat-item">
                      <span className="stat-label">주소</span>
                      <span className={`stat-value ${(result?.text_analysis?.structured_data?.categories?.address?.count || 0) > 0 ? 'detected' : 'safe'}`}>
                        {result?.text_analysis?.structured_data?.categories?.address?.count || 0}개
                      </span>
                    </div>
                    )}
                  </div>
                </div>

                {/* OCR 텍스트 추출 결과 - 항상 표시 */}
                <div className="ocr-text-card">
                  <h3>🔍 추출된 텍스트 (OCR)</h3>
                  <div className="ocr-content">
                    {result?.ocr_text && result?.ocr_text?.texts && (result?.ocr_text?.texts?.length ?? 0) > 0 ? (
                      <>
                        <p className="ocr-summary">{result?.ocr_text?.message}</p>
                        <div className="ocr-texts">
                          {result?.ocr_text?.texts.map((text, index) => (
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
                {result?.image_sanitization && result?.image_sanitization?.items && (result?.image_sanitization?.items?.length ?? 0) > 0 && (
                  <div className="image-results-card">
                    <h3>🧹 EXIF/메타데이터 제거 결과</h3>
                    <p className="image-info">{result?.image_sanitization?.message}</p>
                    <div className="image-results">
                      {result?.image_sanitization?.items.map((it: SanitizedItem, idx: number) => (
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
                                } catch {
                                  // 보안: 콘솔 로그 제거
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
                {result?.text_analysis && (
                  <div className="text-analysis-card">
                    <h3>📝 텍스트 분석 (OCR + 입력 텍스트 전체)</h3>
                    <div className="text-content">
                      {result?.text_analysis?.original_text ? (
                        <>
                          <div className="text-section">
                            <h4>원본 텍스트</h4>
                            <p className="text-preview">{result?.text_analysis?.original_text}</p>
                          </div>
                          
                          
                          {/* 정형 데이터 마스킹 결과가 원본과 다를 때만 표시 */}
                          {result?.text_analysis?.masked_text && result?.text_analysis?.masked_text !== result?.text_analysis?.original_text && (
                          <div className="text-section">
                            <h4>정형 데이터 마스킹된 텍스트</h4>
                            <p className="text-preview">{result?.text_analysis?.masked_text}</p>
                          </div>
                          )}
                        </>
                      ) : (
                        <div className="text-section">
                          <p className="no-text-message">텍스트를 발견하지 못했습니다</p>
                        </div>
                      )}
                      
                      
                      {/* 정형 데이터 탐지 결과 */}
                      {result?.text_analysis?.structured_data && result?.text_analysis?.structured_data?.detected && (
                        <div className="structured-data-section">
                          <h4>📋 감지된 정형 데이터</h4>
                          <div className="structured-data-list">
                            {detectionOptions.phone && result?.text_analysis?.structured_data?.categories?.phone && (
                              <div className="category-item">
                                <h5 className="category-name">전화번호</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.phone?.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.rrn && result?.text_analysis?.structured_data?.categories?.rrn && (
                              <div className="category-item">
                                <h5 className="category-name">주민등록번호</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.rrn?.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.passport && result?.text_analysis?.structured_data?.categories?.passport && (
                              <div className="category-item">
                                <h5 className="category-name">여권번호</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.passport?.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.ip_address && result?.text_analysis?.structured_data?.categories?.ip_address && (
                              <div className="category-item">
                                <h5 className="category-name">IP주소</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.ip_address?.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.email && result?.text_analysis?.structured_data?.categories?.email && (
                              <div className="category-item">
                                <h5 className="category-name">이메일</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.email?.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.account && result?.text_analysis?.structured_data?.categories?.account && (
                              <div className="category-item">
                                <h5 className="category-name">계좌번호</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.account?.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.school && result?.text_analysis?.structured_data?.categories?.school && (
                              <div className="category-item">
                                <h5 className="category-name">학교명</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.school?.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.workplace && result?.text_analysis?.structured_data?.categories?.workplace && (
                              <div className="category-item">
                                <h5 className="category-name">직장명</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.workplace?.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[{item.type}]</span>
                                      <span className="data-value">"{item.value}"</span>
                                      {(item.score !== undefined) && (
                                        <span className="data-score">(신뢰도: {(item.score * 100).toFixed(1)}%)</span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.name && result?.text_analysis?.structured_data?.categories?.name && (
                              <div className="category-item">
                                <h5 className="category-name">이름</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.name?.items.map((item, index) => (
                                    <div key={index} className="data-item">
                                      <span className="data-type">[NAME]</span>
                                      <span className="data-value">"{item.text || item.value || ''}"</span>
                                      {(item.score !== undefined) && (
                                        <span className="data-score">(신뢰도: {(item.score * 100).toFixed(1)}%)</span>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {detectionOptions.address && result?.text_analysis?.structured_data?.categories?.address && (
                              <div className="category-item">
                                <h5 className="category-name">주소</h5>
                                <div className="category-items">
                                  {result?.text_analysis?.structured_data?.categories?.address?.items.map((item, index) => (
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
                {showFaces && result?.face_detection && result?.face_detection?.images && (result?.face_detection?.images?.length ?? 0) > 0 && (
                  <div className="image-results-card">
                    <h3>👤 얼굴 감지 결과</h3>
                    <div className="image-results">
                      {result?.face_detection?.images.map((img, index) => (
                        <div key={index} className="image-result-item">
                          <p className="image-info">{img.count}개 얼굴 감지</p>
                          {img.result_image_url && (
                            <div className="result-image-container">
                              <img 
                                src={`${API_CONFIG.BASE_URL}${img.result_image_url}`} 
                                alt={`얼굴 감지 결과 ${index + 1}`}
                                className="result-image"
                                onError={(e) => {
                                  // 보안: 이미지 URL은 민감 정보일 수 있으므로 로그 제거
                                  e.currentTarget.style.display = 'none';
                                }}
                                onLoad={() => {
                                  // 보안: 이미지 URL은 민감 정보일 수 있으므로 로그 제거
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
                {blurFingers && result?.hand_detection && result?.hand_detection?.images && (result?.hand_detection?.images?.length ?? 0) > 0 && (
                  <div className="image-results-card">
                    <h3>👋 손가락 감지 결과</h3>
                    <div className="image-results">
                      {result?.hand_detection?.images.map((img, index) => (
                        <div key={index} className="image-result-item">
                          <p className="image-info">{img.count}개 손가락 감지</p>
                          {img.result_image_url && (
                            <div className="result-image-container">
                              <img 
                                src={`${API_CONFIG.BASE_URL}${img.result_image_url}`} 
                                alt={`손가락 감지 결과 ${index + 1}`}
                                className="result-image"
                                onError={(e) => {
                                  // 보안: 이미지 URL은 민감 정보일 수 있으므로 로그 제거
                                  e.currentTarget.style.display = 'none';
                                }}
                                onLoad={() => {
                                  // 보안: 이미지 URL은 민감 정보일 수 있으므로 로그 제거
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
                        {it.law_summary || ''}
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

