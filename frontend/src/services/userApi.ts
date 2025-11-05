import axios, { type AxiosInstance, type AxiosError } from 'axios';

const FASTAPI_BASE = import.meta.env.VITE_FASTAPI_BASE_URL || 'http://localhost:8000';

// 사용자 API 인스턴스
const userApi: AxiosInstance = axios.create({
  baseURL: FASTAPI_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // 쿠키 전송을 위해 필요
});

// 요청 인터셉터
userApi.interceptors.request.use(
  (config) => {
    // 토큰이 있다면 헤더에 추가 (향후 JWT 구현 시)
    const token = localStorage.getItem('user_access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터
userApi.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      const data = error.response.data as any;
      const errorMessage = data?.detail || data?.message || '서버 오류가 발생했습니다';
      return Promise.reject(new Error(errorMessage));
    } else if (error.request) {
      return Promise.reject(new Error('네트워크 오류가 발생했습니다'));
    } else {
      return Promise.reject(new Error('요청 처리 중 오류가 발생했습니다'));
    }
  }
);

// ============ 타입 정의 ============

export interface UserRegisterRequest {
  email: string;
  password: string;
}

export interface UserVerifyRequest {
  email: string;
  verification_code: string;
}

export interface UserResponse {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MessageResponse {
  message: string;
  success: boolean;
  verification_code?: string;
  debug_message?: string;
}

// ============ 인증 관련 ============

/**
 * 회원가입
 */
export const register = async (data: UserRegisterRequest): Promise<MessageResponse> => {
  const response = await userApi.post<MessageResponse>('/api/v1/register', data);
  return response.data;
};

/**
 * 이메일 인증
 */
export const verifyEmail = async (data: UserVerifyRequest): Promise<UserResponse> => {
  const response = await userApi.post<UserResponse>('/api/v1/verify-email', data);
  return response.data;
};

/**
 * 로그인
 */
export const login = async (data: UserRegisterRequest): Promise<UserResponse> => {
  const response = await userApi.post<UserResponse>('/api/v1/login', data);
  // 향후 JWT 토큰이 응답에 포함되면 여기서 저장
  if ((response.data as any).access_token) {
    localStorage.setItem('user_access_token', (response.data as any).access_token);
  }
  return response.data;
};

/**
 * 현재 사용자 정보 조회
 */
export const getCurrentUser = async (email: string): Promise<UserResponse> => {
  const response = await userApi.get<UserResponse>(`/api/v1/me?email=${encodeURIComponent(email)}`);
  return response.data;
};

/**
 * 로그아웃
 */
export const logout = async (): Promise<void> => {
  localStorage.removeItem('user_access_token');
  // 향후 로그아웃 API가 있으면 호출
};

