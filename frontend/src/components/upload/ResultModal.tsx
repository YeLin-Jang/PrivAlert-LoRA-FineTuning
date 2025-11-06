import React, { useState } from 'react';
import type { AnalysisResult, VideoAnalysisResult, FaceImage, HandImage, SanitizedItem } from '../../types';
import './ResultModal.css';
import { EducationDetailModal } from './EducationDetailModal';
import { API_CONFIG } from '../../constants';

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

interface ResultModalProps {
  result: AnalysisResult & { video_analysis?: VideoAnalysisResult };
  onClose: () => void;
  detectionOptions?: Record<string, boolean>;
  blurFingers?: boolean;
  onShowEducation?: (maskedText: string, categories: Record<string, unknown>) => void; // 전체 수정하기에서 사용하지 않음 (현재는 직접 수정 적용)
  eduItems?: EducationItem[] | null;
  revisedSentenceRationale?: string | null;
}

export const ResultModal: React.FC<ResultModalProps> = ({
  result,
  onClose,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  detectionOptions: _detectionOptions,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onShowEducation: _onShowEducation,
  eduItems = null,
  revisedSentenceRationale = null,
}) => {
  // 보안: 콘솔 로그 제거
  const [selectedParts, setSelectedParts] = useState<Record<number, string>>({}); // 각 부분별로 선택된 수정문장 저장
  const [isAllModified, setIsAllModified] = useState(false); // 전체 수정 여부
  const [hoveredPartIndex, setHoveredPartIndex] = useState<number | null>(null);
  const [fixedTooltipIndex, setFixedTooltipIndex] = useState<number | null>(null); // 고정된 툴팁 인덱스
  const [ignoredParts, setIgnoredParts] = useState<Set<number>>(new Set()); // 무시된 부분 (형광펜 제거)
  const [educationModalOpen, setEducationModalOpen] = useState(false);
  const [educationModalCategory, setEducationModalCategory] = useState<'rationale' | 'law' | 'risk' | 'tips' | 'all'>('rationale');
  const [educationModalData, setEducationModalData] = useState<EducationItem | null>(null);

  // 구조화된 데이터 항목 타입
  interface StructuredDataItem {
    type: string;
    value: string;
    category: string;
  }

  interface CategoryData {
    items?: StructuredDataItem[];
    count?: number;
  }

  // 음성 인식 텍스트 하이라이트 함수
  const highlightAudioText = (text: string, audioCategories: Record<string, CategoryData>) => {
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
      const categoryData = catData as CategoryData;
      const items = categoryData?.items || [];
      items.forEach((item: StructuredDataItem) => {
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
  
  Object.entries(categories).forEach(([key, value]) => {
    const categoryData = value as CategoryData;
    const count = categoryData?.count || 0;
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
      const categoryData = catData as CategoryData;
      const items = categoryData?.items || [];
      items.forEach((item: StructuredDataItem) => {
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
  
  // 표시용 이미지: 얼굴/손가락 탐지 결과 이미지만 (탐지 후 표시된 이미지)
  // 다운로드용: EXIF 제거 이미지 (별도로 관리)
  interface DisplayImage {
    image_index: number;
    filename: string;
    display_url: string;
    detection_type: 'face' | 'hand';
    [key: string]: unknown;
  }
  
  const displayImages: DisplayImage[] = [];
  
  // 얼굴 탐지 결과 이미지 추가 (표시용)
  faceImages.forEach((img: FaceImage) => {
    if (img.result_image_url && displayImages.length < 3) {
      displayImages.push({
        ...img,
        display_url: img.result_image_url, // 표시용 URL
        detection_type: 'face'
      });
    }
  });
  
  // 손가락 탐지 결과 이미지 추가 (표시용, 같은 image_index가 없을 때만)
  handImages.forEach((img: HandImage) => {
    if (img.result_image_url && displayImages.length < 3) {
      if (!displayImages.find((existing: DisplayImage) => existing.image_index === img.image_index)) {
        displayImages.push({
          ...img,
          display_url: img.result_image_url, // 표시용 URL
          detection_type: 'hand'
        });
      }
    }
  });

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
                          const categoryData = catData as CategoryData;
                          const items = categoryData?.items || [];
                          items.forEach((item: StructuredDataItem) => {
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
                {displayImages.length > 0 ? (
                  displayImages.map((img: DisplayImage, idx: number) => {
                    // 이미지의 image_index를 기준으로 탐지 정보 찾기
                    const imageIndex = img.image_index || (idx + 1);
                    const faceImg = faceImages.find(f => f.image_index === imageIndex);
                    const handImg = handImages.find(h => h.image_index === imageIndex);
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

                    // 같은 image_index의 EXIF 제거 이미지 찾기 (다운로드용)
                    const sanitizedImg = Array.isArray(sanitizedImages) 
                      ? sanitizedImages.find((s: SanitizedItem) => s.image_index === imageIndex)
                      : null;

                    return (
                      <div key={idx} className="photo-item">
                        <div className="photo-placeholder">
                          {img?.display_url ? (
                            <img 
                              src={`${API_CONFIG.BASE_URL}${img.display_url}?t=${Date.now()}`} 
                              alt={`이미지 ${imageIndex}`}
                              onError={(e) => {
                                // 이미지 로드 실패 시 대체 처리
                                const target = e.target as HTMLImageElement;
                                target.style.display = 'none';
                                const placeholder = target.parentElement;
                                if (placeholder) {
                                  const span = document.createElement('span');
                                  span.textContent = `이미지 ${imageIndex}`;
                                  placeholder.appendChild(span);
                                }
                              }}
                            />
                          ) : (
                            <span>이미지 {imageIndex}</span>
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
                        {sanitizedImg?.sanitized_url && (
                          <button
                            className="download-image-button"
                            onClick={async () => {
                              try {
                                // 보안: API 엔드포인트를 통한 프록시 다운로드 (파일 경로 노출 방지)
                                // sanitized_url 형식: /data/results/image/sanitized_xxx.png
                                // 백엔드의 /api/v1/analyze/download/<path:filename> 엔드포인트 사용
                                // 파일 경로를 URL에 노출하지 않고 백엔드에서 프록시로 전송
                                let urlPath = sanitizedImg.sanitized_url;
                                
                                // /data/results/로 시작하는 경우 제거 (백엔드에서 BASE_DATA_DIR과 결합)
                                if (urlPath.startsWith('/data/results/')) {
                                  urlPath = urlPath.replace('/data/results/', '');
                                }
                                
                                // Flask의 <path:filename>은 슬래시를 포함한 경로를 받을 수 있으므로
                                // 각 경로 세그먼트만 인코딩 (슬래시는 유지)
                                const pathSegments = urlPath.split('/');
                                const encodedSegments = pathSegments.map(segment => encodeURIComponent(segment));
                                const encodedPath = encodedSegments.join('/');
                                const downloadUrl = `${API_CONFIG.BASE_URL}/api/v1/analyze/download/${encodedPath}`;
                                
                                const response = await fetch(downloadUrl, {
                                  credentials: 'include', // 쿠키 포함
                                  method: 'GET',
                                  cache: 'no-cache', // 304 에러 방지
                                });
                                
                                if (!response.ok) {
                                  // 보안: 상세한 에러 정보는 사용자에게 노출하지 않음
                                  if (response.status === 404) {
                                    throw new Error('FILE_NOT_FOUND');
                                  } else if (response.status === 403) {
                                    throw new Error('ACCESS_DENIED');
                                  } else {
                                    throw new Error('DOWNLOAD_FAILED');
                                  }
                                }
                                
                                const blob = await response.blob();
                                const url = window.URL.createObjectURL(blob);
                                
                                // 파일명 생성 (확장자 포함)
                                const filename = sanitizedImg.sanitized_filename || `sanitized_image_${imageIndex}.jpg`;
                                
                                const link = document.createElement('a');
                                link.href = url;
                                link.download = filename;
                                document.body.appendChild(link);
                                link.click();
                                
                                // 정리
                                document.body.removeChild(link);
                                window.URL.revokeObjectURL(url);
                              } catch (error: unknown) {
                                // 보안: 일반화된 사용자 친화적 메시지만 표시
                                let message = '다운로드 중 오류가 발생했습니다.';
                                const errorMessage = error instanceof Error ? error.message : '';
                                if (errorMessage === 'FILE_NOT_FOUND') {
                                  message = '파일을 찾을 수 없습니다. 이미 삭제되었을 수 있습니다.';
                                } else if (errorMessage === 'ACCESS_DENIED') {
                                  message = '파일 다운로드 권한이 없습니다.';
                                } else if (errorMessage === 'DOWNLOAD_FAILED') {
                                  message = '파일 다운로드에 실패했습니다. 잠시 후 다시 시도해주세요.';
                                }
                                alert(message);
                              }
                            }}
                          >
                            EXIF 제거 사진 다운로드
                          </button>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="no-images-message" style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '40px', color: '#666' }}>
                    이미지가 없습니다. 텍스트 분석 결과만 표시됩니다.
                  </div>
                )}
              </div>

            </section>
          )}

          {/* 비디오 분석 결과 */}
          {result.video_analysis && (
            <section className="result-section video-analysis-section">
              <div className="section-header">
                <h2>영상 분석 결과</h2>
                <span className="detection-count">
                  {result.video_analysis.summary.total_faces_detected + result.video_analysis.summary.total_fingers_detected}개 검출
                </span>
              </div>

              <div className="video-summary">
                <div className="video-stats">
                  <div className="stat-item">
                    <span className="stat-label">총 프레임 분석</span>
                    <span className="stat-value">{result.video_analysis.summary.total_frames_processed}개</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">얼굴 탐지</span>
                    <span className="stat-value">{result.video_analysis.summary.total_faces_detected}개</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">손가락 탐지</span>
                    <span className="stat-value">{result.video_analysis.summary.total_fingers_detected}개</span>
                  </div>
                </div>

                {/* 얼굴/손가락 탐지 시간 표시 */}
                {result.video_analysis.frames && result.video_analysis.frames.length > 0 && (
                  <div className="video-detection-times">
                    {result.video_analysis.summary.total_faces_detected > 0 && (
                      <div className="detection-time-section">
                        <h4>얼굴 탐지 시간</h4>
                        <div className="time-list">
                          {result.video_analysis.frames
                            .filter((frame) => frame.face && frame.face.count > 0)
                            .slice(0, 10)
                            .map((frame, idx: number) => (
                              <span key={idx} className="time-tag">
                                {frame.timestamp?.toFixed(1) || frame.frame_index || idx}초
                              </span>
                            ))}
                        </div>
                      </div>
                    )}
                    {result.video_analysis.summary.total_fingers_detected > 0 && (
                      <div className="detection-time-section">
                        <h4>손가락 탐지 시간</h4>
                        <div className="time-list">
                          {result.video_analysis.frames
                            .filter((frame) => frame.hand && frame.hand.count > 0)
                            .slice(0, 10)
                            .map((frame, idx: number) => (
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
                {/* eslint-disable-next-line @typescript-eslint/no-unused-vars */}
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
                        // 보안: 콘솔 로그 제거
                        
                        // 카드 클릭 시 모든 정보를 포함한 모달 열기
                        const modalData: EducationItem = {
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
                        
                        // 보안: 콘솔 로그 제거
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
