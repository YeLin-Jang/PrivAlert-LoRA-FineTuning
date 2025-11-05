/**
 * 회원가입 페이지 컴포넌트
 */
import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import type { DetectionOptions } from '../types';
import { DetectionOptionsPanel } from './DetectionOptionsPanel';
import './RegisterPage.css';

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 필터링 옵션 상태
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
    driverLicense: false,
    postalCode: false,
  });

  const toggleDetectionOption = (option: keyof DetectionOptions) => {
    setDetectionOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }));
  };

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // 비밀번호 확인
    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다');
      return;
    }

    if (password.length < 8) {
      setError('비밀번호는 최소 8자 이상이어야 합니다');
      return;
    }

    setLoading(true);

    try {
      await register(username, email, password, detectionOptions);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : '회원가입에 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="register-page">
      <div className="register-container">
        <div className="register-header">
          <Link to="/" className="logo-link">
            <span className="logo-icon">🔔</span>
            <span className="logo-text">PrivAlert</span>
          </Link>
          <h1>회원가입</h1>
          <p className="subtitle">새로운 계정을 만드세요</p>
        </div>

        <form onSubmit={handleSubmit} className="register-form">
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}

          <div className="form-section">
            <h2 className="section-title">기본 정보</h2>
            
            <div className="form-group">
              <label htmlFor="username">사용자명</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                disabled={loading}
                placeholder="3-20자의 영문, 숫자, 언더스코어(_), 하이픈(-)"
                autoComplete="username"
                pattern="[a-zA-Z0-9_-]{3,20}"
              />
            </div>

            <div className="form-group">
              <label htmlFor="email">이메일</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                placeholder="example@email.com"
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">비밀번호</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                placeholder="최소 8자 이상"
                autoComplete="new-password"
                minLength={8}
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmPassword">비밀번호 확인</label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={loading}
                placeholder="비밀번호를 다시 입력하세요"
                autoComplete="new-password"
              />
            </div>
          </div>

          <div className="form-section">
            <h2 className="section-title">필터링 설정</h2>
            <p className="section-description">
              원하는 개인정보 탐지 항목을 선택하세요. 나중에 마이페이지에서 변경할 수 있습니다.
            </p>
            
            <DetectionOptionsPanel
              detectionOptions={detectionOptions}
              onToggle={toggleDetectionOption}
              onSelectAll={selectAllOptions}
              onDeselectAll={deselectAllOptions}
            />
          </div>

          <button
            type="submit"
            className="submit-button"
            disabled={loading || !username || !email || !password || !confirmPassword}
          >
            {loading ? '가입 중...' : '회원가입'}
          </button>

          <div className="form-footer">
            <p>
              이미 계정이 있으신가요?{' '}
              <Link to="/login" className="link">
                로그인
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}

