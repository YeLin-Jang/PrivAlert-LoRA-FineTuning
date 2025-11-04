import axios from 'axios';
import type { ApiResponse } from '../types';
import { removeSensitiveParams, safeRedirect } from '../utils/urlSecurity';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

// 관리자 API 인스턴스
const adminApi = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // 쿠키 전송을 위해 필요
});

// 요청 인터셉터: JWT 토큰을 헤더에 추가 (URL에는 절대 포함하지 않음)
adminApi.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('admin_access_token');
    if (token) {
      // 보안: 토큰은 Authorization 헤더에만 포함, URL에는 절대 포함하지 않음
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // 보안: URL에서 민감 정보 제거 (토큰, 비밀번호 등)
    if (config.url) {
      const fullUrl = config.baseURL 
        ? `${config.baseURL}${config.url.startsWith('/') ? '' : '/'}${config.url}`
        : `${API_BASE}${config.url.startsWith('/') ? '' : '/'}${config.url}`;
      config.url = removeSensitiveParams(fullUrl).replace(config.baseURL || API_BASE, '');
    }
    
    // 보안: params에서도 민감 정보 제거
    if (config.params) {
      const sensitiveParams = ['token', 'access_token', 'refresh_token', 'auth_token', 'password', 'secret', 'key'];
      sensitiveParams.forEach(param => {
        delete config.params[param];
      });
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터: 401 오류 시 토큰 갱신 시도
adminApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Refresh token으로 새 access token 발급
        const response = await axios.post(
          `${API_BASE}/api/v1/admin/auth/refresh`,
          {},
          { withCredentials: true }
        );
        
        const { access_token } = response.data.data;
        localStorage.setItem('admin_access_token', access_token);
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        
        return adminApi(originalRequest);
      } catch (refreshError) {
        // Refresh 실패 시 로그아웃 처리
        localStorage.removeItem('admin_access_token');
        // 보안: URL에서 민감 정보 제거 후 안전한 리다이렉트
        safeRedirect('/admin/login');
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// ============ 인증 관련 ============

export interface AdminLoginRequest {
  username: string;
  password: string;
}

export type AdminUser = {
  id: number;
  username: string;
  role: 'user' | 'admin' | 'super_admin';
};

export interface AdminLoginResponse {
  access_token: string;
  user: AdminUser;
}

export const adminLogin = async (credentials: AdminLoginRequest): Promise<AdminLoginResponse> => {
  const response = await axios.post<ApiResponse<AdminLoginResponse>>(
    `${API_BASE}/api/v1/admin/auth/login`,
    credentials,
    { withCredentials: true }
  );
  
  if (!response.data.success) {
    throw new Error(response.data.error || '로그인 실패');
  }
  
  const { access_token } = response.data.data!;
  localStorage.setItem('admin_access_token', access_token);
  
  return response.data.data!;
};

export const adminLogout = async (): Promise<void> => {
  await adminApi.post('/api/v1/admin/auth/logout');
  localStorage.removeItem('admin_access_token');
};

export const getCurrentAdmin = async (): Promise<AdminUser> => {
  const response = await adminApi.get<ApiResponse<AdminUser>>('/api/v1/admin/auth/me');
  if (!response.data.success) {
    throw new Error(response.data.error || '사용자 정보 조회 실패');
  }
  return response.data.data!;
};

export const changePassword = async (currentPassword: string, newPassword: string): Promise<void> => {
  const response = await adminApi.post('/api/v1/admin/auth/change-password', {
    current_password: currentPassword,
    new_password: newPassword,
  });
  if (!response.data.success) {
    throw new Error(response.data.error || '비밀번호 변경 실패');
  }
};

// ============ 사용자 관리 ============

export type User = {
  id: number;
  username: string;
  email?: string;
  role: 'user' | 'admin' | 'super_admin';
  is_active: boolean;
  created_at: string;
  last_login?: string;
};

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
  };
}

export const getUsers = async (
  page: number = 1,
  perPage: number = 10,
  search?: string,
  role?: string,
  isActive?: boolean
): Promise<PaginatedResponse<User>> => {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString(),
  });
  
  if (search) params.append('search', search);
  if (role) params.append('role', role);
  if (isActive !== undefined) params.append('is_active', isActive.toString());
  
  const response = await adminApi.get<ApiResponse<PaginatedResponse<User>>>(
    `/api/v1/admin/users?${params.toString()}`
  );
  
  if (!response.data.success) {
    throw new Error(response.data.error || '사용자 목록 조회 실패');
  }
  
  return response.data.data!;
};

export const getUser = async (userId: number): Promise<User> => {
  const response = await adminApi.get<ApiResponse<User>>(`/api/v1/admin/users/${userId}`);
  if (!response.data.success) {
    throw new Error(response.data.error || '사용자 조회 실패');
  }
  return response.data.data!;
};

export const updateUserStatus = async (userId: number, isActive: boolean): Promise<User> => {
  const response = await adminApi.patch<ApiResponse<User>>(
    `/api/v1/admin/users/${userId}/status`,
    { is_active: isActive }
  );
  if (!response.data.success) {
    throw new Error(response.data.error || '상태 변경 실패');
  }
  return response.data.data!;
};

export const updateUserRole = async (userId: number, role: 'user' | 'admin' | 'super_admin'): Promise<User> => {
  const response = await adminApi.patch<ApiResponse<User>>(
    `/api/v1/admin/users/${userId}/role`,
    { role }
  );
  if (!response.data.success) {
    throw new Error(response.data.error || '역할 변경 실패');
  }
  return response.data.data!;
};

export const getUserActivity = async (userId: number): Promise<any[]> => {
  const response = await adminApi.get<ApiResponse<{ logs: any[] }>>(
    `/api/v1/admin/users/${userId}/activity`
  );
  if (!response.data.success) {
    throw new Error(response.data.error || '활동 로그 조회 실패');
  }
  return response.data.data!.logs;
};

// ============ 로그 및 통계 ============

export const getActivityLogs = async (page: number = 1, perPage: number = 20): Promise<PaginatedResponse<any>> => {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString(),
  });
  
  const response = await adminApi.get<ApiResponse<PaginatedResponse<any>>>(
    `/api/v1/admin/logs/activity?${params.toString()}`
  );
  if (!response.data.success) {
    throw new Error(response.data.error || '활동 로그 조회 실패');
  }
  return response.data.data!;
};

export const getDetectionLogs = async (page: number = 1, perPage: number = 20): Promise<PaginatedResponse<any>> => {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString(),
  });
  
  const response = await adminApi.get<ApiResponse<PaginatedResponse<any>>>(
    `/api/v1/admin/logs/detection?${params.toString()}`
  );
  if (!response.data.success) {
    throw new Error(response.data.error || '탐지 로그 조회 실패');
  }
  return response.data.data!;
};

export const getDetectionStats = async (): Promise<any> => {
  const response = await adminApi.get<ApiResponse<any>>('/api/v1/admin/stats/detection');
  if (!response.data.success) {
    throw new Error(response.data.error || '탐지 통계 조회 실패');
  }
  return response.data.data!;
};

export const getUsageStats = async (): Promise<any> => {
  const response = await adminApi.get<ApiResponse<any>>('/api/v1/admin/stats/usage');
  if (!response.data.success) {
    throw new Error(response.data.error || '사용량 통계 조회 실패');
  }
  return response.data.data!;
};

// ============ 탐지 관리 ============

export interface Detection {
  id: number;
  user_id: number;
  type: string;
  text: string;
  risk_score: number;
  detected_at: string;
  status: string;
  masked_text?: string;
}

export const getDetections = async (
  page: number = 1,
  perPage: number = 20,
  type?: string,
  minRisk?: number
): Promise<PaginatedResponse<Detection>> => {
  const params = new URLSearchParams({
    page: page.toString(),
    per_page: perPage.toString(),
  });
  
  if (type) params.append('type', type);
  if (minRisk !== undefined) params.append('min_risk', minRisk.toString());
  
  const response = await adminApi.get<ApiResponse<PaginatedResponse<Detection>>>(
    `/api/v1/admin/detections?${params.toString()}`
  );
  if (!response.data.success) {
    throw new Error(response.data.error || '탐지 결과 조회 실패');
  }
  return response.data.data!;
};

export const getDetection = async (detectionId: number): Promise<Detection> => {
  const response = await adminApi.get<ApiResponse<Detection>>(`/api/v1/admin/detections/${detectionId}`);
  if (!response.data.success) {
    throw new Error(response.data.error || '탐지 결과 조회 실패');
  }
  return response.data.data!;
};

export const updateDetection = async (
  detectionId: number,
  updates: Partial<Detection>
): Promise<Detection> => {
  const response = await adminApi.patch<ApiResponse<Detection>>(
    `/api/v1/admin/detections/${detectionId}`,
    updates
  );
  if (!response.data.success) {
    throw new Error(response.data.error || '탐지 결과 수정 실패');
  }
  return response.data.data!;
};

// ============ 대시보드 ============

export const getDashboardOverview = async (): Promise<any> => {
  const response = await adminApi.get<ApiResponse<any>>('/api/v1/admin/dashboard/overview');
  if (!response.data.success) {
    throw new Error(response.data.error || '대시보드 데이터 조회 실패');
  }
  return response.data.data!;
};

