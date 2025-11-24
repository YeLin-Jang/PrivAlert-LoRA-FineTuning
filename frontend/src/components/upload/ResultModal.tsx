import React, { useState, useMemo, useRef } from 'react';
import type { AnalysisResult } from '../../types';
import './ResultModal.css';
import { EducationDetailModal } from './EducationDetailModal';
import { API_CONFIG } from '../../constants';

interface ResultModalProps {
  result: AnalysisResult & { video_analysis?: any };
  onClose: () => void;
  detectionOptions?: Record<string, boolean>;
  blurFingers?: boolean;
  onShowEducation?: (maskedText: string, categories: Record<string, any>) => void; // 전체 수정하기에서 사용하지 않음 (현재는 직접 수정 적용)
  eduItems?: any[] | null;
  revisedSentence?: string | null;
  revisedSentenceRationale?: string | null;
  userOriginalText?: string | null;
  sessionId?: string | null;
}

export const ResultModal: React.FC<ResultModalProps> = ({
  result,
  onClose,
  detectionOptions: _detectionOptions,
  onShowEducation: _onShowEducation,
  eduItems = null,
  revisedSentence = null,
  revisedSentenceRationale = null,
  userOriginalText = null,
  sessionId = null,
}) => {
  // 보안: 콘솔 로그 제거
  const [selectedParts, setSelectedParts] = useState<Record<number, string>>({}); // 각 부분별로 선택된 수정문장 저장
  const [isAllModified, setIsAllModified] = useState(false); // 전체 수정 여부
  const [hoveredPartIndex, setHoveredPartIndex] = useState<number | null>(null);
  const [fixedTooltipIndex, setFixedTooltipIndex] = useState<number | null>(null); // 고정된 툴팁 인덱스
  const [ignoredParts, setIgnoredParts] = useState<Set<number>>(new Set()); // 무시된 부분 (형광펜 제거)
  const [educationModalOpen, setEducationModalOpen] = useState(false);
  const [educationModalCategory, setEducationModalCategory] = useState<'rationale' | 'law' | 'risk' | 'tips' | 'all'>('rationale');
  const [educationModalData, setEducationModalData] = useState<any>(null);
  const [exifPreviewOpen, setExifPreviewOpen] = useState<number | null>(null); // EXIF 제거된 이미지 미리보기
  const [tooltipPosition, setTooltipPosition] = useState<Record<number, 'top' | 'bottom'>>({}); // 툴팁 위치 (위/아래)
  const tooltipRefs = useRef<Record<number, HTMLSpanElement | null>>({});
  const [isSentenceRevised, setIsSentenceRevised] = useState(false); // 문장 전체 수정 여부

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
        const revisedSuggestion = getSuggestionText(part.category);
        const isHovered = hoveredPartIndex === part.partIndex;
        // 음성 인식 결과는 클릭 고정 없이 호버만 사용
        const showTooltip = isHovered;

        return (
          <span
            key={idx}
            ref={(el) => {
              if (el) {
                tooltipRefs.current[part.partIndex] = el;
              }
            }}
            className={`highlight-text highlight-${part.riskLevel}`}
            onMouseEnter={() => {
              setHoveredPartIndex(part.partIndex);
              // 위치 계산
              const element = tooltipRefs.current[part.partIndex];
              if (element) {
                const rect = element.getBoundingClientRect();
                const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                const spaceAbove = rect.top + scrollTop;
                const spaceBelow = window.innerHeight - rect.bottom;
                // 위쪽 공간이 300px 미만이면 아래쪽에 표시
                if (spaceAbove < 300 && spaceBelow > 300) {
                  setTooltipPosition(prev => ({ ...prev, [part.partIndex]: 'bottom' }));
                } else {
                  setTooltipPosition(prev => ({ ...prev, [part.partIndex]: 'top' }));
                }
              }
            }}
            onMouseLeave={() => {
              setHoveredPartIndex(null);
            }}
          >
            {part.text}
            {showTooltip && (
              <div className={tooltipPosition[part.partIndex] === 'bottom' ? 'text-revision-tooltip-below' : 'text-revision-tooltip'}>
                <div className="tooltip-content">
                  <div className="tooltip-text-bubble problem-bubble">
                    <p className="tooltip-original">{displayOriginalText}</p>
                  </div>
                  <div className="tooltip-text-bubble revised-bubble">
                    <p className="tooltip-revised">
                      {hasRevisedText && revisedText ? revisedText : revisedSuggestion}
                    </p>
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

  const getSuggestionText = (category?: string): string => {
    if (category) {
      return getGeneralizedText(category);
    }
    if (revisedSentence && revisedSentence.trim()) {
      return revisedSentence.trim();
    }
    return '정보';
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
  const educationCategories = useMemo(() => {
    const merged: Record<string, any> = { ...(categories || {}) };
    const faceCount = result.face_detection?.total_count || 0;
    if (faceCount > 0) {
      merged.face = {
        count: faceCount,
        items: [
          {
            type: 'face',
            value: '얼굴',
            category: 'face',
          },
        ],
      };
    }
    return merged;
  }, [categories, result.face_detection]);
  const educationCardOrder: string[] = ['name', 'phone', 'address', 'school', 'face'];
  const orderedEducationEntries = educationCardOrder.map(key => [key, educationCategories[key] || null] as const);
  const displayOriginalText =
    (userOriginalText && userOriginalText.trim().length > 0 ? userOriginalText : textAnalysis?.original_text) || '';
  const hasDisplayText = displayOriginalText.trim().length > 0;
  const revisedText = textAnalysis?.revised_text || '';
  const hasRevisedText = revisedText.trim().length > 0;
  
  // 검출된 항목 카운트 계산
  const detectedCounts: Record<string, number> = {};
  let totalDetected = 0;
  
  Object.entries(categories).forEach(([key, value]: [string, any]) => {
    const count = value?.count || 0;
    detectedCounts[key] = count;
    totalDetected += count;
  });
  const summaryPriority = ['name', 'phone', 'address', 'school', 'rrn', 'passport', 'email', 'account', 'ip_address', 'workplace'];
  const summaryKeys = summaryPriority.filter(key => detectedCounts[key] > 0);
  const remainingSummaryKeys = Object.keys(detectedCounts).filter(key => !summaryPriority.includes(key));
  const orderedSummaryKeys = [...summaryKeys, ...remainingSummaryKeys];
  const baselineSummaryKeys: string[] = ['name', 'phone', 'address', 'school'];
  const displaySummaryKeys = Array.from(new Set([...baselineSummaryKeys, ...orderedSummaryKeys]));
  const hasOcrTexts = (result.ocr_text?.texts?.length || 0) > 0;

  type RiskLevel = 'very-dangerous' | 'dangerous' | 'caution';

  // 위험도별 색상 매핑
  const getRiskLevel = (category: string): RiskLevel => {
    // 매우 위험: 주민등록번호, 계좌번호, 여권번호
    if (['rrn', 'account', 'passport'].includes(category)) return 'very-dangerous';
    // 위험: 전화번호, 이메일, 이름, 주소
    if (['phone', 'email', 'name', 'address'].includes(category)) return 'dangerous';
    // 주의: 나머지
    return 'caution';
  };

  const normalizeDetectedValue = (value?: string) =>
    value ? value.trim().replace(/\s+/g, ' ').toLowerCase() : '';

  const ocrValueRiskMap = useMemo(() => {
    const map = new Map<string, { category: string; riskLevel: RiskLevel }>();
    if (!categories) return map;

    Object.entries(categories).forEach(([catKey, catData]) => {
      const items = (catData as any)?.items || [];
      items.forEach((item: any) => {
        const normalized = normalizeDetectedValue(item?.value);
        if (normalized) {
          map.set(normalized, {
            category: catKey,
            riskLevel: getRiskLevel(catKey),
          });
        }
      });
    });

    return map;
  }, [categories]);

  const getOcrItemRiskClass = (text?: string) => {
    const normalized = normalizeDetectedValue(text);
    if (!normalized) return '';
    const info = ocrValueRiskMap.get(normalized);
    if (!info) return '';
    return `ocr-risk-${info.riskLevel}`;
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
        const revisedSuggestion = getSuggestionText(part.category);
        const isHovered = hoveredPartIndex === part.partIndex;
        const isFixed = fixedTooltipIndex === part.partIndex;
        // 고정된 툴팁이 있으면 (다른 부분이 고정되어 있으면) 이 부분의 툴팁은 표시하지 않음
        const hasFixedTooltip = fixedTooltipIndex !== null;
        const showTooltip = (isHovered || isFixed) && (!hasFixedTooltip || isFixed);
        
        return (
          <span
            key={idx}
            ref={(el) => {
              if (el) {
                tooltipRefs.current[part.partIndex] = el;
              }
            }}
            className={`highlight-text highlight-${part.riskLevel}`}
            onMouseEnter={() => {
              // 고정된 툴팁이 없을 때만 호버 표시
              if (fixedTooltipIndex === null) {
                setHoveredPartIndex(part.partIndex);
                // 위치 계산
                const element = tooltipRefs.current[part.partIndex];
                if (element) {
                  const rect = element.getBoundingClientRect();
                  const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                  const spaceAbove = rect.top + scrollTop;
                  const spaceBelow = window.innerHeight - rect.bottom;
                  // 위쪽 공간이 300px 미만이면 아래쪽에 표시
                  if (spaceAbove < 300 && spaceBelow > 300) {
                    setTooltipPosition(prev => ({ ...prev, [part.partIndex]: 'bottom' }));
                  } else {
                    setTooltipPosition(prev => ({ ...prev, [part.partIndex]: 'top' }));
                  }
                }
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
                // 위치 계산
                const element = tooltipRefs.current[part.partIndex];
                if (element) {
                  const rect = element.getBoundingClientRect();
                  const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                  const spaceAbove = rect.top + scrollTop;
                  const spaceBelow = window.innerHeight - rect.bottom;
                  // 위쪽 공간이 300px 미만이면 아래쪽에 표시
                  if (spaceAbove < 300 && spaceBelow > 300) {
                    setTooltipPosition(prev => ({ ...prev, [part.partIndex]: 'bottom' }));
                  } else {
                    setTooltipPosition(prev => ({ ...prev, [part.partIndex]: 'top' }));
                  }
                }
              }
            }}
          >
            {part.text}
            {showTooltip && (
              <div className={tooltipPosition[part.partIndex] === 'bottom' ? 'text-revision-tooltip-below' : 'text-revision-tooltip'}>
                <div className="tooltip-content">
                  <div className="tooltip-header">
                    <span className="tooltip-title">개인정보 검출 내역</span>
                    <span className="tooltip-chip">{categoryNames[part.category] ?? '개인정보'}</span>
                  </div>
                  <div className="tooltip-text-bubble problem-bubble">
                    <p className="tooltip-original">{displayOriginalText}</p>
                  </div>
                  <div className="tooltip-text-bubble revised-bubble">
                    <p className="tooltip-revised">
                      {hasRevisedText && revisedText ? revisedText : revisedSuggestion}
                    </p>
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
                        // revised_text가 있으면 전체 문장 수정, 없으면 개별 단어만 수정
                        if (hasRevisedText && revisedText) {
                          // 전체 문장 수정
                          setIsSentenceRevised(true);
                          setSelectedParts({});
                          setIsAllModified(false);
                        } else {
                          // 개별 단어 수정 (기존 로직)
                          setSelectedParts({
                            ...selectedParts,
                            [part.partIndex]: revisedSuggestion
                          });
                        }
                        setFixedTooltipIndex(null);
                        setHoveredPartIndex(null);
                      }}
                    >
                      {hasRevisedText && revisedText ? '문장 전체 수정' : '수정하기'}
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
    face: '얼굴',
  };

  // 이미지 분석 결과
  const faceImages = result.face_detection?.images || [];
  const handImages = result.hand_detection?.images || [];
  const sanitizedImages = result.image_sanitization?.items || [];
  
  // 표시용 이미지: 얼굴/손가락 탐지 결과 이미지만 (탐지 후 표시된 이미지)
  // 다운로드용: EXIF 제거 이미지 (별도로 관리)
  const hasImageUploads = faceImages.length > 0 || handImages.length > 0 || sanitizedImages.length > 0 || hasOcrTexts;
  const displayImages: any[] = [];
  
  // 얼굴 탐지 결과 이미지 추가 (표시용)
  faceImages.forEach((img: any) => {
    if (img.result_image_url && displayImages.length < 3) {
      displayImages.push({
        ...img,
        display_url: img.result_image_url, // 표시용 URL
        detection_type: 'face'
      });
    }
  });
  
  // 손가락 탐지 결과 이미지 추가 (표시용, 같은 image_index가 없을 때만)
  handImages.forEach((img: any) => {
    if (img.result_image_url && displayImages.length < 3) {
      if (!displayImages.find((existing: any) => existing.image_index === img.image_index)) {
        displayImages.push({
          ...img,
          display_url: img.result_image_url, // 표시용 URL
          detection_type: 'hand'
        });
      }
    }
  });

  const shouldShowPhotoSection = hasImageUploads;
  const photoDetectionCount = (result.summary?.faces_detected || 0) + (result.summary?.fingers_detected || 0);
  // placeholder 제거 - 실제 이미지가 없으면 표시하지 않음

  const videoAnalysisData = result.video_analysis as any | undefined;
  const resolveImageSrc = (path?: string) => {
    if (!path) return '';
    if (path.startsWith('http') || path.startsWith('data:') || path.startsWith('blob:')) {
      return path;
    }
    if (path.startsWith('/')) {
      const backendPrefixes = ['/data/', '/results/', '/uploads/', '/api/'];
      if (backendPrefixes.some((prefix) => path.startsWith(prefix))) {
        return `${API_CONFIG.BASE_URL}${path}`;
      }
      return path;
    }
    return `${API_CONFIG.BASE_URL}${path}`;
  };
  const videoTotalFrames = videoAnalysisData
    ? videoAnalysisData.total_frames_processed ??
      videoAnalysisData.summary?.total_frames_processed ??
      videoAnalysisData.video_info?.frame_count ??
      0
    : 0;
  const videoFacesDetected = videoAnalysisData
    ? videoAnalysisData.faces_detected ??
      videoAnalysisData.summary?.total_faces_detected ??
      0
    : 0;
  const videoFingersDetected = videoAnalysisData
    ? videoAnalysisData.fingers_detected ??
      videoAnalysisData.summary?.total_fingers_detected ??
      0
    : 0;
  const videoDetectionCount = videoAnalysisData
    ? videoAnalysisData.detection_count ?? videoFacesDetected + videoFingersDetected
    : 0;
  const videoFrames = videoAnalysisData?.frames || [];
  const faceDetectionTimes: string[] =
    videoFacesDetected > 0 && videoFrames.length > 0
      ? videoFrames
          .filter((frame: any) => frame.face && frame.face.count > 0)
          .slice(0, 10)
          .map((frame: any, idx: number) => `${frame.timestamp?.toFixed(1) || frame.frame_index || idx}초`)
      : ['0.0초'];
  const fingerDetectionTimes: string[] =
    videoFingersDetected > 0 && videoFrames.length > 0
      ? videoFrames
          .filter((frame: any) => frame.hand && frame.hand.count > 0)
          .slice(0, 10)
          .map((frame: any, idx: number) => `${frame.timestamp?.toFixed(1) || frame.frame_index || idx}초`)
      : ['0.0초'];
  const educationDetectedCount = totalDetected + (result.face_detection?.total_count || 0);
  const shouldShowEducationSection = educationDetectedCount > 0 && orderedEducationEntries.length > 0;

  return (
    <div className="result-modal-overlay" onClick={onClose}>
      <div
        className="result-modal-content"
        data-session-id={sessionId || undefined}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="result-modal-header">
          <img
            src="/Privalert.png"
            alt="PrivAlert"
            className="result-modal-logo"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = 'none';
            }}
          />
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
              {!hasDisplayText && textAnalysis?.message ? (
                <div className="text-analysis-content">
                  <div className="no-text-message-box">
                    <p className="no-text-message">{textAnalysis.message}</p>
                  </div>
                </div>
              ) : (
              <div className="text-analysis-content">
                {/* 왼쪽: 검출 항목 요약 */}
                <div className="detection-summary-box">
                  {displaySummaryKeys.map(key => (
                    <div key={key} className="detection-item">
                      <span className="detection-label">{categoryNames[key] || key}</span>
                      <span className={`detection-value ${detectedCounts[key] > 0 ? 'detected' : 'safe'}`}>
                        {(detectedCounts[key] || 0)}개
                      </span>
                    </div>
                  ))}
                  {!displaySummaryKeys.length && (
                    <div className="detection-item">
                      <span className="detection-label">검출된 항목 없음</span>
                    </div>
                  )}

                </div>

                {/* 중앙: 분석된 텍스트 */}
                <div className="analyzed-text-box">
                  <div className="text-content">
                      {isSentenceRevised && hasRevisedText ? (
                        <div className="revised-text-display">
                          {revisedText}
                        </div>
                      ) : (
                        highlightText(displayOriginalText)
                      )}
                    </div>
                    {hasOcrTexts && (
                      <div className="ocr-detected-box centered">
                        <h4>이미지/동영상 OCR 탐지 텍스트</h4>
                        <p className="ocr-note">이미지·동영상 추출 텍스트도 텍스트 분석에 포함됩니다.</p>
                        <div className="ocr-text-list">
                          {result.ocr_text?.texts?.map((ocrLine, idx) => {
                            const normalized = normalizeDetectedValue(ocrLine);
                            const ocrInfo = ocrValueRiskMap.get(normalized);
                            const categoryName = ocrInfo ? categoryNames[ocrInfo.category] || ocrInfo.category : null;
                            
                            return (
                              <span
                                key={idx}
                                className={`ocr-text-item ${getOcrItemRiskClass(ocrLine)}`}
                                title={categoryName || undefined}
                              >
                                {ocrLine}
                                {categoryName && (
                                  <span className="ocr-category-tooltip">{categoryName}</span>
                                )}
                              </span>
                            );
                          })}
                        </div>
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
              {hasDisplayText && (
              <div className="text-action-buttons">
                <button 
                  className="action-btn primary"
                  onClick={() => {
                      if (isAllModified || isSentenceRevised) {
                        // 전체 복원: 모든 수정사항 제거
                        setSelectedParts({});
                        setIsAllModified(false);
                        setIsSentenceRevised(false);
                        setIgnoredParts(new Set());
                        setFixedTooltipIndex(null);
                        setHoveredPartIndex(null);
                      } else if (hasRevisedText && revisedText) {
                        // revised_text가 있으면 전체 문장 수정
                        setIsSentenceRevised(true);
                        setSelectedParts({});
                        setIsAllModified(false);
                      } else {
                        // 모든 탐지된 부분을 수정문장으로 교체
                        // highlightText와 동일한 로직으로 parts 계산
                        const originalText = displayOriginalText;
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
                            allParts[part.partIndex] = getSuggestionText(part.category);
                          }
                        });

                        setSelectedParts(allParts);
                        setIsAllModified(true);
                      }
                    }}
                  >
                    {isAllModified || isSentenceRevised ? '전체 복원하기' : '전체 수정하기'}
                </button>
              </div>
              )}
            </section>
          )}

          {/* 사진 분석 결과 */}
          {shouldShowPhotoSection && (
            <section className="result-section photo-analysis-section">
              <div className="section-header">
                <h2>사진 분석 결과</h2>
                <span className="detection-count">{photoDetectionCount}개 검출</span>
              </div>

              <div className="photo-grid">
                {displayImages.length > 0 ? (
                  displayImages.map((img: any, idx: number) => {
                    // 이미지의 image_index를 기준으로 탐지 정보 찾기
                    const imageIndex = typeof img.image_index === 'number' ? img.image_index : (idx + 1);
                    const imageLabel = imageIndex > 0 ? imageIndex : '이미지';
                    const faceImg = faceImages.find(f => f.image_index === imageIndex);
                    const handImg = handImages.find(h => h.image_index === imageIndex);
                    const detections: string[] = [];
                    
                    if (faceImg && faceImg.count && faceImg.count > 0) detections.push('얼굴');
                    if (handImg && handImg.count && handImg.count > 0) detections.push('지문정보');

                    // 같은 image_index의 EXIF 제거 이미지 찾기 (다운로드용)
                    const sanitizedImg = Array.isArray(sanitizedImages) 
                      ? sanitizedImages.find((s: any) => s.image_index === imageIndex)
                      : null;

                    const resolvedUrl = img?.display_url ? resolveImageSrc(img.display_url) : '';
                    const finalImageSrc = resolvedUrl
                      ? (img.placeholder ? resolvedUrl : `${resolvedUrl}${resolvedUrl.includes('?') ? '&' : '?'}t=${Date.now()}`)
                      : '';

                    return (
                      <div key={idx} className="photo-item">
                        <div className="photo-placeholder">
                          {img?.display_url ? (
                            <img 
                              src={finalImageSrc} 
                              alt={`이미지 ${imageLabel}`}
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
                            <span>이미지 {imageLabel}</span>
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
                            <span className="no-detection">
                              {img.placeholder ? '이미지 로딩 중...' : '검출 내역 없음'}
                            </span>
                          )}
                        </div>
                        {sanitizedImg?.report && (
                          <div className="metadata-status-box">
                            <div className="metadata-status-header">
                              <span className="status-check">✓</span>
                              <span className="status-text">메타데이터 제거 완료</span>
                            </div>
                            <div className="metadata-status-details">
                              <div className="status-item">
                                <span className="status-label">EXIF:</span>
                                <span className="status-value removed">제거됨</span>
                              </div>
                              <div className="status-item">
                                <span className="status-label">GPS:</span>
                                <span className="status-value removed">제거됨</span>
                              </div>
                              {sanitizedImg.report.source_format && sanitizedImg.report.target_format && (
                                <div className="status-item">
                                  <span className="status-label">형식:</span>
                                  <span className="status-value">{sanitizedImg.report.source_format} → {sanitizedImg.report.target_format}</span>
                                </div>
                              )}
                            </div>
                            {sanitizedImg.sanitized_url && (
                              <button
                                className="preview-sanitized-button"
                                onClick={() => setExifPreviewOpen(imageIndex)}
                              >
                                제거된 이미지 미리보기
                              </button>
                            )}
                          </div>
                        )}
                        {sanitizedImg?.sanitized_url && (
                          <button
                            className="download-image-button"
                            onClick={async () => {
                              try {
                                const rawUrl = sanitizedImg.sanitized_url;
                                const absoluteUrl = rawUrl.startsWith('http');
                                const backendManaged = rawUrl.startsWith('/data/');
                                const fallbackUrl = resolveImageSrc(rawUrl);
                                const effectiveSessionId =
                                  sessionId ||
                                  localStorage.getItem('analysis_session_id') ||
                                  localStorage.getItem('session_id');
                                
                                // 정적 파일 경로 체크 (public 폴더의 파일들)
                                const isStaticFile = rawUrl.startsWith('/') && 
                                  !rawUrl.startsWith('/data/') && 
                                  !rawUrl.startsWith('/api/') &&
                                  !rawUrl.startsWith('/results/') &&
                                  !rawUrl.startsWith('/uploads/');
                                
                                if (!backendManaged && (isStaticFile || absoluteUrl || !effectiveSessionId)) {
                                  if (fallbackUrl) {
                                    // 정적 파일을 fetch로 가져와서 다운로드
                                    const staticResponse = await fetch(fallbackUrl, {
                                      cache: 'no-cache',
                                    });
                                    if (!staticResponse.ok) {
                                      throw new Error('FILE_NOT_FOUND');
                                    }
                                    const blob = await staticResponse.blob();
                                    const url = window.URL.createObjectURL(blob);
                                    const filename = sanitizedImg.sanitized_filename || `sanitized_image_${imageIndex}.png`;
                                    const link = document.createElement('a');
                                    link.href = url;
                                    link.download = filename;
                                    document.body.appendChild(link);
                                    link.click();
                                    document.body.removeChild(link);
                                    window.URL.revokeObjectURL(url);
                                    return;
                                  }
                                  throw new Error('FILE_NOT_FOUND');
                                }
                                
                                // 보안: API 엔드포인트를 통한 프록시 다운로드 (파일 경로 노출 방지)
                                let urlPath = rawUrl;
                                
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
                                const finalUrl = effectiveSessionId
                                  ? `${downloadUrl}?session_id=${encodeURIComponent(effectiveSessionId)}`
                                  : downloadUrl;
                                
                                const headers: Record<string, string> = {};
                                if (effectiveSessionId) {
                                  headers['X-Session-ID'] = effectiveSessionId;
                                }
                                
                                const response = await fetch(finalUrl, {
                                  credentials: 'include', // 쿠키 포함
                                  method: 'GET',
                                  cache: 'no-cache', // 304 에러 방지
                                  headers,
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
                              } catch (error: any) {
                                // 보안: 일반화된 사용자 친화적 메시지만 표시
                                let message = '다운로드 중 오류가 발생했습니다.';
                                if (error?.message === 'FILE_NOT_FOUND') {
                                  message = '파일을 찾을 수 없습니다. 이미 삭제되었을 수 있습니다.';
                                } else if (error?.message === 'ACCESS_DENIED') {
                                  message = '파일 다운로드 권한이 없습니다.';
                                } else if (error?.message === 'DOWNLOAD_FAILED') {
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

              {sanitizedImages.length > 0 && (
                <div className="metadata-summary-panel">
                  <div className="metadata-summary-header">
                    <h3>메타데이터 제거 상태</h3>
                    {result.image_sanitization?.message && (
                      <p className="metadata-summary-message">{result.image_sanitization.message}</p>
                    )}
                  </div>
                  <div className="metadata-summary-list">
                    {sanitizedImages.map((item: any, idx: number) => (
                      <div key={`meta-${idx}`} className="metadata-summary-item">
                        <div className="metadata-summary-title">
                          {item.filename || `이미지 ${item.image_index}`}
                        </div>
                        <div className="metadata-summary-detail">
                          <span>EXIF {item.report?.exif_removed ? '제거' : '유지'}</span>
                          <span>GPS {item.report?.gps_removed ? '제거' : '유지'}</span>
                          {item.report?.size && <span>최종 크기 {item.report.size}</span>}
                        </div>
                        {item.summary_ko && (
                          <p className="metadata-summary-description">{item.summary_ko}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </section>
          )}

          {/* 비디오 분석 결과 */}
          {videoAnalysisData && (
            <section className="result-section video-analysis-section">
              <div className="section-header">
                <h2>영상 분석 결과</h2>
                <span className="detection-count">
                  {videoDetectionCount}개 검출
                </span>
              </div>

              <div className="video-summary">
                <div className="video-stats">
                  <div className="stat-item">
                    <span className="stat-label">총 프레임 분석</span>
                    <span className="stat-value">{videoTotalFrames}개</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">얼굴 탐지</span>
                    <span className="stat-value">{videoFacesDetected}개</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">손가락 탐지</span>
                    <span className="stat-value">{videoFingersDetected}개</span>
                  </div>
                </div>

                {/* 얼굴/손가락 탐지 시간 표시 */}
                {videoFrames.length > 0 && (
                  <div className="video-detection-times">
                    <div className="frame-status-card">
                      <h4>프레임 처리 상태</h4>
                      <div className="frame-status-list">
                        {videoFrames.slice(0, 10).map((frame: any, idx: number) => (
                          <span key={idx} className="frame-status-item">
                            {frame.status || `프레임 ${frame.frame_index + 1} 분석완료`}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="detection-time-section">
                      <h4>얼굴 탐지 시간</h4>
                      <div className="time-list">
                        {faceDetectionTimes.map((timeLabel, idx) => (
                          <span key={`face-time-${idx}`} className="time-tag">
                            {timeLabel}
                          </span>
                        ))}
                      </div>
                    </div>
                    <div className="detection-time-section">
                      <h4>손가락 탐지 시간</h4>
                      <div className="time-list">
                        {fingerDetectionTimes.map((timeLabel, idx) => (
                          <span key={`finger-time-${idx}`} className="time-tag">
                            {timeLabel}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {videoAnalysisData.audio_transcription?.text && (
                  <div className="video-audio-section">
                    <h3>음성 인식 텍스트</h3>
                    <div className="audio-text-content">
                      {videoAnalysisData.audio_transcription.analysis ?
                        highlightAudioText(
                          videoAnalysisData.audio_transcription.text,
                          videoAnalysisData.audio_transcription.analysis.categories || {}
                        ) :
                        videoAnalysisData.audio_transcription.text
                      }
                    </div>

                    {videoAnalysisData.audio_transcription.analysis && (
                      <div className="audio-analysis">
                        {videoAnalysisData.audio_transcription.analysis.detected && (
                          <div className="audio-detection-summary">
                            <span className="detection-badge">
                              {videoAnalysisData.audio_transcription.analysis.total_count}개 검출
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
          {shouldShowEducationSection && (
            <section className="result-section education-section">
              <div className="section-header">
                <h2>교육 안내</h2>
                <span className="detection-count">{educationDetectedCount}개 검출</span>
              </div>
              <div className="education-category-boxes">
                {/* 탐지된 각 카테고리별로 카드 생성 */}
                {orderedEducationEntries.map(([catKey]) => {
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
                      (catKey === 'face' && itemCategory === '얼굴');
                  });

                  // eduItem이 없어도 카테고리 이름만 표시
                  return (
                    <div
                      key={catKey}
                      className="education-simple-card"
                      onClick={() => {
                        // 보안: 콘솔 로그 제거

                        // 카드 클릭 시 모든 정보를 포함한 모달 열기
                        const modalData: any = {
                          category: catName,
                        };

                        if (eduItem) {
                          Object.assign(modalData, eduItem);
                        }

                        setEducationModalData(modalData);
                        setEducationModalCategory('all'); // 모든 정보 표시
                        setEducationModalOpen(true);

                        // 보안: 콘솔 로그 제거
                      }}
                    >
                      <div className="simple-card-content centered">
                        <span className="edu-card-title">{catName}</span>
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

      {/* EXIF 제거된 이미지 미리보기 모달 */}
      {exifPreviewOpen !== null && sanitizedImages[exifPreviewOpen] && (
        <div className="exif-preview-overlay" onClick={() => setExifPreviewOpen(null)}>
          <div className="exif-preview-modal" onClick={(e) => e.stopPropagation()}>
            <div className="exif-preview-header">
              <h2>EXIF 제거된 이미지</h2>
              <button className="exif-preview-close" onClick={() => setExifPreviewOpen(null)}>×</button>
            </div>
            <div className="exif-preview-content">
              <div className="exif-preview-image-container">
                <img
                  src={resolveImageSrc(sanitizedImages[exifPreviewOpen].sanitized_url)}
                  alt="EXIF 제거된 이미지"
                  className="exif-preview-image"
                />
              </div>
              <div className="exif-preview-report">
                <h3>메타데이터 제거 리포트</h3>
                <div className="exif-report-grid">
                  <div className="exif-report-item">
                    <span className="report-label">원본 형식:</span>
                    <span className="report-value">{sanitizedImages[exifPreviewOpen].report?.source_format || 'N/A'}</span>
                  </div>
                  <div className="exif-report-item">
                    <span className="report-label">변환 형식:</span>
                    <span className="report-value">{sanitizedImages[exifPreviewOpen].report?.target_format || 'N/A'}</span>
                  </div>
                  <div className="exif-report-item">
                    <span className="report-label">EXIF 제거:</span>
                    <span className="report-value removed">✓ 완료</span>
                  </div>
                  <div className="exif-report-item">
                    <span className="report-label">GPS 제거:</span>
                    <span className="report-value removed">✓ 완료</span>
                  </div>
                  {sanitizedImages[exifPreviewOpen].report?.size && (
                    <div className="exif-report-item">
                      <span className="report-label">파일 크기:</span>
                      <span className="report-value">{(sanitizedImages[exifPreviewOpen].report.size / 1024).toFixed(2)} KB</span>
                    </div>
                  )}
                </div>
                {sanitizedImages[exifPreviewOpen].details_ko && (
                  <div className="exif-report-details">
                    <h4>상세 정보</h4>
                    <ul>
                      {sanitizedImages[exifPreviewOpen].details_ko.exif && (
                        <li>{sanitizedImages[exifPreviewOpen].details_ko.exif}</li>
                      )}
                      {sanitizedImages[exifPreviewOpen].details_ko.gps && (
                        <li>{sanitizedImages[exifPreviewOpen].details_ko.gps}</li>
                      )}
                      {sanitizedImages[exifPreviewOpen].details_ko.format && (
                        <li>{sanitizedImages[exifPreviewOpen].details_ko.format}</li>
                      )}
                      {sanitizedImages[exifPreviewOpen].details_ko.size && (
                        <li>{sanitizedImages[exifPreviewOpen].details_ko.size}</li>
                      )}
                    </ul>
                  </div>
                )}
                <div className="exif-preview-note">
                  <p>✓ 이 이미지는 EXIF 메타데이터가 완전히 제거되었습니다.</p>
                  <p>✓ 위치 정보, 촬영 기기 정보, 촬영 시간 등이 모두 삭제되었습니다.</p>
                  <p>✓ 다운로드한 파일에도 동일하게 적용됩니다.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

