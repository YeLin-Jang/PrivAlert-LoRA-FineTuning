import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { login as loginApi, logout as logoutApi, getCurrentUser, signup as signupApi } from '../api';
import type { User } from '../api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  isAuthenticated: boolean;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  console.log('[AuthProvider] 초기화 시작');
  const [user, setUser] = useState<User | null>(null);
  // 초기 로딩을 false로 시작 - 즉시 화면 표시
  const [loading, setLoading] = useState(false);
  console.log('[AuthProvider] 초기 상태:', { user, loading });

  // 백그라운드에서 인증 상태 확인 (비동기)
  useEffect(() => {
    console.log('[AuthProvider] useEffect 실행 - 백그라운드에서 인증 확인 시작');
    // 화면을 먼저 표시하고, 백그라운드에서 인증 체크
    checkAuth();
  }, []);

  const checkAuth = async () => {
    console.log('========================================');
    console.log('[AuthContext] checkAuth 함수 시작!');
    console.log('[AuthContext] API_BASE:', import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000');
    console.log('[AuthContext] getCurrentUser 함수 존재 여부:', typeof getCurrentUser);
    
    // 타임아웃 설정 (3초)
    const timeoutPromise = new Promise<never>((_, reject) => {
      setTimeout(() => reject(new Error('TIMEOUT')), 3000);
    });

    try {
      console.log('[AuthContext] getCurrentUser 호출 직전');
      console.log('[AuthContext] getCurrentUser 함수:', getCurrentUser);
      
      const userData = await Promise.race([
        getCurrentUser(),
        timeoutPromise
      ]);
      
      console.log('[AuthContext] ✅ 사용자 정보 조회 성공:', userData.email);
      setUser(userData);
    } catch (error: any) {
      console.log('[AuthContext] ❌ 에러 발생:', error?.message);
      console.log('[AuthContext] 에러 상세:', error);
      console.log('[AuthContext] 에러 스택:', error?.stack);
      
      // 로그인하지 않은 상태는 정상적인 상황
      if (error?.message === 'UNAUTHORIZED') {
        // 로그인하지 않은 상태 - 정상
        console.log('[AuthContext] ✅ 로그인하지 않은 상태 (정상)');
        setUser(null);
      } else if (error?.message === 'TIMEOUT' || error?.message === 'NETWORK_ERROR') {
        // 타임아웃 또는 네트워크 오류 - 서버 연결 안 됨
        console.warn('[AuthContext] ⚠️ 서버 연결 확인 필요:', error?.message);
        console.warn('[AuthContext] 백엔드 서버가 실행 중인지 확인하세요:', import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000');
        setUser(null);
      } else {
        // 기타 오류
        console.error('[AuthContext] ❌ 인증 확인 오류:', error);
        console.error('[AuthContext] 에러 전체:', JSON.stringify(error, null, 2));
        setUser(null);
      }
    } finally {
      // 항상 로딩 상태를 해제하여 화면이 표시되도록
      console.log('[AuthContext] ✅ 로딩 완료 - loading을 false로 설정');
      console.log('========================================');
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await loginApi(email, password);
    if (response.success && response.data) {
      // 로그인 성공 후 사용자 정보 다시 가져오기
      const userData = await getCurrentUser();
      setUser(userData);
    } else {
      throw new Error(response.error || '로그인 실패');
    }
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch (error) {
      console.error('로그아웃 오류:', error);
    } finally {
      setUser(null);
    }
  };

  const signup = async (email: string, password: string) => {
    const response = await signupApi(email, password);
    if (!response.success) {
      throw new Error(response.error || '회원가입 실패');
    }
    // 회원가입 후 자동 로그인
    await login(email, password);
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    logout,
    signup,
    isAuthenticated: !!user,
    isAdmin: user?.is_admin || false,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

