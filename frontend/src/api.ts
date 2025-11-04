import axios from 'axios';
import type { ApiResponse, AnalysisResult } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
  withCredentials: true, // 쿠키 자동 전송
});

// JSON API용 별도 인스턴스
const jsonApi = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// 에러 인터셉터: 401/403은 정상적인 상황 (로그인 안 함)
jsonApi.interceptors.response.use(
  (response) => {
    console.log('[api.ts] 인터셉터: 응답 성공', response.config.url);
    return response;
  },
  (error) => {
    console.log('[api.ts] 인터셉터: 에러 발생', error.config?.url, error.response?.status);
    // 401/403은 로그인하지 않은 상태 (정상)
    if (error.response?.status === 401 || error.response?.status === 403) {
      console.log('[api.ts] 인터셉터: UNAUTHORIZED로 변환');
      // 에러를 다시 던지되, 특별한 메시지로 표시
      const customError = new Error('UNAUTHORIZED');
      (customError as any).response = error.response;
      return Promise.reject(customError);
    }
    return Promise.reject(error);
  }
);

// 요청 인터셉터: 요청 전송 확인
jsonApi.interceptors.request.use(
  (config) => {
    console.log('[api.ts] 인터셉터: 요청 전송', config.method?.toUpperCase(), config.url, config.baseURL);
    return config;
  },
  (error) => {
    console.error('[api.ts] 인터셉터: 요청 오류', error);
    return Promise.reject(error);
  }
);

// 통합 분석 API
export const analyzeContent = async (
  files: File[],
  text: string,
  blurFingers: boolean = true,
  showFaces: boolean = false,
  detectionOptions?: Record<string, boolean>
): Promise<AnalysisResult> => {
  const formData = new FormData();
  
  // 파일 추가
  files.forEach((file) => {
    formData.append('image', file);
  });
  
  // 텍스트 추가
  if (text.trim()) {
    formData.append('text', text);
  }
  
  // 옵션 추가
  formData.append('blur_fingers', blurFingers.toString());
  formData.append('show_faces', showFaces.toString());
  
  // 탐지 옵션 추가
  if (detectionOptions) {
    Object.entries(detectionOptions).forEach(([key, value]) => {
      formData.append(`detect_${key}`, value.toString());
    });
  }

  console.log('API 요청 전송:', { files: files.length, text: text.length, detectionOptions });
  const response = await api.post<ApiResponse<AnalysisResult>>('/api/v1/analyze', formData);
  console.log('API 응답:', response.data);
  
  if (!response.data.success) {
    throw new Error(response.data.message || '분석 중 오류가 발생했습니다.');
  }
  
  console.log('API 데이터:', response.data.data);
  return response.data.data!;
};

// 교육/수정 제안 API
export const suggestEducation = async (
  maskedText: string,
  categories: Record<string, any>,
  language: string = 'ko',
  tone: string = 'educational'
) => {
  const response = await axios.post(`${API_BASE}/api/v1/education/suggest`, {
    masked_text: maskedText,
    categories,
    language,
    tone,
  });
  if (!response.data?.success) {
    throw new Error(response.data?.error || '교육 제안 생성 실패');
  }
  return response.data.data;
};

// 정형 데이터 필터링 API
export const filterStructuredData = async (
  text: string,
  detectionOptions: Record<string, boolean> = {}
): Promise<any> => {
  // 활성화된 필터들만 추출
  const activeFilters = Object.entries(detectionOptions)
    .filter(([key, value]) => value && ['phone', 'rrn', 'passport', 'ip_address', 'email', 'account', 'school', 'workplace', 'address', 'driverLicense', 'postalCode', 'name'].includes(key))
    .map(([key]) => key);
  
  const response = await api.post('/api/v1/filter/filter', {
    text,
    use_replacements: true,
    filters: activeFilters
  });
  
  return response.data;
};

// 이름 탐지 API
export const detectNames = async (text: string) => {
  const response = await axios.post(`${API_BASE}/api/v1/name/detect`, {
    text
  }, {
    headers: {
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.data?.success) {
    throw new Error(response.data?.message || '이름 탐지 실패');
  }
  
  return response.data.data;
};

// 이름 마스킹 API
export const maskNames = async (text: string) => {
  const response = await axios.post(`${API_BASE}/api/v1/name/mask`, {
    text
  }, {
    headers: {
      'Content-Type': 'application/json'
    }
  });
  
  if (!response.data?.success) {
    throw new Error(response.data?.message || '이름 마스킹 실패');
  }
  
  return response.data.data;
};

// ==================== 인증 API ====================

export interface User {
  user_id: number;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  roles: string[];
  created_at?: string;
}

export interface AuthResponse {
  success: boolean;
  message?: string;
  data?: {
    user_id: number;
    email: string;
    is_admin: boolean;
  };
  error?: string;
}

// 회원가입
export const signup = async (email: string, password: string): Promise<AuthResponse> => {
  const response = await jsonApi.post<AuthResponse>('/api/v1/auth/signup', {
    email,
    password,
  });
  return response.data;
};

// 로그인
export const login = async (email: string, password: string): Promise<AuthResponse> => {
  const response = await jsonApi.post<AuthResponse>('/api/v1/auth/login', {
    email,
    password,
  });
  return response.data;
};

// 로그아웃
export const logout = async (): Promise<void> => {
  await jsonApi.post('/api/v1/auth/logout');
};

// 현재 사용자 정보 조회
export const getCurrentUser = async (): Promise<User> => {
  const url = `${API_BASE}/api/v1/auth/me`;
  console.log('[api.ts] getCurrentUser 호출:', url);
  
  try {
    console.log('[api.ts] axios 요청 전송 시작');
    const response = await jsonApi.get<{ success: boolean; data: User }>('/api/v1/auth/me');
    console.log('[api.ts] 응답 받음:', response.status, response.data);
    
    if (!response.data.success || !response.data.data) {
      console.error('[api.ts] 응답 데이터가 없음:', response.data);
      throw new Error('사용자 정보 조회 실패');
    }
    console.log('[api.ts] 사용자 정보 반환:', response.data.data.email);
    return response.data.data;
  } catch (error: any) {
    console.error('[api.ts] getCurrentUser 에러:', error);
    console.error('[api.ts] 에러 타입:', error.constructor.name);
    console.error('[api.ts] 에러 메시지:', error.message);
    console.error('[api.ts] 에러 response:', error.response);
    console.error('[api.ts] 에러 request:', error.request);
    
    // axios 에러 처리
    if (error.response) {
      console.log('[api.ts] HTTP 에러 응답 받음:', error.response.status);
      // 401 (Unauthorized) 또는 403 (Forbidden)은 로그인하지 않은 상태
      if (error.response.status === 401 || error.response.status === 403) {
        console.log('[api.ts] UNAUTHORIZED로 변환');
        throw new Error('UNAUTHORIZED');
      }
      // 다른 HTTP 에러
      throw new Error(`HTTP ${error.response.status}: ${error.response.statusText}`);
    }
    // 네트워크 에러 (서버 연결 안 됨)
    if (error.request) {
      console.log('[api.ts] 네트워크 에러 (요청은 보냈지만 응답 없음)');
      throw new Error('NETWORK_ERROR');
    }
    // 기타 에러
    if (error.message === 'UNAUTHORIZED') {
      throw error; // 이미 변환된 에러는 그대로 전달
    }
    console.error('[api.ts] 기타 에러:', error);
    throw error;
  }
};

// 비밀번호 변경
export const changePassword = async (
  currentPassword: string,
  newPassword: string
): Promise<void> => {
  const response = await jsonApi.post('/api/v1/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
  if (!response.data?.success) {
    throw new Error(response.data?.error || '비밀번호 변경 실패');
  }
};
