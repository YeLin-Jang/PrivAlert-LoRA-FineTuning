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
    // 초기 로드 시 세션 쿠키 확인 및 사용자 정보 조회
    // 세션 쿠키는 자동으로 전송되므로 localStorage 토큰 여부와 무관하게 확인
    const checkAuth = async () => {
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
        
        // 인증 실패 시 (401, 403 등)
        // localStorage에 user_email이 있으면 유지 (로그인 상태 유지)
        const storedEmail = localStorage.getItem('user_email');
        if (!storedEmail) {
          // 초기 로드이고 토큰도 없으면 비로그인 상태로 설정
          localStorage.removeItem('user_email');
          localStorage.removeItem('user_access_token');
          localStorage.removeItem('auth_token');
          localStorage.removeItem('csrf_token');
          localStorage.removeItem('session_id');
          setUser(null);
        }
        // 토큰이 있으면 사용자 정보는 유지 (세션 쿠키가 곧 설정될 수 있음)
      } catch (error) {
        // 네트워크 오류 등 - 사용자 정보는 유지 (일시적인 네트워크 문제일 수 있음)
        const storedEmail = localStorage.getItem('user_email');
        if (!storedEmail) {
          // 초기 로드이고 토큰도 없으면 비로그인 상태로 설정
          setUser(null);
        }
        // 토큰이 있으면 사용자 정보는 유지 (네트워크 복구 후 재확인 가능)
        console.debug('인증 확인 중 네트워크 오류:', error);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const handleLogin = async (email: string, password: string) => {
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
        .catch(error => {
          // 에러는 무시 (이미 user가 설정되어 있음)
          console.debug('사용자 정보 최신화 실패:', error);
        });
    } catch (error: any) {
      throw new Error(error.message || '로그인에 실패했습니다');
    }
  };

  const handleLogout = async () => {
    try {
      await userApi.logout();
    } catch (error) {
      console.error('로그아웃 오류:', error);
    } finally {
      localStorage.removeItem('user_email');
      localStorage.removeItem('user_access_token');
      localStorage.removeItem('auth_token');
      setUser(null);
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

