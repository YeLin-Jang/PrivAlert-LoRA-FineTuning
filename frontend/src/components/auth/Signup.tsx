import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../../services/userApi';
import './Auth.css';

const Signup: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [verificationCode, setVerificationCode] = useState('');
  const navigate = useNavigate();

  const validatePassword = (pwd: string): string | null => {
    if (pwd.length < 12) {
      return '비밀번호는 최소 12자 이상이어야 합니다';
    }
    if (!/[A-Z]/.test(pwd)) {
      return '비밀번호에 대문자가 포함되어야 합니다';
    }
    if (!/[a-z]/.test(pwd)) {
      return '비밀번호에 소문자가 포함되어야 합니다';
    }
    if (!/[0-9]/.test(pwd)) {
      return '비밀번호에 숫자가 포함되어야 합니다';
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) {
      return '비밀번호에 특수문자가 포함되어야 합니다';
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess(false);

    // 비밀번호 검증
    const passwordError = validatePassword(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다');
      return;
    }

    setLoading(true);

    try {
      const response = await register({ email, password });
      setSuccess(true);
      
      // 개발 모드에서 인증번호가 응답에 포함된 경우
      if (response.verification_code) {
        setVerificationCode(response.verification_code);
      }
      
      // 이메일 인증 페이지로 이동
      setTimeout(() => {
        navigate('/auth/verify', { state: { email } });
      }, 2000);
    } catch (err: any) {
      setError(err.message || '회원가입에 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <h1>회원가입</h1>
        {success && (
          <div className="success-message">
            회원가입이 완료되었습니다. 이메일을 확인하여 인증번호를 입력하세요.
            {verificationCode && (
              <div className="debug-info">
                <strong>개발 모드:</strong> 인증번호: {verificationCode}
              </div>
            )}
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
            <label htmlFor="password">비밀번호</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading || success}
              placeholder="최소 12자, 대소문자, 숫자, 특수문자 포함"
            />
            <small className="form-hint">
              비밀번호는 최소 12자 이상이며, 대문자, 소문자, 숫자, 특수문자를 포함해야 합니다.
            </small>
          </div>
          <div className="form-group">
            <label htmlFor="confirmPassword">비밀번호 확인</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={loading || success}
              placeholder="비밀번호를 다시 입력하세요"
            />
          </div>
          <button type="submit" disabled={loading || success} className="auth-button">
            {loading ? '처리 중...' : '회원가입'}
          </button>
        </form>
        <div className="auth-link">
          이미 계정이 있으신가요? <Link to="/auth/login">로그인</Link>
        </div>
      </div>
    </div>
  );
};

export default Signup;
