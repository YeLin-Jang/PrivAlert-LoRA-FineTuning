import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { verifyEmail } from '../../services/userApi';
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
  }, [location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    if (!email || !verificationCode) {
      setError('이메일과 인증번호를 모두 입력하세요');
      return;
    }

    if (verificationCode.length !== 6) {
      setError('인증번호는 6자리 숫자입니다');
      return;
    }

    setLoading(true);

    try {
      await verifyEmail({ email, verification_code: verificationCode });
      setSuccess(true);
      
      // 로그인 페이지로 이동
      setTimeout(() => {
        navigate('/auth/login', { state: { email } });
      }, 2000);
    } catch (err: any) {
      setError(err.message || '인증에 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
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
            <label htmlFor="verificationCode">인증번호</label>
            <input
              id="verificationCode"
              type="text"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              required
              disabled={loading || success}
              placeholder="6자리 숫자"
              maxLength={6}
              pattern="[0-9]{6}"
            />
            <small className="form-hint">
              이메일로 전송된 6자리 인증번호를 입력하세요.
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
  );
};

export default EmailVerification;

