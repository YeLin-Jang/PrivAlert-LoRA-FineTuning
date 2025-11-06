import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { userApi } from '../../services/userApi';
import CommonHeader from '../common/CommonHeader';
import './Auth.css';

const Signup: React.FC = () => {
  const [email, setEmail] = useState('');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
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

    // 별명 검증
    if (!nickname || nickname.trim().length < 2) {
      setError('별명은 최소 2자 이상이어야 합니다');
      return;
    }

    if (nickname.trim().length > 20) {
      setError('별명은 최대 20자까지 가능합니다');
      return;
    }

    setLoading(true);

    try {
      // 이메일에서 username 생성 (이메일 주소의 @ 앞 부분)
      const username = email.split('@')[0];
      
      await userApi.register(username, email, password, nickname.trim());
      setSuccess(true);
      
      // 이메일 인증 페이지로 이동 (실무: 코드는 이메일로만 전송)
      setTimeout(() => {
        navigate('/auth/verify', { 
          state: { 
            email
          } 
        });
      }, 2000);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : '회원가입에 실패했습니다';
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
          <h1>회원가입</h1>
        {success && (
          <div className="success-message">
            회원가입 요청이 접수되었습니다.<br />
            이메일로 전송된 인증 코드를 확인하여 인증을 완료해주세요.
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
            <label htmlFor="nickname">별명</label>
            <input
              id="nickname"
              type="text"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              required
              disabled={loading || success}
              placeholder="사용할 별명을 입력하세요 (2-20자)"
              maxLength={20}
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
    </div>
  );
};

export default Signup;
