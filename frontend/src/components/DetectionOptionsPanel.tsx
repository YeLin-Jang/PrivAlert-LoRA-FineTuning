import React from 'react';
import type { DetectionOptions } from '../types';

interface DetectionOptionsPanelProps {
  detectionOptions: DetectionOptions;
  onToggle: (option: keyof DetectionOptions) => void;
  onSelectAll: () => void;
  onDeselectAll: () => void;
}

const OPTION_LABELS: Record<keyof DetectionOptions, string> = {
  face: '얼굴',
  fingerprint: '지문/손가락',
  phone: '전화번호',
  rrn: '주민등록번호',
  passport: '여권번호',
  ip_address: 'IP주소',
  email: '이메일',
  account: '계좌번호',
  school: '학교명',
  workplace: '직장명',
  name: '이름',
  address: '주소',
};

export const DetectionOptionsPanel: React.FC<DetectionOptionsPanelProps> = ({
  detectionOptions,
  onToggle,
  onSelectAll,
  onDeselectAll,
}) => {
  return (
    <div className="detection-options-panel">
      <div className="options-header">
        <h3>🔍 민감 정보 탐지 옵션</h3>
        <div className="options-actions">
          <button type="button" onClick={onSelectAll} className="select-all-btn">
            전체 선택
          </button>
          <button type="button" onClick={onDeselectAll} className="deselect-all-btn">
            전체 해제
          </button>
        </div>
      </div>
      
      <div className="options-grid">
        {Object.entries(detectionOptions).map(([key, value]) => (
          <label key={key} className="option-checkbox">
            <input
              type="checkbox"
              checked={value}
              onChange={() => onToggle(key as keyof DetectionOptions)}
              aria-label={OPTION_LABELS[key as keyof DetectionOptions]}
            />
            <span>{OPTION_LABELS[key as keyof DetectionOptions]}</span>
          </label>
        ))}
      </div>
    </div>
  );
};


