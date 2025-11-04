import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './LoginForm.css';

interface LoginFormProps {
  onSwitchToSignup: () => void;
  onClose?: () => void;
}

export default function LoginForm({ onSwitchToSignup, onClose }: LoginFormProps) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      onClose?.();
    } catch (err: any) {
      setError(err.message || '로그인에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-modal">
      <div className="auth-modal-content">
        {onClose && (
          <button className="auth-close-btn" onClick={onClose}>
            ✕
          </button>
        )}
        <h2>로그인</h2>
        
        {error && <div className="auth-error">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="auth-form-group">
            <label htmlFor="login-email">이메일</label>
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="이메일을 입력하세요"
              disabled={loading}
            />
          </div>
          
          <div className="auth-form-group">
            <label htmlFor="login-password">비밀번호</label>
            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="비밀번호를 입력하세요"
              disabled={loading}
              minLength={8}
            />
          </div>
          
          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? '로그인 중...' : '로그인'}
          </button>
        </form>
        
        <div className="auth-switch">
          계정이 없으신가요?{' '}
          <button type="button" onClick={onSwitchToSignup} className="auth-link-btn">
            회원가입
          </button>
        </div>
      </div>
    </div>
  );
}

