import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { API_CONFIG } from '../../constants';
import CommonHeader from '../common/CommonHeader';
import './Auth.css';

const EmailVerification: React.FC = () => {
  const [email, setEmail] = useState('');
  const [otp, setOtp] = useState<string[]>(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const inputRefs = React.useRef<(HTMLInputElement | null)[]>([]);

  useEffect(() => {
    // 회원가입 페이지에서 전달된 이메일 사용
    if (location.state?.email) {
      setEmail(location.state.email);
    }
    // 첫 번째 입력 필드에 포커스
    inputRefs.current[0]?.focus();
  }, [location]);

  const handleOtpChange = (index: number, value: string) => {
    // 숫자만 허용
    if (value && !/^\d$/.test(value)) {
      return;
    }

    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    // 다음 입력 필드로 자동 이동
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    // Backspace 처리
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
    // Paste 처리
    if (e.key === 'v' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      navigator.clipboard.readText().then((text) => {
        const digits = text.replace(/\D/g, '').slice(0, 6).split('');
        const newOtp = [...otp];
        digits.forEach((digit, i) => {
          if (index + i < 6) {
            newOtp[index + i] = digit;
          }
        });
        setOtp(newOtp);
        const nextIndex = Math.min(index + digits.length, 5);
        inputRefs.current[nextIndex]?.focus();
      });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (!email) {
      setError('이메일을 입력하세요');
      return;
    }

    const verificationCode = otp.join('');
    
    if (!verificationCode || verificationCode.length !== 6) {
      setError('인증 코드 6자리를 모두 입력하세요');
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
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '이메일 인증에 실패했습니다';
      setError(errorMessage);
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
            <img src="/Privalert.png" alt="PrivAlert" className="auth-logo-image" />
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
            <div className="otp-input-container">
              {otp.map((digit, index) => (
                <input
                  key={index}
                  ref={(el) => {
                    inputRefs.current[index] = el;
                  }}
                  type="text"
                  inputMode="numeric"
                  maxLength={1}
                  value={digit}
                  onChange={(e) => handleOtpChange(index, e.target.value)}
                  onKeyDown={(e) => handleKeyDown(index, e)}
                  disabled={loading || success}
                  className="otp-input"
                  autoComplete="off"
                />
              ))}
            </div>
            <small className="form-hint">
              이메일로 전송된 6자리 인증 코드를 입력하세요.<br />
              코드는 10분 동안 유효합니다.
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

