import React, { useState } from 'react';
import type { AnalysisResult } from '../../types';
import './ResultModal.css';
import { EducationDetailModal } from './EducationDetailModal';

interface ResultModalProps {
  result: AnalysisResult & { video_analysis?: any };
  onClose: () => void;
  detectionOptions?: Record<string, boolean>;
  blurFingers?: boolean;
  onShowEducation?: (maskedText: string, categories: Record<string, any>) => void; // 전체 수정하기에서 사용하지 않음 (현재는 직접 수정 적용)
  eduItems?: any[] | null;
  revisedSentenceRationale?: string | null;
}

export const ResultModal: React.FC<ResultModalProps> = ({
  result,
  onClose,
  detectionOptions: _detectionOptions,
  onShowEducation: _onShowEducation,
  eduItems = null,
  revisedSentenceRationale = null,
}) => {
  // 디버깅: props 확인
  if (import.meta.env.DEV) {
    console.log('ResultModal props:', {
      hasEduItems: !!eduItems,
      eduItemsLength: eduItems?.length || 0,
      hasRevisedSentenceRationale: !!revisedSentenceRationale,
      revisedSentenceRationale,
    });
  }
  const [selectedParts, setSelectedParts] = useState<Record<number, string>>({}); // 각 부분별로 선택된 수정문장 저장
  const [isAllModified, setIsAllModified] = useState(false); // 전체 수정 여부
  const [hoveredPartIndex, setHoveredPartIndex] = useState<number | null>(null);
  const [fixedTooltipIndex, setFixedTooltipIndex] = useState<number | null>(null); // 고정된 툴팁 인덱스
  const [ignoredParts, setIgnoredParts] = useState<Set<number>>(new Set()); // 무시된 부분 (형광펜 제거)
  const [educationModalOpen, setEducationModalOpen] = useState(false);
  const [educationModalCategory, setEducationModalCategory] = useState<'rationale' | 'law' | 'risk' | 'tips' | 'all'>('rationale');
  const [educationModalData, setEducationModalData] = useState<any>(null);

  // 음성 인식 텍스트 하이라이트 함수
  const highlightAudioText = (text: string, audioCategories: Record<string, any>) => {
    if (!text || !audioCategories) return text;

    const parts: Array<{
      text: string;
      category?: string;
      riskLevel?: string;
      partIndex: number;
      startIndex: number;
      endIndex: number;
    }> = [];

    const allDetectedItems: Array<{
      value: string;
      category: string;
      startIndex: number;
      endIndex: number;
    }> = [];

    Object.entries(audioCategories).forEach(([catKey, catData]) => {
      const items = (catData as any)?.items || [];
      items.forEach((item: any) => {
        const value = item.value || '';
        if (value) {
          const index = text.indexOf(value);
          if (index !== -1) {
            allDetectedItems.push({
              value,
              category: catKey,
              startIndex: index,
              endIndex: index + value.length
            });
          }
        }
      });
    });

    allDetectedItems.sort((a, b) => a.startIndex - b.startIndex);

    const filteredItems: typeof allDetectedItems = [];
    let lastEndIndex = 0;
    allDetectedItems.forEach(item => {
      if (item.startIndex >= lastEndIndex) {
        filteredItems.push(item);
        lastEndIndex = item.endIndex;
      }
    });

    let partIndex = 0;
    let currentIndex = 0;

    filteredItems.forEach(item => {
      if (item.startIndex > currentIndex) {
        parts.push({
          text: text.substring(currentIndex, item.startIndex),
          partIndex: partIndex++,
          startIndex: currentIndex,
          endIndex: item.startIndex
        });
      }

      const riskLevel = getRiskLevel(item.category);
      parts.push({
        text: item.value,
        category: item.category,
        riskLevel,
        partIndex: partIndex++,
        startIndex: item.startIndex,
        endIndex: item.endIndex
      });

      currentIndex = item.endIndex;
    });

    if (currentIndex < text.length) {
      parts.push({
        text: text.substring(currentIndex),
        partIndex: partIndex++,
        startIndex: currentIndex,
        endIndex: text.length
      });
    }

    return parts.map((part, idx) => {
      if (part.category && part.riskLevel) {
        const revisedSuggestion = getGeneralizedText(part.category);
        const isHovered = hoveredPartIndex === part.partIndex;
        // 음성 인식 결과는 클릭 고정 없이 호버만 사용
        const showTooltip = isHovered;

        return (
          <span
            key={idx}
            className={`highlight-text highlight-${part.riskLevel}`}
            onMouseEnter={() => {
              setHoveredPartIndex(part.partIndex);
            }}
            onMouseLeave={() => {
              setHoveredPartIndex(null);
            }}
          >
            {part.text}
            {showTooltip && (
              <div className="text-revision-tooltip">
                <div className="tooltip-content">
                  <div className="tooltip-text-bubble problem-bubble">
                    <p className="tooltip-original">{part.text}</p>
                  </div>
                  <div className="tooltip-text-bubble revised-bubble">
                    <p className="tooltip-revised">{revisedSuggestion}</p>
                  </div>
                  {revisedSentenceRationale && (
                    <p className="tooltip-rationale">{revisedSentenceRationale}</p>
                  )}
                  {/* 음성 인식 결과는 수정 불가하므로 버튼 제거 */}
                </div>
              </div>
            )}
          </span>
        );
      }
      return <span key={idx}>{part.text}</span>;
    });
  };

  // 카테고리별 일반화된 표현 매핑
  const getGeneralizedText = (category: string): string => {
    const mappings: Record<string, string> = {
      phone: '연락처',
      rrn: '주민등록번호',
      email: '이메일',
      account: '계좌번호',
      school: '학교',
      workplace: '직장',
      name: '이름',
      address: '주소',
      passport: '여권번호',
      ip_address: 'IP주소',
    };
    return mappings[category] || '정보';
  };

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

  // 위험도별 색상 매핑
  const getRiskLevel = (category: string): 'very-dangerous' | 'dangerous' | 'caution' => {
    // 매우 위험: 주민등록번호, 계좌번호, 여권번호
    if (['rrn', 'account', 'passport'].includes(category)) return 'very-dangerous';
    // 위험: 전화번호, 이메일, 이름, 주소
    if (['phone', 'email', 'name', 'address'].includes(category)) return 'dangerous';
    // 주의: 나머지
    return 'caution';
  };

  // 텍스트 하이라이트 함수 (위험도별 색상 적용, 개별 수정 제안)
  const highlightText = (text: string) => {
    // 보안: 콘솔 로그 제거

    if (!text || !structuredData) {
      return text;
    }

    if (!categories || Object.keys(categories).length === 0) {
      return text;
    }

    // 원본 텍스트에서 직접 민감 정보 찾기
    const parts: Array<{
      text: string;
      category?: string;
      riskLevel?: string;
      originalValue?: string;
      partIndex: number;
      startIndex: number;
      endIndex: number;
    }> = [];

    // 모든 카테고리의 items를 수집하여 원본 텍스트에서 찾기
    const allDetectedItems: Array<{
      value: string;
      category: string;
      startIndex: number;
      endIndex: number;
    }> = [];

    Object.entries(categories).forEach(([catKey, catData]) => {
      const items = (catData as any)?.items || [];
      items.forEach((item: any) => {
        const value = item.value || '';
        if (value) {
          const index = text.indexOf(value);
          if (index !== -1) {
            allDetectedItems.push({
              value,
              category: catKey,
              startIndex: index,
              endIndex: index + value.length
            });
          }
        }
      });
    });

    // 시작 인덱스 순으로 정렬
    allDetectedItems.sort((a, b) => a.startIndex - b.startIndex);

    // 겹치는 부분 제거 (먼저 발견된 것 우선)
    const filteredItems: typeof allDetectedItems = [];
    let lastEndIndex = 0;
    allDetectedItems.forEach(item => {
      if (item.startIndex >= lastEndIndex) {
        filteredItems.push(item);
        lastEndIndex = item.endIndex;
      }
    });

    // 텍스트를 부분으로 나누기
    let partIndex = 0;
    let currentIndex = 0;

    filteredItems.forEach(item => {
      // 민감 정보 전 텍스트
      if (item.startIndex > currentIndex) {
        parts.push({
          text: text.substring(currentIndex, item.startIndex),
          partIndex: partIndex++,
          startIndex: currentIndex,
          endIndex: item.startIndex
        });
      }

      // 민감 정보
      const riskLevel = getRiskLevel(item.category);
      parts.push({
        text: item.value,
        category: item.category,
        riskLevel,
        originalValue: item.value,
        partIndex: partIndex++,
        startIndex: item.startIndex,
        endIndex: item.endIndex
      });

      currentIndex = item.endIndex;
    });

    // 나머지 텍스트
    if (currentIndex < text.length) {
      parts.push({
        text: text.substring(currentIndex),
        partIndex: partIndex++,
        startIndex: currentIndex,
        endIndex: text.length
      });
    }

    // 보안: 콘솔 로그 제거

    return parts.map((part, idx) => {
      // 선택된 수정문장이 있으면 해당 부분 교체 (형광펜 제거)
      if (selectedParts[part.partIndex]) {
        return <span key={idx}>{selectedParts[part.partIndex]}</span>;
      }

      // 무시된 부분은 형광펜 없이 표시
      if (ignoredParts.has(part.partIndex)) {
        return <span key={idx}>{part.text}</span>;
      }

      if (part.category && part.riskLevel) {
        // 보안: 콘솔 로그 제거
        const revisedSuggestion = getGeneralizedText(part.category);
        const isHovered = hoveredPartIndex === part.partIndex;
        const isFixed = fixedTooltipIndex === part.partIndex;
        // 고정된 툴팁이 있으면 (다른 부분이 고정되어 있으면) 이 부분의 툴팁은 표시하지 않음
        const hasFixedTooltip = fixedTooltipIndex !== null;
        const showTooltip = (isHovered || isFixed) && (!hasFixedTooltip || isFixed);
        
        return (
          <span
            key={idx}
            className={`highlight-text highlight-${part.riskLevel}`}
            onMouseEnter={() => {
              // 고정된 툴팁이 없을 때만 호버 표시
              if (fixedTooltipIndex === null) {
                setHoveredPartIndex(part.partIndex);
              }
            }}
            onMouseLeave={() => {
              // 고정된 툴팁이 없을 때만 호버 제거
              if (fixedTooltipIndex === null) {
                setHoveredPartIndex(null);
              }
            }}
            onClick={() => {
              // 클릭 시 툴팁 고정/해제
              if (isFixed) {
                setFixedTooltipIndex(null);
                setHoveredPartIndex(null);
              } else {
                setFixedTooltipIndex(part.partIndex);
                setHoveredPartIndex(part.partIndex);
              }
            }}
          >
            {part.text}
            {showTooltip && (
              <div className="text-revision-tooltip">
                <div className="tooltip-content">
                  <div className="tooltip-header">
                    <span className="tooltip-title">개인정보 검출 내역</span>
                    <span className="tooltip-chip">{categoryNames[part.category] ?? '개인정보'}</span>
                  </div>
                  <div className="tooltip-text-bubble problem-bubble">
                    <p className="tooltip-original">{part.text}</p>
                  </div>
                  <div className="tooltip-text-bubble revised-bubble">
                    <p className="tooltip-revised">{revisedSuggestion}</p>
                  </div>
                  {revisedSentenceRationale && (
                    <p className="tooltip-rationale">{revisedSentenceRationale}</p>
                  )}
                  <div className="tooltip-buttons right">
                    <button
                      className="tooltip-btn ignore"
                      onClick={(e) => {
                        e.stopPropagation();
                        // 무시하기: 형광펜 제거, 툴팁 닫기
                        setIgnoredParts(new Set([...ignoredParts, part.partIndex]));
                        setFixedTooltipIndex(null);
                        setHoveredPartIndex(null);
                      }}
                    >
                      무시하기
                    </button>
                    <button
                      className="tooltip-btn accept"
                      onClick={(e) => {
                        e.stopPropagation();
                        // 수정하기: 해당 부분 교체, 형광펜 제거, 툴팁 닫기
                        setSelectedParts({
                          ...selectedParts,
                          [part.partIndex]: revisedSuggestion
                        });
                        setFixedTooltipIndex(null);
                        setHoveredPartIndex(null);
                      }}
                    >
                      수정하기
                    </button>
                  </div>
                </div>
              </div>
            )}
          </span>
        );
      }
      return <span key={idx}>{part.text}</span>;
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
                      {highlightText(textAnalysis.original_text || '')}
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
                      <span>매우 위험</span>
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

              {/* 액션 버튼 - 전체 수정하기만 표시 */}
              {textAnalysis.original_text && textAnalysis.original_text.trim().length > 0 && (
              <div className="text-action-buttons">
                <button 
                  className="action-btn primary"
                  onClick={() => {
                      if (isAllModified) {
                        // 전체 복원: 모든 수정사항 제거
                        setSelectedParts({});
                        setIsAllModified(false);
                        setIgnoredParts(new Set());
                        setFixedTooltipIndex(null);
                        setHoveredPartIndex(null);
                      } else {
                        // 모든 탐지된 부분을 수정문장으로 교체
                        // highlightText와 동일한 로직으로 parts 계산
                        const originalText = textAnalysis.original_text || '';
                        const allDetectedItems: Array<{
                          value: string;
                          category: string;
                          startIndex: number;
                          endIndex: number;
                        }> = [];

                        Object.entries(categories).forEach(([catKey, catData]) => {
                          const items = (catData as any)?.items || [];
                          items.forEach((item: any) => {
                            const value = item.value || '';
                            if (value) {
                              const index = originalText.indexOf(value);
                              if (index !== -1) {
                                allDetectedItems.push({
                                  value,
                                  category: catKey,
                                  startIndex: index,
                                  endIndex: index + value.length
                                });
                              }
                            }
                          });
                        });

                        allDetectedItems.sort((a, b) => a.startIndex - b.startIndex);

                        const filteredItems: typeof allDetectedItems = [];
                        let lastEndIndex = 0;
                        allDetectedItems.forEach(item => {
                          if (item.startIndex >= lastEndIndex) {
                            filteredItems.push(item);
                            lastEndIndex = item.endIndex;
                          }
                        });

                        // highlightText와 동일한 방식으로 partIndex 계산
                        const parts: Array<{
                          text: string;
                          category?: string;
                          riskLevel?: string;
                          partIndex: number;
                          startIndex: number;
                          endIndex: number;
                        }> = [];

                        let partIndex = 0;
                        let currentIndex = 0;

                        filteredItems.forEach(item => {
                          if (item.startIndex > currentIndex) {
                            parts.push({
                              text: originalText.substring(currentIndex, item.startIndex),
                              partIndex: partIndex++,
                              startIndex: currentIndex,
                              endIndex: item.startIndex
                            });
                          }

                          const riskLevel = getRiskLevel(item.category);
                          parts.push({
                            text: item.value,
                            category: item.category,
                            riskLevel,
                            partIndex: partIndex++,
                            startIndex: item.startIndex,
                            endIndex: item.endIndex
                          });

                          currentIndex = item.endIndex;
                        });

                        if (currentIndex < originalText.length) {
                          parts.push({
                            text: originalText.substring(currentIndex),
                            partIndex: partIndex++,
                            startIndex: currentIndex,
                            endIndex: originalText.length
                          });
                        }

                        // 모든 민감 정보 부분을 수정문장으로 교체
                        const allParts: Record<number, string> = {};
                        parts.forEach(part => {
                          if (part.category && part.riskLevel) {
                            allParts[part.partIndex] = getGeneralizedText(part.category);
                          }
                        });

                        setSelectedParts(allParts);
                        setIsAllModified(true);
                      }
                    }}
                  >
                    {isAllModified ? '전체 복원하기' : '전체 수정하기'}
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
                  const detections: string[] = [];
                  
                  if (faceImg && faceImg.count && faceImg.count > 0) detections.push('얼굴');
                  if (handImg && handImg.count && handImg.count > 0) detections.push('지문정보');

                  // 텍스트 분석 결과에서 탐지된 항목 추가
                  if (structuredData?.detected && structuredData?.categories) {
                    const detectedCategories = Object.keys(structuredData.categories);
                    detectedCategories.forEach(cat => {
                      const catName = categoryNames[cat] || cat;
                      if (!detections.includes(catName)) {
                        detections.push(catName);
                      }
                    });
                  }

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
                          <div className="detection-alert">
                            <p className="detection-alert-text">
                              {detections.join(', ')}이(가) 탐지되었습니다.
                            </p>
                            <div className="detection-tags">
                              {detections.map((det, i) => (
                            <span key={i} className="detection-tag">{det}</span>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <span className="no-detection">검출 내역 없음</span>
                        )}
                      </div>
                      {img?.sanitized_url && (
                        <button
                          className="download-image-button"
                          onClick={() => {
                            // 이미지 다운로드
                            const link = document.createElement('a');
                            link.href = img.sanitized_url;
                            link.download = img.sanitized_filename || `sanitized_image_${idx + 1}.jpg`;
                            link.click();
                          }}
                        >
                          EXIF 제거 사진 다운로드
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>

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

                {/* 얼굴/손가락 탐지 시간 표시 */}
                {result.video_analysis.frames && result.video_analysis.frames.length > 0 && (
                  <div className="video-detection-times">
                    {result.video_analysis.faces_detected > 0 && (
                      <div className="detection-time-section">
                        <h4>얼굴 탐지 시간</h4>
                        <div className="time-list">
                          {result.video_analysis.frames
                            .filter((frame: any) => frame.face && frame.face.count > 0)
                            .slice(0, 10)
                            .map((frame: any, idx: number) => (
                              <span key={idx} className="time-tag">
                                {frame.timestamp?.toFixed(1) || frame.frame_index || idx}초
                              </span>
                            ))}
                        </div>
                      </div>
                    )}
                    {result.video_analysis.fingers_detected > 0 && (
                      <div className="detection-time-section">
                        <h4>손가락 탐지 시간</h4>
                        <div className="time-list">
                          {result.video_analysis.frames
                            .filter((frame: any) => frame.hand && frame.hand.count > 0)
                            .slice(0, 10)
                            .map((frame: any, idx: number) => (
                              <span key={idx} className="time-tag">
                                {frame.timestamp?.toFixed(1) || frame.frame_index || idx}초
                              </span>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {result.video_analysis.audio_transcription?.text && (
                  <div className="video-audio-section">
                    <h3>음성 인식 텍스트</h3>
                    <div className="audio-text-content">
                      {result.video_analysis.audio_transcription.analysis ?
                        highlightAudioText(
                          result.video_analysis.audio_transcription.text,
                          result.video_analysis.audio_transcription.analysis.categories || {}
                        ) :
                        result.video_analysis.audio_transcription.text
                      }
                    </div>

                    {result.video_analysis.audio_transcription.analysis && (
                      <div className="audio-analysis">
                        {result.video_analysis.audio_transcription.analysis.detected && (
                          <div className="audio-detection-summary">
                            <span className="detection-badge">
                              {result.video_analysis.audio_transcription.analysis.total_count}개 검출
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>
          )}

          {/* 교육 안내 - 탐지된 민감정보 항목별 카드 */}
          {totalDetected > 0 && ((eduItems && eduItems.length > 0) || revisedSentenceRationale) && (
            <section className="result-section education-section">
              <div className="section-header">
                <h2>교육 안내</h2>
                <span className="detection-count">{totalDetected}개 검출</span>
              </div>
              <div className="education-category-boxes">
                {/* 탐지된 각 카테고리별로 카드 생성 */}
                {Object.entries(categories).map(([catKey, _catData]) => {
                  const catName = categoryNames[catKey] || catKey;
                  // 해당 카테고리의 교육 데이터 찾기
                  const eduItem = eduItems?.find(item => {
                    // 카테고리 이름 매칭 (한국어 ↔ 영어)
                    const itemCategory = item.category;
                    return itemCategory === catName ||
                      (catKey === 'phone' && itemCategory === '전화번호') ||
                      (catKey === 'rrn' && itemCategory === '주민등록번호') ||
                      (catKey === 'email' && itemCategory === '이메일') ||
                      (catKey === 'account' && itemCategory === '계좌번호') ||
                      (catKey === 'name' && itemCategory === '이름') ||
                      (catKey === 'address' && itemCategory === '주소') ||
                      (catKey === 'school' && itemCategory === '학교명') ||
                      (catKey === 'workplace' && itemCategory === '직장명');
                  });

                  // eduItem이 없어도 카테고리 이름만 표시
                  return (
                    <div
                      key={catKey}
                      className="education-simple-card"
                      onClick={() => {
                        // 디버깅: 클릭 이벤트 확인
                        if (import.meta.env.DEV) {
                          console.log('교육 카드 클릭:', {
                            catName,
                            eduItem,
                            revisedSentenceRationale,
                            eduItems,
                          });
                        }
                        
                        // 카드 클릭 시 모든 정보를 포함한 모달 열기
                        const modalData: any = {
                          category: catName,
                        };
                        
                        if (eduItem) {
                          Object.assign(modalData, eduItem);
                        }
                        
                        if (revisedSentenceRationale) {
                          modalData.revised_sentence_rationale = revisedSentenceRationale;
                        }
                        
                        setEducationModalData(modalData);
                        setEducationModalCategory('all'); // 모든 정보 표시
                        setEducationModalOpen(true);
                        
                        // 디버깅: 모달 상태 확인
                        if (import.meta.env.DEV) {
                          console.log('모달 열기:', {
                            modalData,
                            category: 'all',
                          });
                        }
                      }}
                    >
                      <div className="simple-card-content">
                        {catName}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* 교육 상세 모달 */}
      <EducationDetailModal
        isOpen={educationModalOpen}
        onClose={() => setEducationModalOpen(false)}
        category={educationModalCategory}
        data={educationModalData || {}}
      />
    </div>
  );
};
