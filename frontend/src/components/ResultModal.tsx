import React from 'react';
import type { AnalysisResult } from '../types';

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
}) => {
  // XSS 방지: 텍스트 이스케이프
  const escapeHtml = (text: string) => {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>🔍 통합 분석 결과</h2>
          <button 
            className="modal-close"
            onClick={onClose}
            aria-label="닫기"
          >
            ✕
          </button>
        </div>
        
        <div className="modal-body">
          {/* 결과 요약 표시 */}
          <div className="result-summary">
            <div className="summary-card">
              <h3>📊 분석 요약</h3>
              <p>{result.summary?.message || '분석 완료'}</p>
            </div>
          </div>
          
          {/* 비디오 분석 결과는 UploadForm에서 처리 */}
          {/* 텍스트 분석 결과 */}
          {result.text_analysis && (
            <div className="text-analysis-section">
              <h3>📝 텍스트 분석</h3>
              <div dangerouslySetInnerHTML={{ 
                __html: escapeHtml(result.text_analysis.original_text || '') 
              }} />
            </div>
          )}
        </div>
        
        <div className="modal-footer">
          <button 
            className="modal-button primary"
            onClick={onClose}
          >
            확인
          </button>
        </div>
      </div>
    </div>
  );
};

