import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useUserAuth } from '../../contexts/UserAuthContext';
import './Auth.css';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useUserAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // 이메일 인증 페이지에서 전달된 이메일 사용
    if (location.state?.email) {
      setEmail(location.state.email);
    }
  }, [location]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      // 로그인 성공 후 메인 페이지로 이동
      navigate('/');
    } catch (err: any) {
      setError(err.message || '로그인에 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-box">
        <h1>로그인</h1>
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
              disabled={loading}
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
              disabled={loading}
              placeholder="비밀번호를 입력하세요"
            />
          </div>
          <button type="submit" disabled={loading} className="auth-button">
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>
        <div className="auth-link">
          계정이 없으신가요? <Link to="/auth/signup">회원가입</Link>
        </div>
      </div>
    </div>
  );
};

export default Login;

