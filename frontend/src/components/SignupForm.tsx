import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import './LoginForm.css';

interface SignupFormProps {
  onSwitchToLogin: () => void;
  onClose?: () => void;
}

export default function SignupForm({ onSwitchToLogin, onClose }: SignupFormProps) {
  const { signup } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('비밀번호가 일치하지 않습니다.');
      return;
    }

    if (password.length < 8) {
      setError('비밀번호는 최소 8자 이상이어야 합니다.');
      return;
    }

    setLoading(true);

    try {
      await signup(email, password);
      onClose?.();
    } catch (err: any) {
      setError(err.message || '회원가입에 실패했습니다.');
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
        <h2>회원가입</h2>
        
        {error && <div className="auth-error">{error}</div>}
        
        <form onSubmit={handleSubmit}>
          <div className="auth-form-group">
            <label htmlFor="signup-email">이메일</label>
            <input
              id="signup-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="이메일을 입력하세요"
              disabled={loading}
            />
          </div>
          
          <div className="auth-form-group">
            <label htmlFor="signup-password">비밀번호</label>
            <input
              id="signup-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="비밀번호를 입력하세요 (최소 8자)"
              disabled={loading}
              minLength={8}
            />
          </div>
          
          <div className="auth-form-group">
            <label htmlFor="signup-confirm">비밀번호 확인</label>
            <input
              id="signup-confirm"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              placeholder="비밀번호를 다시 입력하세요"
              disabled={loading}
              minLength={8}
            />
          </div>
          
          <button type="submit" className="auth-submit-btn" disabled={loading}>
            {loading ? '가입 중...' : '회원가입'}
          </button>
        </form>
        
        <div className="auth-switch">
          이미 계정이 있으신가요?{' '}
          <button type="button" onClick={onSwitchToLogin} className="auth-link-btn">
            로그인
          </button>
        </div>
      </div>
    </div>
  );
}

