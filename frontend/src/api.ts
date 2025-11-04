import axios from 'axios';
import type { ApiResponse, AnalysisResult, User, LoginRequest, RegisterRequest, SessionStatus } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// CSRF 토큰 저장
let csrfToken: string | null = null;

// 기본 axios 인스턴스
const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // 쿠키 포함
  headers: {
    'Content-Type': 'application/json',
  },
});

// CSRF 토큰 가져오기
export const getCsrfToken = async (): Promise<string | null> => {
  try {
    const response = await api.get<ApiResponse<{ csrf_token: string }>>('/api/v1/auth/csrf-token');
    if (response.data.success && response.data.data?.csrf_token) {
      csrfToken = response.data.data.csrf_token;
      return csrfToken;
    }
    return null;
  } catch (error) {
    console.error('CSRF 토큰 가져오기 실패:', error);
    return null;
  }
};

// 요청 인터셉터: CSRF 토큰 추가
api.interceptors.request.use(async (config) => {
  // CSRF 토큰이 없으면 가져오기
  if (!csrfToken && config.url !== '/api/v1/auth/csrf-token') {
    await getCsrfToken();
  }
  
  // CSRF 토큰 헤더 추가
  if (csrfToken && config.method !== 'get') {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  
  return config;
});

// 응답 인터셉터: CSRF 토큰 갱신
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    // 403 오류 시 CSRF 토큰 갱신
    if (error.response?.status === 403) {
      csrfToken = null;
      await getCsrfToken();
    }
    return Promise.reject(error);
  }
);

// 파일 업로드용 axios 인스턴스
const fileApi = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

fileApi.interceptors.request.use(async (config) => {
  if (!csrfToken) {
    await getCsrfToken();
  }
  if (csrfToken) {
    config.headers['X-CSRF-Token'] = csrfToken;
  }
  return config;
});

// 통합 분석 API
export const analyzeContent = async (
  files: File[],
  text: string,
  blurFingers: boolean = true,
  showFaces: boolean = false,
  detectionOptions?: Record<string, boolean>
): Promise<AnalysisResult> => {
  await getCsrfToken();
  
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
  
  // CSRF 토큰 추가
  if (csrfToken) {
    formData.append('csrf_token', csrfToken);
  }
  
  // 탐지 옵션 추가
  if (detectionOptions) {
    Object.entries(detectionOptions).forEach(([key, value]) => {
      formData.append(`detect_${key}`, value.toString());
    });
  }

  console.log('API 요청 전송:', { files: files.length, text: text.length, detectionOptions });
  const response = await fileApi.post<ApiResponse<AnalysisResult>>('/api/v1/analyze', formData);
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
  await getCsrfToken();
  
  const response = await api.post('/api/v1/education/suggest', {
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
  await getCsrfToken();
  
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
  await getCsrfToken();
  
  const response = await api.post('/api/v1/name/detect', {
    text
  });
  
  if (!response.data?.success) {
    throw new Error(response.data?.message || '이름 탐지 실패');
  }
  
  return response.data.data;
};

// 이름 마스킹 API
export const maskNames = async (text: string) => {
  const response = await api.post('/api/v1/name/mask', {
    text
  });
  
  if (!response.data?.success) {
    throw new Error(response.data?.message || '이름 마스킹 실패');
  }
  
  return response.data.data;
};

// ========== 인증 API ==========

// 회원가입
export const register = async (data: RegisterRequest): Promise<User> => {
  // CSRF 토큰 가져오기
  await getCsrfToken();
  
  const response = await api.post<ApiResponse<{ user: User }>>('/api/v1/auth/register', data);
  
  if (!response.data.success) {
    throw new Error(response.data.error || '회원가입 실패');
  }
  
  return response.data.data!.user;
};

// 로그인
export const login = async (data: LoginRequest): Promise<{ user: User; session_id: string }> => {
  // CSRF 토큰 가져오기
  await getCsrfToken();
  
  const response = await api.post<ApiResponse<{ user: User; session_id: string }>>('/api/v1/auth/login', data);
  
  if (!response.data.success) {
    throw new Error(response.data.error || '로그인 실패');
  }
  
  return response.data.data!;
};

// 로그아웃
export const logout = async (): Promise<void> => {
  await getCsrfToken();
  
  const response = await api.post<ApiResponse>('/api/v1/auth/logout');
  
  if (!response.data.success) {
    throw new Error(response.data.error || '로그아웃 실패');
  }
  
  csrfToken = null; // CSRF 토큰 초기화
};

// 현재 사용자 정보 조회
export const getCurrentUser = async (): Promise<User> => {
  const response = await api.get<ApiResponse<{ user: User }>>('/api/v1/auth/me');
  
  if (!response.data.success) {
    throw new Error(response.data.error || '사용자 정보 조회 실패');
  }
  
  return response.data.data!.user;
};

// 세션 확인
export const checkSession = async (): Promise<SessionStatus> => {
  const response = await api.get<ApiResponse<SessionStatus>>('/api/v1/auth/session');
  
  if (!response.data.success) {
    return { authenticated: false };
  }
  
  return response.data.data || { authenticated: false };
};

// ========== 통합 분석 API (기존) ==========
