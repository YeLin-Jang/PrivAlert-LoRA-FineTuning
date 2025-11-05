import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { login, logout, getCurrentUser, type UserResponse } from '../services/userApi';

interface UserAuthContextType {
  user: UserResponse | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  isAuthenticated: boolean;
}

const UserAuthContext = createContext<UserAuthContextType | undefined>(undefined);

export const useUserAuth = () => {
  const context = useContext(UserAuthContext);
  if (!context) {
    throw new Error('useUserAuth must be used within UserAuthProvider');
  }
  return context;
};

interface UserAuthProviderProps {
  children: ReactNode;
}

export const UserAuthProvider: React.FC<UserAuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(false); // 초기값을 false로 변경 (비동기 체크는 백그라운드에서)

  useEffect(() => {
    // 초기 로드 시 저장된 사용자 정보 확인 (비동기, 블로킹하지 않음)
    const checkAuth = async () => {
      const storedEmail = localStorage.getItem('user_email');
      if (storedEmail) {
        setLoading(true); // 사용자 정보 확인 중일 때만 로딩 표시
        try {
          const currentUser = await getCurrentUser(storedEmail);
          setUser(currentUser);
        } catch (error) {
          // 토큰이 유효하지 않으면 제거 (에러를 무시하고 계속 진행)
          localStorage.removeItem('user_email');
          localStorage.removeItem('user_access_token');
          setUser(null);
        } finally {
          setLoading(false);
        }
      }
    };

    checkAuth();
  }, []);

  const handleLogin = async (email: string, password: string) => {
    try {
      const response = await login({ email, password });
      setUser(response);
      localStorage.setItem('user_email', email);
    } catch (error) {
      throw error;
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('로그아웃 오류:', error);
    } finally {
      localStorage.removeItem('user_email');
      localStorage.removeItem('user_access_token');
      setUser(null);
    }
  };

  const value: UserAuthContextType = {
    user,
    loading,
    login: handleLogin,
    logout: handleLogout,
    isAuthenticated: !!user,
  };

  return <UserAuthContext.Provider value={value}>{children}</UserAuthContext.Provider>;
};

