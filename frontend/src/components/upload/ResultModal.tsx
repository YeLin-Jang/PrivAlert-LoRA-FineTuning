import React, { useState } from 'react';
import type { AnalysisResult } from '../../types';
import './ResultModal.css';

interface ResultModalProps {
  result: AnalysisResult & { video_analysis?: any };
  onClose: () => void;
  detectionOptions?: Record<string, boolean>;
  blurFingers?: boolean;
  onShowEducation?: (maskedText: string, categories: Record<string, any>) => void;
}

export const ResultModal: React.FC<ResultModalProps> = ({
  result,
  onClose,
  detectionOptions: _detectionOptions,
  onShowEducation,
}) => {
  const [showOriginal, setShowOriginal] = useState(false);

  // 텍스트 분석 결과
  const textAnalysis = result.text_analysis as (typeof result.text_analysis & {
    message?: string;
    source?: {
      direct_input: boolean;
      ocr: boolean;
      ocr_count: number;
    };
  }) | undefined;
  const structuredData = textAnalysis?.structured_data;
  const categories = structuredData?.categories || {};
  
  // 검출된 항목 카운트 계산
  const detectedCounts: Record<string, number> = {};
  let totalDetected = 0;
  
  Object.entries(categories).forEach(([key, value]: [string, any]) => {
    const count = value?.count || 0;
    detectedCounts[key] = count;
    totalDetected += count;
  });

  // 텍스트 하이라이트 함수 (간단한 구현)
  const highlightText = (text: string) => {
    if (!text || !structuredData) return text;
    
    // 마스킹된 텍스트를 사용하여 하이라이트
    const maskedText = textAnalysis?.masked_text || text;
    return maskedText.split(/(\[.*?\])/g).map((part, idx) => {
      if (part.startsWith('[') && part.endsWith(']')) {
        return <mark key={idx} className="highlight-yellow">{part}</mark>;
      }
      return part;
    });
  };

  // 카테고리 한국어 이름 매핑
  const categoryNames: Record<string, string> = {
    phone: '전화번호',
    rrn: '주민등록번호',
    email: '이메일',
    account: '계좌번호',
    school: '학교명',
    workplace: '직장명',
    name: '이름',
    address: '주소',
    passport: '여권번호',
    ip_address: 'IP주소',
  };

  // 이미지 분석 결과
  const faceImages = result.face_detection?.images || [];
  const handImages = result.hand_detection?.images || [];
  const sanitizedImages = result.image_sanitization?.items || [];
  
  // 모든 이미지 합치기 (최대 3개)
  // sanitizedImages, faceImages, handImages를 합쳐서 표시
  const allImages = [
    ...sanitizedImages.slice(0, 3),
  ];

  return (
    <div className="result-modal-overlay" onClick={onClose}>
      <div className="result-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="result-modal-header">
          <h1>PrivAlert</h1>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="result-modal-body">
          {/* 텍스트 분석 결과 */}
          {textAnalysis && (
            <section className="result-section text-analysis-section">
              <div className="section-header">
                <h2>텍스트 분석 결과</h2>
                <span className="detection-count">{totalDetected}개 검출</span>
              </div>

              {/* 텍스트가 없을 때 메시지 표시 */}
              {(!textAnalysis.original_text || textAnalysis.original_text.trim().length === 0) && textAnalysis.message ? (
                <div className="text-analysis-content">
                  <div className="no-text-message-box">
                    <p className="no-text-message">{textAnalysis.message}</p>
                    {textAnalysis.source && (
                      <div className="text-source-info">
                        {textAnalysis.source.ocr && (
                          <span className="source-tag">OCR: {textAnalysis.source.ocr_count}개 이미지 처리됨</span>
                        )}
                        {textAnalysis.source.direct_input && (
                          <span className="source-tag">직접 입력</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-analysis-content">
                  {/* 왼쪽: 검출 항목 요약 */}
                  <div className="detection-summary-box">
                    {Object.entries(detectedCounts).map(([key, count]) => (
                      <div key={key} className="detection-item">
                        <span className="detection-label">{categoryNames[key] || key}</span>
                        <span className="detection-value">{count}개</span>
                      </div>
                    ))}
                    {totalDetected === 0 && (
                      <div className="detection-item">
                        <span className="detection-label">검출된 항목 없음</span>
                      </div>
                    )}
                  </div>

                  {/* 중앙: 분석된 텍스트 */}
                  <div className="analyzed-text-box">
                    <div className="text-content">
                      {showOriginal 
                        ? textAnalysis.original_text 
                        : highlightText(textAnalysis.original_text || '')
                      }
                    </div>
                    {textAnalysis.source && (
                      <div className="text-source-info">
                        {textAnalysis.source.ocr && (
                          <span className="source-tag">OCR: {textAnalysis.source.ocr_count}개 이미지에서 추출</span>
                        )}
                        {textAnalysis.source.direct_input && (
                          <span className="source-tag">직접 입력</span>
                        )}
                      </div>
                    )}
                  </div>

                  {/* 오른쪽: 위험 레벨 범례 */}
                  <div className="risk-legend-box">
                    <div className="risk-level">
                      <div className="risk-circle very-dangerous"></div>
                      <span>ㅈㄴ 위험</span>
                    </div>
                    <div className="risk-level">
                      <div className="risk-circle dangerous"></div>
                      <span>위험</span>
                    </div>
                    <div className="risk-level">
                      <div className="risk-circle caution"></div>
                      <span>주의</span>
                    </div>
                  </div>
                </div>
              )}

              {/* 액션 버튼 - 텍스트가 있을 때만 표시 */}
              {textAnalysis.original_text && textAnalysis.original_text.trim().length > 0 && (
                <div className="text-action-buttons">
                  <button 
                    className="action-btn secondary"
                    onClick={() => setShowOriginal(!showOriginal)}
                  >
                    원본 보기
                  </button>
                  <button 
                    className="action-btn primary"
                    onClick={() => {
                      if (onShowEducation && textAnalysis.masked_text) {
                        onShowEducation(textAnalysis.masked_text, categories);
                      }
                    }}
                  >
                    전체 수정하기
                  </button>
                </div>
              )}
            </section>
          )}

          {/* 사진 분석 결과 */}
          {(faceImages.length > 0 || handImages.length > 0 || sanitizedImages.length > 0) && (
            <section className="result-section photo-analysis-section">
              <div className="section-header">
                <h2>사진 분석 결과</h2>
                <span className="detection-count">
                  {(result.summary?.faces_detected || 0) + (result.summary?.fingers_detected || 0)}개 검출
                </span>
              </div>

              <div className="photo-grid">
                {allImages.slice(0, 3).map((img: any, idx: number) => {
                  const faceImg = faceImages.find(f => f.image_index === (idx + 1));
                  const handImg = handImages.find(h => h.image_index === (idx + 1));
                  const detections = [];
                  
                  if (faceImg && faceImg.count && faceImg.count > 0) detections.push('얼굴');
                  if (handImg && handImg.count && handImg.count > 0) detections.push('지문정보');
                  if (structuredData?.detected) detections.push('주민등록');

                  return (
                    <div key={idx} className="photo-item">
                      <div className="photo-placeholder">
                        {img?.sanitized_url ? (
                          <img src={img.sanitized_url} alt={`이미지 ${idx + 1}`} />
                        ) : (
                          <span>이미지 {idx + 1}</span>
                        )}
                      </div>
                      <div className="photo-detections">
                        {detections.length > 0 ? (
                          detections.map((det, i) => (
                            <span key={i} className="detection-tag">{det}</span>
                          ))
                        ) : (
                          <span className="no-detection">검출 내역 없음</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {sanitizedImages.length > 0 && (
                <button className="download-all-button">
                  전체 수정사진 다운로드
                </button>
              )}
            </section>
          )}

          {/* 비디오 분석 결과 */}
          {result.video_analysis && (
            <section className="result-section video-analysis-section">
              <div className="section-header">
                <h2>영상 분석 결과</h2>
                <span className="detection-count">
                  {result.video_analysis.faces_detected + result.video_analysis.fingers_detected}개 검출
                </span>
              </div>
              
              <div className="video-summary">
                <div className="video-stats">
                  <div className="stat-item">
                    <span className="stat-label">총 프레임 분석</span>
                    <span className="stat-value">{result.video_analysis.total_frames_processed}개</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">얼굴 탐지</span>
                    <span className="stat-value">{result.video_analysis.faces_detected}개</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">손가락 탐지</span>
                    <span className="stat-value">{result.video_analysis.fingers_detected}개</span>
                  </div>
                </div>
                
                {result.video_analysis.audio_transcription?.text && (
                  <div className="video-audio-section">
                    <h3>음성 인식 텍스트</h3>
                    <div className="audio-text-content">
                      {result.video_analysis.audio_transcription.text}
                    </div>
                    
                    {result.video_analysis.audio_transcription.analysis && (
                      <div className="audio-analysis">
                        {result.video_analysis.audio_transcription.analysis.detected && (
                          <>
                            <div className="audio-detection-summary">
                              <span className="detection-badge">
                                {result.video_analysis.audio_transcription.analysis.total_count}개 검출
                              </span>
                            </div>
                            {result.video_analysis.audio_transcription.analysis.revised_text && (
                              <div className="audio-revised-text">
                                <h4>수정 제안:</h4>
                                <p>{result.video_analysis.audio_transcription.analysis.revised_text}</p>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* 교육 안내 */}
          {totalDetected > 0 && (
            <section className="result-section education-section">
              <div className="section-header">
                <h2>교육 안내</h2>
                <span className="detection-count">{totalDetected}개 검출</span>
              </div>
              <div className="education-keywords">
                {Object.entries(categories).map(([key]) => (
                  <span key={key} className="keyword-tag">키워드</span>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
};
