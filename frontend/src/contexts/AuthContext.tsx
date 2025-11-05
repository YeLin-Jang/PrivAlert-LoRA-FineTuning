/**
 * 사용자 인증 컨텍스트
 * 보안: 민감 정보는 메모리에만 저장, 로컬 스토리지에는 토큰만 저장
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { userApi } from '../services/userApi';

interface User {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  last_login?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string, detectionOptions?: Record<string, boolean>) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    // 보안: 로컬 스토리지에서 토큰 제거
    localStorage.removeItem('auth_token');
  }, []);

  const refreshUser = useCallback(async () => {
    const currentToken = localStorage.getItem('auth_token');
    if (!currentToken) return;
    
    try {
      const userData = await userApi.getCurrentUser();
      setUser(userData);
    } catch (error) {
      // 토큰이 유효하지 않으면 로그아웃
      setUser(null);
      setToken(null);
      localStorage.removeItem('auth_token');
    }
  }, []);

  // 보안: 토큰을 로컬 스토리지에서 로드 (민감 정보는 저장하지 않음)
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    if (storedToken) {
      setToken(storedToken);
      // 토큰이 있으면 사용자 정보 조회
      refreshUser().finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [refreshUser]);

  const login = async (username: string, password: string) => {
    try {
      const response = await userApi.login(username, password);
      setUser(response.user);
      setToken(response.token);
      // 보안: 토큰만 로컬 스토리지에 저장
      localStorage.setItem('auth_token', response.token);
    } catch (error) {
      throw error;
    }
  };

  const register = async (
    username: string,
    email: string,
    password: string,
    detectionOptions?: Record<string, boolean>
  ) => {
    try {
      const response = await userApi.register(username, email, password, detectionOptions);
      setUser(response.user);
      setToken(response.token);
      // 보안: 토큰만 로컬 스토리지에 저장
      localStorage.setItem('auth_token', response.token);
    } catch (error) {
      throw error;
    }
  };


  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

