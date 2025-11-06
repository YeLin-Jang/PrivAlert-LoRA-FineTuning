import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import { userApi, type UserResponse } from '../services/userApi';

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
  const [loading, setLoading] = useState(true); // 초기 로딩 상태를 true로 설정 (인증 확인 중)

  useEffect(() => {
    // 보안: 공개 페이지에서는 불필요한 인증 API 호출을 하지 않음
    // 세션 쿠키나 localStorage에 인증 정보가 있을 때만 사용자 정보 조회
    const checkAuth = async () => {
      // localStorage에 세션 정보가 없으면 인증 API를 호출하지 않음 (보안: 불필요한 요청 방지)
      const sessionId = localStorage.getItem('session_id');
      const storedEmail = localStorage.getItem('user_email');
      const csrfToken = localStorage.getItem('csrf_token');
      
      // 인증 정보가 전혀 없으면 비로그인 상태로 설정하고 종료
      if (!sessionId && !storedEmail && !csrfToken) {
        setUser(null);
        setLoading(false);
        return;
      }
      
      // 인증 정보가 있을 때만 사용자 정보 조회 (보안: 필요한 경우에만 API 호출)
      try {
        // 백엔드 API는 /api/v1/user/me 사용 (세션 쿠키 기반)
        const { API_CONFIG } = await import('../constants');
        const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/user/me`, {
          method: 'GET',
          credentials: 'include', // 세션 쿠키 자동 전송
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data) {
            // 백엔드 응답: { success: true, data: { ...user data... } }
            const userData = data.data;
            setUser(userData);
            if (userData.email) {
              localStorage.setItem('user_email', userData.email);
            }
            setLoading(false);
            return; // 성공 시 종료
          }
        }
        
        // 인증 실패 시 (401, 403 등) - 세션이 만료되었거나 유효하지 않음
        if (response.status === 401 || response.status === 403) {
          // 세션이 만료되었으므로 모든 인증 정보 제거
          localStorage.removeItem('user_email');
          localStorage.removeItem('user_access_token');
          localStorage.removeItem('auth_token');
          localStorage.removeItem('csrf_token');
          localStorage.removeItem('session_id');
          setUser(null);
          setLoading(false);
          return;
        }
        
        // 기타 오류 (500 등)는 네트워크 문제로 간주
        // 기존 인증 정보는 유지 (일시적인 서버 문제일 수 있음)
        setLoading(false);
      } catch (error) {
        // 네트워크 오류 등 - 기존 인증 정보는 유지 (일시적인 네트워크 문제일 수 있음)
        // fetch 자체가 실패한 경우만 catch됨
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogin = async (email: string, password: string) => {
    setLoading(true); // 로그인 시작 시 로딩 상태 활성화
    try {
      // 백엔드 API는 /api/v1/auth/login을 사용 (email/password)
      const { API_CONFIG } = await import('../constants');
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = '로그인에 실패했습니다';
        let requiresVerification = false;
        
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.error || errorMessage;
          requiresVerification = errorData.requires_verification || false;
        } catch {
          // JSON 파싱 실패 시 상태 코드로 메시지 생성
          if (response.status === 404) {
            errorMessage = '서버를 찾을 수 없습니다. 백엔드 서버가 실행 중인지 확인하세요.';
          } else if (response.status === 401) {
            errorMessage = '이메일 또는 비밀번호가 올바르지 않습니다.';
          } else if (response.status === 403) {
            errorMessage = '이메일 인증이 필요합니다. 이메일을 확인해주세요.';
            requiresVerification = true;
          } else if (response.status === 500) {
            errorMessage = '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
          }
        }
        
        const error = new Error(errorMessage) as any;
        error.requiresVerification = requiresVerification;
        throw error;
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || '로그인 실패');
      }

      // 토큰 저장 (세션 쿠키는 자동으로 설정됨)
      if (data.data?.csrf_token) {
        localStorage.setItem('csrf_token', data.data.csrf_token);
      }
      if (data.data?.session_id) {
        localStorage.setItem('session_id', data.data.session_id);
      }

      // 사용자 정보 즉시 설정 (로그인 응답에 user 정보가 있으면 바로 사용)
      if (data.data?.user) {
        setUser(data.data.user);
        if (data.data.user.email) {
          localStorage.setItem('user_email', data.data.user.email);
        }
        setLoading(false); // 사용자 정보가 있으면 즉시 로딩 종료
      }

      // 사용자 정보 최신화 (백그라운드에서 실행, 실패해도 이미 user가 설정되어 있음)
      fetch(`${API_CONFIG.BASE_URL}/api/v1/user/me`, {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      })
        .then(userResponse => {
          if (userResponse.ok) {
            return userResponse.json();
          }
          return null;
        })
        .then(userData => {
          if (userData?.success && userData.data) {
            setUser(userData.data);
            if (userData.data.email) {
              localStorage.setItem('user_email', userData.data.email);
            }
          }
        })
        .catch(() => {
          // 에러는 무시 (이미 user가 설정되어 있음)
          // 보안: 콘솔 로그 제거
        })
        .finally(() => {
          setLoading(false); // 최신화 완료 후 로딩 종료
        });
    } catch (error: any) {
      setLoading(false); // 에러 발생 시에도 로딩 종료
      throw new Error(error.message || '로그인에 실패했습니다');
    }
  };

  const handleLogout = async () => {
    setLoading(true); // 로그아웃 시작 시 로딩 상태 활성화
    try {
      await userApi.logout();
    } catch (error) {
      // 보안: 콘솔 로그 제거
    } finally {
      localStorage.removeItem('user_email');
      localStorage.removeItem('user_access_token');
      localStorage.removeItem('auth_token');
      localStorage.removeItem('csrf_token');
      localStorage.removeItem('session_id');
      setUser(null);
      setLoading(false); // 로그아웃 완료 후 로딩 종료
    }
  };

  // localStorage에 user_email이 있으면 로그인 상태로 간주 (세션 쿠키 확인 중일 수 있음)
  const storedEmail = localStorage.getItem('user_email');
  const isAuthenticated = !!user || !!storedEmail;

  const value: UserAuthContextType = {
    user,
    loading,
    login: handleLogin,
    logout: handleLogout,
    isAuthenticated,
  };

  return <UserAuthContext.Provider value={value}>{children}</UserAuthContext.Provider>;
};

