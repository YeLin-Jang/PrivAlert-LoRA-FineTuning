import React, { useState, useEffect } from 'react';
import { 
  detectNames, 
  maskNames, 
  rewriteText, 
  processNames, 
  getNameDetectionStatus 
} from '../api';
import type { 
  NameDetectionResult, 
  NameMaskingResult, 
  NameRewritingResult, 
  NameProcessingResult,
  DetectedName 
} from '../types';
import './NameProcessingForm.css';

const NameProcessingForm: React.FC = () => {
  const [text, setText] = useState('');
  const [maskChar, setMaskChar] = useState('*');
  const [useOpenAI, setUseOpenAI] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [serviceStatus, setServiceStatus] = useState<{
    model_loaded: boolean;
    device: string;
    service_status: string;
  } | null>(null);
  
  // 결과 상태
  const [detectionResult, setDetectionResult] = useState<NameDetectionResult | null>(null);
  const [maskingResult, setMaskingResult] = useState<NameMaskingResult | null>(null);
  const [rewritingResult, setRewritingResult] = useState<NameRewritingResult | null>(null);
  const [processingResult, setProcessingResult] = useState<NameProcessingResult | null>(null);

  // 컴포넌트 마운트 시 서비스 상태 확인
  useEffect(() => {
    checkServiceStatus();
  }, []);

  const checkServiceStatus = async () => {
    try {
      const status = await getNameDetectionStatus();
      setServiceStatus(status);
    } catch (err) {
      console.error('서비스 상태 확인 실패:', err);
      setError('이름 탐지 서비스를 사용할 수 없습니다.');
    }
  };

  const handleDetectNames = async () => {
    if (!text.trim()) {
      setError('텍스트를 입력해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const result = await detectNames(text);
      setDetectionResult(result);
      setMaskingResult(null);
      setRewritingResult(null);
      setProcessingResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '이름 탐지 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleMaskNames = async () => {
    if (!text.trim()) {
      setError('텍스트를 입력해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const result = await maskNames(text, maskChar);
      setMaskingResult(result);
      setDetectionResult(null);
      setRewritingResult(null);
      setProcessingResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '이름 마스킹 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRewriteText = async () => {
    if (!text.trim()) {
      setError('텍스트를 입력해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const result = await rewriteText(text, useOpenAI);
      setRewritingResult(result);
      setDetectionResult(null);
      setMaskingResult(null);
      setProcessingResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '텍스트 리라이팅 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleProcessNames = async () => {
    if (!text.trim()) {
      setError('텍스트를 입력해주세요.');
      return;
    }

    setIsLoading(true);
    setError(null);
    
    try {
      const result = await processNames(text, maskChar, useOpenAI);
      setProcessingResult(result);
      setDetectionResult(null);
      setMaskingResult(null);
      setRewritingResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '이름 처리 중 오류가 발생했습니다.');
    } finally {
      setIsLoading(false);
    }
  };

  const renderDetectedNames = (names: DetectedName[]) => {
    if (names.length === 0) {
      return <p className="no-results">탐지된 이름이 없습니다.</p>;
    }

    return (
      <div className="detected-names">
        <h4>탐지된 이름 ({names.length}개)</h4>
        <ul>
          {names.map((name, index) => (
            <li key={index} className="name-item">
              <span className="name-text">{name.text}</span>
              <span className="name-confidence">
                신뢰도: {(name.confidence * 100).toFixed(1)}%
              </span>
              <span className="name-position">
                위치: {name.start}-{name.end}
              </span>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  const renderTextComparison = (original: string, processed: string, title: string) => {
    return (
      <div className="text-comparison">
        <h4>{title}</h4>
        <div className="text-boxes">
          <div className="text-box">
            <h5>원본 텍스트</h5>
            <div className="text-content original">{original}</div>
          </div>
          <div className="text-box">
            <h5>처리된 텍스트</h5>
            <div className="text-content processed">{processed}</div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="name-processing-form">
      <div className="form-header">
        <h2>이름 탐지 및 마스킹 처리</h2>
        <p>텍스트에서 개인 이름을 탐지하고 마스킹 처리합니다.</p>
      </div>

      {/* 서비스 상태 */}
      {serviceStatus && (
        <div className={`service-status ${serviceStatus.model_loaded ? 'ready' : 'not-ready'}`}>
          <span className="status-indicator"></span>
          <span className="status-text">
            {serviceStatus.model_loaded ? '서비스 준비됨' : '서비스 로딩 중...'}
          </span>
          <span className="device-info">({serviceStatus.device})</span>
        </div>
      )}

      {/* 입력 폼 */}
      <div className="input-section">
        <div className="form-group">
          <label htmlFor="text-input">분석할 텍스트</label>
          <textarea
            id="text-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="이름이 포함된 텍스트를 입력하세요..."
            rows={6}
            disabled={isLoading}
          />
        </div>

        <div className="form-options">
          <div className="form-group">
            <label htmlFor="mask-char">마스킹 문자</label>
            <input
              id="mask-char"
              type="text"
              value={maskChar}
              onChange={(e) => setMaskChar(e.target.value)}
              maxLength={1}
              disabled={isLoading}
            />
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={useOpenAI}
                onChange={(e) => setUseOpenAI(e.target.checked)}
                disabled={isLoading}
              />
              OpenAI API 사용 (리라이팅)
            </label>
          </div>
        </div>
      </div>

      {/* 버튼들 */}
      <div className="action-buttons">
        <button
          onClick={handleDetectNames}
          disabled={isLoading || !serviceStatus?.model_loaded}
          className="btn btn-detect"
        >
          {isLoading ? '탐지 중...' : '이름 탐지'}
        </button>
        
        <button
          onClick={handleMaskNames}
          disabled={isLoading || !serviceStatus?.model_loaded}
          className="btn btn-mask"
        >
          {isLoading ? '마스킹 중...' : '이름 마스킹'}
        </button>
        
        <button
          onClick={handleRewriteText}
          disabled={isLoading || !serviceStatus?.model_loaded}
          className="btn btn-rewrite"
        >
          {isLoading ? '리라이팅 중...' : '텍스트 리라이팅'}
        </button>
        
        <button
          onClick={handleProcessNames}
          disabled={isLoading || !serviceStatus?.model_loaded}
          className="btn btn-process"
        >
          {isLoading ? '처리 중...' : '통합 처리'}
        </button>
      </div>

      {/* 오류 메시지 */}
      {error && (
        <div className="error-message">
          <span className="error-icon">⚠️</span>
          {error}
        </div>
      )}

      {/* 결과 표시 */}
      <div className="results-section">
        {/* 이름 탐지 결과 */}
        {detectionResult && (
          <div className="result-card">
            <h3>이름 탐지 결과</h3>
            {renderDetectedNames(detectionResult.detected_names)}
          </div>
        )}

        {/* 이름 마스킹 결과 */}
        {maskingResult && (
          <div className="result-card">
            <h3>이름 마스킹 결과</h3>
            {renderTextComparison(
              maskingResult.original_text,
              maskingResult.masked_text,
              `마스킹 처리 (${maskingResult.mask_count}개 이름 마스킹)`
            )}
            {renderDetectedNames(maskingResult.detected_names)}
          </div>
        )}

        {/* 텍스트 리라이팅 결과 */}
        {rewritingResult && (
          <div className="result-card">
            <h3>텍스트 리라이팅 결과</h3>
            {renderTextComparison(
              rewritingResult.original_text,
              rewritingResult.rewritten_text,
              '리라이팅 처리'
            )}
          </div>
        )}

        {/* 통합 처리 결과 */}
        {processingResult && (
          <div className="result-card">
            <h3>통합 처리 결과</h3>
            {renderTextComparison(
              processingResult.original_text,
              processingResult.masked_text,
              `1단계: 이름 마스킹 (${processingResult.mask_count}개 이름 마스킹)`
            )}
            {renderTextComparison(
              processingResult.masked_text,
              processingResult.rewritten_text,
              '2단계: 텍스트 리라이팅'
            )}
            {renderDetectedNames(processingResult.detected_names)}
          </div>
        )}
      </div>
    </div>
  );
};

export default NameProcessingForm;
