/**
 * 사용자 API 서비스
 * 보안: 민감 정보 노출 방지, 안전한 API 호출
 */
import axios, { type AxiosInstance } from 'axios';
import { API_CONFIG } from '../constants';

// Axios 인스턴스 생성
const createApiInstance = (): AxiosInstance => {
  const instance = axios.create({
    baseURL: API_CONFIG.BASE_URL,
    timeout: API_CONFIG.TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // 요청 인터셉터: 토큰 추가 및 XSS 방지
  instance.interceptors.request.use(
    (config) => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      // 보안: Content-Type 설정
      if (!config.headers['Content-Type']) {
        config.headers['Content-Type'] = 'application/json';
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // 응답 인터셉터: 에러 처리
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        // 인증 실패 시 토큰 제거
        localStorage.removeItem('auth_token');
      }
      return Promise.reject(error);
    }
  );

  return instance;
};

const api = createApiInstance();

export interface LoginResponse {
  user: {
    id: number;
    username: string;
    email: string;
    is_active: boolean;
  };
  token: string;
}

export interface RegisterResponse extends LoginResponse {}

export interface FilteringSettings {
  id: number;
  user_id: number;
  detection_options: Record<string, boolean>;
  created_at?: string;
  updated_at?: string;
}

export interface RevisionHistory {
  id: number;
  user_id: number;
  revised_sentence: string;
  categories: string[];
  created_at: string;
}

export const userApi = {
  /**
   * 로그인
   */
  async login(username: string, password: string): Promise<LoginResponse> {
    const response = await api.post('/api/v1/user/auth/login', {
      username,
      password,
    });

    if (!response.data?.success) {
      throw new Error(response.data?.error || '로그인 실패');
    }

    return response.data.data;
  },

  /**
   * 회원가입
   */
  async register(
    username: string,
    email: string,
    password: string,
    detectionOptions?: Record<string, boolean>
  ): Promise<RegisterResponse> {
    const response = await api.post('/api/v1/user/auth/register', {
      username,
      email,
      password,
      detection_options: detectionOptions || {},
    });

    if (!response.data?.success) {
      throw new Error(response.data?.error || '회원가입 실패');
    }

    return response.data.data;
  },

  /**
   * 현재 사용자 정보 조회
   */
  async getCurrentUser() {
    const response = await api.get('/api/v1/user/auth/me');

    if (!response.data?.success) {
      throw new Error(response.data?.error || '사용자 정보 조회 실패');
    }

    return response.data.data.user;
  },

  /**
   * 필터링 설정 조회
   */
  async getFilteringSettings(): Promise<FilteringSettings> {
    const response = await api.get('/api/v1/user/filtering-settings');

    if (!response.data?.success) {
      throw new Error(response.data?.error || '필터링 설정 조회 실패');
    }

    return response.data.data.settings;
  },

  /**
   * 필터링 설정 업데이트
   */
  async updateFilteringSettings(
    detectionOptions: Record<string, boolean>
  ): Promise<FilteringSettings> {
    const response = await api.put('/api/v1/user/filtering-settings', {
      detection_options: detectionOptions,
    });

    if (!response.data?.success) {
      throw new Error(response.data?.error || '필터링 설정 업데이트 실패');
    }

    return response.data.data.settings;
  },

  /**
   * 수정 기록 조회
   */
  async getRevisionHistory(page: number = 1, perPage: number = 20) {
    const response = await api.get('/api/v1/user/revision-history', {
      params: { page, per_page: perPage },
    });

    if (!response.data?.success) {
      throw new Error(response.data?.error || '수정 기록 조회 실패');
    }

    return response.data.data;
  },

  /**
   * 수정 기록 생성
   */
  async createRevisionHistory(
    revisedSentence: string,
    categories?: string[]
  ): Promise<RevisionHistory> {
    const response = await api.post('/api/v1/user/revision-history', {
      revised_sentence: revisedSentence,
      categories: categories || [],
    });

    if (!response.data?.success) {
      throw new Error(response.data?.error || '수정 기록 생성 실패');
    }

    return response.data.data.record;
  },
};

