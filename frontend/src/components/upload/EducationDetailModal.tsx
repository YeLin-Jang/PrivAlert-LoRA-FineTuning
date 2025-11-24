import React from 'react';
import './EducationDetailModal.css';

interface EducationDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  category: 'rationale' | 'law' | 'risk' | 'tips' | 'all';
  data: {
    category?: string;
    law_summary?: string;
    law_summary_rationale?: string;
    risk_scenarios?: string[];
    risk_scenarios_rationale?: string;
    tips?: string[];
    tips_rationale?: string;
  };
}

export const EducationDetailModal: React.FC<EducationDetailModalProps> = ({
  isOpen,
  onClose,
  category,
  data,
}) => {
  // 보안: 콘솔 로그 제거

  if (!isOpen) return null;

  const getTitle = () => {
    if (category === 'all') {
      return data.category || '교육 안내';
    }
    switch (category) {
      case 'rationale':
        return 'AI 신뢰성 (근거)';
      case 'law':
        return '법령';
      case 'risk':
        return '위험 시나리오';
      case 'tips':
        return '보안 팁';
      default:
        return '';
    }
  };

  const getContent = () => {
    if (category === 'all') {
      // 모든 정보를 한 번에 표시 (수정문장 근거 포함)
      return (
        <div className="education-detail-content">
          {data.law_summary && (
            <div className="education-section-item">
              <h3>법령 요약</h3>
              <p>{data.law_summary}</p>
              {data.law_summary_rationale && (
                <div className="rationale-section rationale-highlight">
                  <h4 className="rationale-subtitle">
                    <span className="rationale-icon">⚖️</span>
                    법령 인용 근거
                  </h4>
                  <div className="rationale-content">
                    <p>{data.law_summary_rationale}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {data.risk_scenarios && data.risk_scenarios.length > 0 && (
            <div className="education-section-item">
              <h3>위험 시나리오</h3>
              <ul className="risk-scenarios-list">
                {data.risk_scenarios.map((scenario, idx) => (
                  <li key={idx}>
                    <span className="scenario-number">{idx + 1}</span>
                    <span className="scenario-text">{scenario}</span>
                  </li>
                ))}
              </ul>
              {data.risk_scenarios_rationale && (
                <div className="rationale-section rationale-highlight">
                  <h4 className="rationale-subtitle">
                    <span className="rationale-icon">⚠️</span>
                    위험 시나리오 근거
                  </h4>
                  <div className="rationale-content">
                    <p>{data.risk_scenarios_rationale}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {data.tips && data.tips.length > 0 && (
            <div className="education-section-item">
              <h3>보안 팁</h3>
              <ul className="tips-list">
                {data.tips.map((tip, idx) => (
                  <li key={idx}>{tip}</li>
                ))}
              </ul>
              {data.tips_rationale && (
                <div className="rationale-section rationale-highlight">
                  <h4 className="rationale-subtitle">
                    <span className="rationale-icon">💡</span>
                    보안 팁 근거
                  </h4>
                  <div className="rationale-content">
                    <p>{data.tips_rationale}</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      );
    }

    switch (category) {
      case 'law':
        return (
          <div className="education-detail-content">
            <h3>법령 요약</h3>
            <p>{data.law_summary || '법령 정보가 없습니다.'}</p>
            {data.law_summary_rationale && (
              <div className="rationale-section rationale-highlight">
                <h4 className="rationale-subtitle">
                  <span className="rationale-icon">⚖️</span>
                  법령 인용 근거
                </h4>
                <div className="rationale-content">
                  <p>{data.law_summary_rationale}</p>
                </div>
              </div>
            )}
          </div>
        );
      case 'risk':
        return (
          <div className="education-detail-content">
            <h3>위험 시나리오</h3>
            {data.risk_scenarios && data.risk_scenarios.length > 0 ? (
              <ul className="risk-scenarios-list">
                {data.risk_scenarios.map((scenario, idx) => (
                  <li key={idx}>
                    <span className="scenario-number">{idx + 1}</span>
                    <span className="scenario-text">{scenario}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>위험 시나리오 정보가 없습니다.</p>
            )}
            {data.risk_scenarios_rationale && (
              <div className="rationale-section rationale-highlight">
                <h4 className="rationale-subtitle">
                  <span className="rationale-icon">⚠️</span>
                  위험 시나리오 근거
                </h4>
                <div className="rationale-content">
                  <p>{data.risk_scenarios_rationale}</p>
                </div>
              </div>
            )}
          </div>
        );
      case 'tips':
        return (
          <div className="education-detail-content">
            <h3>보안 팁</h3>
            {data.tips && data.tips.length > 0 ? (
              <ul className="tips-list">
                {data.tips.map((tip, idx) => (
                  <li key={idx}>{tip}</li>
                ))}
              </ul>
            ) : (
              <p>보안 팁 정보가 없습니다.</p>
            )}
            {data.tips_rationale && (
              <div className="rationale-section rationale-highlight">
                <h4 className="rationale-subtitle">
                  <span className="rationale-icon">💡</span>
                  보안 팁 근거
                </h4>
                <div className="rationale-content">
                  <p>{data.tips_rationale}</p>
                </div>
              </div>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="education-detail-overlay">
      {/* overlay 클릭 시 닫히지 않음 (X 버튼만 닫기 가능) */}
      <div className="education-detail-modal" onClick={(e) => e.stopPropagation()}>
        <div className="education-detail-header">
          <h2>{getTitle()}</h2>
          {data.category && category !== 'all' && (
            <span className="education-detail-category">{data.category}</span>
          )}
          <button className="education-detail-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="education-detail-body">
          {getContent()}
        </div>
      </div>
    </div>
  );
};


