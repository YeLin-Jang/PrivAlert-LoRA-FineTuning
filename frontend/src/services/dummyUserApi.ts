/**
 * 더미 사용자 API (인증 없이 접근 가능)
 * 보안: 더미 데이터만 조회/수정 가능
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

  // 응답 인터셉터: 에러 처리
  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      const errorMessage = error.response?.data?.error || error.response?.data?.message || 'API 요청 중 오류가 발생했습니다.';
      return Promise.reject(new Error(errorMessage));
    }
  );

  return instance;
};

const api = createApiInstance();

export interface DemoUser {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  last_login?: string;
}

export interface FilteringSettings {
  id: number;
  user_id: number;
  detection_options: DetectionOptions;
  created_at: string;
  updated_at: string;
}

export interface RevisionHistory {
  id: number;
  user_id: number;
  revised_sentence: string;
  categories: string[];
  created_at: string;
  updated_at: string;
}

export interface DetectionOptions {
  face: boolean;
  fingerprint: boolean;
  phone: boolean;
  rrn: boolean;
  passport: boolean;
  ip_address: boolean;
  email: boolean;
  account: boolean;
  school: boolean;
  workplace: boolean;
  name: boolean;
  address: boolean;
  driverLicense: boolean;
  postalCode: boolean;
}

export const dummyUserApi = {
  /**
   * 더미 사용자 정보 조회
   */
  getDemoUser: async (): Promise<DemoUser> => {
    const response = await api.get('/api/v1/demo/user');
    // APIResponse.success는 data를 루트로 펼치므로 response.data.user로 접근
    return response.data.user;
  },

  /**
   * 더미 사용자 필터링 설정 조회
   */
  getFilteringSettings: async (): Promise<FilteringSettings> => {
    const response = await api.get('/api/v1/demo/filtering-settings');
    // APIResponse.success는 data를 루트로 펼치므로 response.data.settings로 접근
    return response.data.settings;
  },

  /**
   * 더미 사용자 필터링 설정 업데이트
   */
  updateFilteringSettings: async (detectionOptions: DetectionOptions): Promise<FilteringSettings> => {
    const response = await api.put('/api/v1/demo/filtering-settings', {
      detection_options: detectionOptions,
    });
    // APIResponse.success는 data를 루트로 펼치므로 response.data.settings로 접근
    return response.data.settings;
  },

  /**
   * 더미 사용자 수정 기록 조회
   */
  getRevisionHistory: async (page: number = 1, perPage: number = 20): Promise<{
    records: RevisionHistory[];
    pagination: {
      page: number;
      per_page: number;
      total: number;
      pages: number;
    };
  }> => {
    const response = await api.get('/api/v1/demo/revision-history', {
      params: { page, per_page: perPage },
    });
    // APIResponse.success는 data를 루트로 펼치므로 response.data.records로 접근
    return {
      records: response.data.records,
      pagination: response.data.pagination,
    };
  },

  /**
   * 더미 사용자 수정 기록 생성
   */
  createRevisionHistory: async (
    revisedSentence: string,
    categories?: string[]
  ): Promise<RevisionHistory> => {
    const response = await api.post('/api/v1/demo/revision-history', {
      revised_sentence: revisedSentence,
      categories: categories || [],
    });
    // APIResponse.success는 data를 루트로 펼치므로 response.data.record로 접근
    return response.data.record;
  },

  /**
   * 더미 사용자 기존 비밀번호 확인
   * 보안: 기존 비밀번호가 올바른지 확인
   */
  verifyPassword: async (currentPassword: string): Promise<void> => {
    const response = await api.post('/api/v1/demo/verify-password', {
      current_password: currentPassword,
    });
    return response.data;
  },

  /**
   * 더미 사용자 비밀번호 변경
   * 보안: 기존 비밀번호 확인 후 새 비밀번호로 변경
   */
  changePassword: async (
    currentPassword: string,
    newPassword: string
  ): Promise<void> => {
    const response = await api.put('/api/v1/demo/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    return response.data;
  },
};

