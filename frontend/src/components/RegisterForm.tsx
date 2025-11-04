import { useState } from 'react';
import { register } from '../api';
import type { User } from '../types';
import './Auth.css';

interface RegisterFormProps {
  onRegisterSuccess: (user: User) => void;
  onSwitchToLogin: () => void;
}

export default function RegisterForm({ onRegisterSuccess, onSwitchToLogin }: RegisterFormProps) {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    fullName: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [passwordRequirements, setPasswordRequirements] = useState({
    length: false,
    upper: false,
    lower: false,
    digit: false
  });

  const validatePassword = (password: string) => {
    setPasswordRequirements({
      length: password.length >= 8,
      upper: /[A-Z]/.test(password),
      lower: /[a-z]/.test(password),
      digit: /[0-9]/.test(password)
    });
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    if (name === 'password') {
      validatePassword(value);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // 비밀번호 확인
    if (formData.password !== formData.confirmPassword) {
      setError('비밀번호가 일치하지 않습니다');
      return;
    }

    // 비밀번호 복잡도 확인
    const isValid = Object.values(passwordRequirements).every(req => req);
    if (!isValid) {
      setError('비밀번호가 요구사항을 만족하지 않습니다');
      return;
    }

    setLoading(true);

    try {
      const user = await register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        full_name: formData.fullName || undefined
      });
      onRegisterSuccess(user);
    } catch (err: any) {
      setError(err.message || '회원가입에 실패했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>회원가입</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">사용자명</label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              required
              minLength={3}
              maxLength={50}
              pattern="[a-zA-Z0-9_]+"
              title="영문, 숫자, 언더스코어만 사용 가능"
              autoComplete="username"
            />
          </div>
          <div className="form-group">
            <label htmlFor="email">이메일</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              maxLength={255}
              autoComplete="email"
            />
          </div>
          <div className="form-group">
            <label htmlFor="fullName">전체 이름 (선택)</label>
            <input
              type="text"
              id="fullName"
              name="fullName"
              value={formData.fullName}
              onChange={handleChange}
              maxLength={100}
              autoComplete="name"
            />
          </div>
          <div className="form-group">
            <label htmlFor="password">비밀번호</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              minLength={8}
              maxLength={128}
              autoComplete="new-password"
            />
            <div className="password-requirements">
              <div className={passwordRequirements.length ? 'requirement-met' : 'requirement-unmet'}>
                최소 8자 이상
              </div>
              <div className={passwordRequirements.upper ? 'requirement-met' : 'requirement-unmet'}>
                대문자 포함
              </div>
              <div className={passwordRequirements.lower ? 'requirement-met' : 'requirement-unmet'}>
                소문자 포함
              </div>
              <div className={passwordRequirements.digit ? 'requirement-met' : 'requirement-unmet'}>
                숫자 포함
              </div>
            </div>
          </div>
          <div className="form-group">
            <label htmlFor="confirmPassword">비밀번호 확인</label>
            <input
              type="password"
              id="confirmPassword"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              minLength={8}
              autoComplete="new-password"
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? '회원가입 중...' : '회원가입'}
          </button>
        </form>
        <div className="auth-switch">
          이미 계정이 있으신가요?{' '}
          <button type="button" onClick={onSwitchToLogin} className="btn-link">
            로그인
          </button>
        </div>
      </div>
    </div>
  );
}

