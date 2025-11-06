import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { API_CONFIG } from '../../constants';
import CommonHeader from '../common/CommonHeader';
import './Auth.css';

const EmailVerification: React.FC = () => {
  const [email, setEmail] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // 회원가입 페이지에서 전달된 이메일 사용
    if (location.state?.email) {
      setEmail(location.state.email);
    }
    // 실무: 코드는 이메일로만 전송되므로 자동 입력하지 않음
  }, [location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (!email) {
      setError('이메일을 입력하세요');
      return;
    }

    if (!verificationCode) {
      setError('인증 코드를 입력하세요');
      return;
    }

    // 6자리 숫자만 허용
    if (!/^\d{6}$/.test(verificationCode)) {
      setError('인증 코드는 6자리 숫자여야 합니다');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/auth/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email,
          code: verificationCode,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || '이메일 인증에 실패했습니다');
      }

      const data = await response.json();
      
      if (data.success) {
        setSuccess(true);
        // 로그인 페이지로 이동
        setTimeout(() => {
          navigate('/auth/login', { state: { email } });
        }, 2000);
      } else {
        throw new Error(data.error || '이메일 인증에 실패했습니다');
      }
    } catch (err: any) {
      setError(err.message || '인증에 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <CommonHeader />
      <div className="auth-content">
        <div className="auth-box">
          <div className="auth-logo-section">
            <div className="auth-logo-icon">🔒</div>
            <div className="auth-logo-text">PrivAlert</div>
            <div className="auth-slogan">당신의 개인정보 보호 분석 시스템</div>
          </div>
          <h1>이메일 인증</h1>
        {success && (
          <div className="success-message">
            이메일 인증이 완료되었습니다! 로그인 페이지로 이동합니다.
          </div>
        )}
        {error && <div className="error-message">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">이메일</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading || success}
              placeholder="example@email.com"
            />
          </div>
          <div className="form-group">
            <label htmlFor="verificationCode">인증 코드</label>
            <input
              id="verificationCode"
              type="text"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              required
              disabled={loading || success}
              placeholder="6자리 숫자 코드"
              maxLength={6}
              style={{ 
                textAlign: 'center', 
                fontSize: '24px', 
                letterSpacing: '8px',
                fontFamily: 'monospace',
                fontWeight: 'bold'
              }}
            />
            <small className="form-hint">
              이메일로 전송된 6자리 인증 코드를 입력하세요. 코드는 10분 동안 유효합니다.
            </small>
          </div>
          <button type="submit" disabled={loading || success} className="auth-button">
            {loading ? '인증 중...' : '인증하기'}
          </button>
        </form>
        <div className="auth-link">
          <Link to="/auth/login">로그인으로 돌아가기</Link>
        </div>
        </div>
      </div>
    </div>
  );
};

export default EmailVerification;

