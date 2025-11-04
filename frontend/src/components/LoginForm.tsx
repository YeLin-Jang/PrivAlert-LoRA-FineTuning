import { useState, useEffect } from 'react';
import { login, checkSession, getCurrentUser } from '../api';
import type { User } from '../types';
import './Auth.css';

interface LoginFormProps {
  onLoginSuccess: (user: User) => void;
  onSwitchToRegister: () => void;
}

export default function LoginForm({ onLoginSuccess, onSwitchToRegister }: LoginFormProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // 세션 확인
    checkSession().then((session) => {
      if (session.authenticated && session.user) {
        onLoginSuccess(session.user);
      }
    }).catch(() => {
      // 세션이 없으면 무시
    });
  }, [onLoginSuccess]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const result = await login({ username, password });
      onLoginSuccess(result.user);
    } catch (err: any) {
      setError(err.message || '로그인에 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>로그인</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">사용자명 또는 이메일</label>
            <input
              type="text"
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              minLength={3}
              autoComplete="username"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">비밀번호</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
              autoComplete="current-password"
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>
        <div className="auth-switch">
          계정이 없으신가요?{' '}
          <button type="button" onClick={onSwitchToRegister} className="btn-link">
            회원가입
          </button>
        </div>
      </div>
    </div>
  );
}

