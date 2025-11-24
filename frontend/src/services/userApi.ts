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
    withCredentials: true, // 쿠키 전송을 위해 필요 (세션 인증)
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
      // CSRF 토큰 추가 (세션 기반 인증)
      const csrfToken = localStorage.getItem('csrf_token');
      if (csrfToken) {
        config.headers['X-CSRF-Token'] = csrfToken;
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
      // 타임아웃 에러 처리
      if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
        return Promise.reject(new Error('요청 시간이 초과되었습니다. 서버 응답이 지연되고 있습니다. 잠시 후 다시 시도해주세요.'));
      }
      
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
    username?: string;
    email: string;
    nickname?: string;
    is_active: boolean;
  };
  token: string;
}

export interface RegisterResponse extends LoginResponse {
  verification_code?: string; // 개발 모드에서만 제공
}

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

// UserResponse는 백엔드 /api/v1/user/me 응답 구조와 일치
export interface UserResponse {
  id: number;
  email: string;
  nickname?: string;
  email_verified: boolean;
  email_verified_at?: string;
  mfa_enabled: boolean;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  last_login?: string;
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
      // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
      throw new Error('로그인에 실패했습니다. 이메일과 비밀번호를 확인해주세요.');
    }

    return response.data.data;
  },

  /**
   * 회원가입
   */
  async register(
    _username: string,
    email: string,
    password: string,
    nickname?: string,
    _detectionOptions?: Record<string, boolean>
  ): Promise<RegisterResponse> {
    try {
      // 백엔드 API는 /api/v1/auth/signup 사용 (API_CONFIG.BASE_URL 사용)
      const response = await fetch(`${API_CONFIG.BASE_URL}/api/v1/auth/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email,
          password,
          nickname: nickname || undefined,
        }),
      });

      if (!response.ok) {
        let errorMessage = '회원가입에 실패했습니다';
        
        // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
        // HTTP 상태 코드에 따라 일반화된 메시지만 반환
        if (response.status === 400) {
          errorMessage = '입력 정보를 확인해주세요.';
        } else if (response.status === 404) {
          errorMessage = '서버를 찾을 수 없습니다. 잠시 후 다시 시도해주세요.';
        } else if (response.status === 409) {
          errorMessage = '이미 등록된 이메일입니다.';
        } else if (response.status === 500) {
          errorMessage = '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
        } else {
          errorMessage = '회원가입에 실패했습니다. 잠시 후 다시 시도해주세요.';
        }
        
        throw new Error(errorMessage);
      }

      let data: any;
      try {
        data = await response.json();
      } catch (jsonError) {
        // 보안: 콘솔 로그 제거
        throw new Error('서버 응답을 처리할 수 없습니다');
      }

      if (!data || !data.success) {
        // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
        throw new Error('회원가입에 실패했습니다. 잠시 후 다시 시도해주세요.');
      }

      // 응답 형식 변환 (백엔드 응답에 맞춤)
      // 백엔드 응답: { success: true, data: { email } }
      // 실무: 인증 코드는 이메일로만 전송되므로 응답에 포함되지 않음
      const responseData = data.data || {};

      return {
        user: {
          id: 0, // 이메일 인증 완료 전까지는 user_id가 없음
          username: email.split('@')[0],
          email: responseData.email || email,
          is_active: false, // 이메일 인증 전까지 비활성화
        },
        token: '', // 이제 토큰 대신 코드 사용
        verification_code: undefined, // 실무: 코드는 응답에 포함하지 않음
      };
    } catch (error: any) {
      // 네트워크 에러 등 기타 에러 처리
      if (error instanceof TypeError && error.message.includes('fetch')) {
        throw new Error('네트워크 오류가 발생했습니다. 인터넷 연결을 확인하세요.');
      }
      throw error;
    }
  },

  /**
   * 현재 사용자 정보 조회
   */
  async getCurrentUser(): Promise<UserResponse> {
    const response = await api.get('/api/v1/user/me');

    if (!response.data?.success) {
      // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
      throw new Error('사용자 정보를 불러올 수 없습니다.');
    }

    // 백엔드 응답 형식: APIResponse.success(data={**user.to_dict(), "csrf_token": ...})
    // 최종 응답: {"success": true, "message": "...", "id": ..., "email": ..., "nickname": ..., "csrf_token": ...}
    // user 정보와 csrf_token이 최상위 레벨에 있음 (APIResponse.success는 response_data.update(data) 사용)
    const userData = response.data.data || response.data;
    
    // CSRF 토큰 저장 (백엔드에서 제공하는 경우)
    if (userData?.csrf_token) {
      localStorage.setItem('csrf_token', userData.csrf_token);
    }
    
    // userData에서 불필요한 필드 제거
    const { csrf_token, success, message, code, error, ...userInfo } = userData || {};
    
    return userInfo as UserResponse;
  },

  /**
   * 로그아웃
   */
  async logout(): Promise<void> {
    try {
      await api.post('/api/v1/auth/logout');
    } catch (error) {
      // 로그아웃 API 호출 실패해도 토큰은 제거
      // 보안: 콘솔 로그 제거
    } finally {
      localStorage.removeItem('auth_token');
      localStorage.removeItem('user_email');
      localStorage.removeItem('user_access_token');
      localStorage.removeItem('csrf_token');
      localStorage.removeItem('session_id');
    }
  },

  /**
   * 필터링 설정 조회
   */
  async getFilteringSettings(): Promise<FilteringSettings> {
    const response = await api.get('/api/v1/user/filtering-settings');

    if (!response.data?.success) {
      // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
      throw new Error('필터링 설정을 불러올 수 없습니다.');
    }

    // APIResponse.success에서 data={'settings': ...}를 update하므로
    // 최종 응답: {"success": true, "message": "...", "settings": {...}}
    // 안전하게 접근하기 위해 옵셔널 체이닝 사용
    const settings = response.data.settings || response.data.data?.settings;
    if (!settings) {
      throw new Error('필터링 설정 데이터를 찾을 수 없습니다.');
    }
    return settings;
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
      // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
      throw new Error('필터링 설정을 저장할 수 없습니다.');
    }

    // APIResponse.success에서 data={'settings': ...}를 update하므로
    // 최종 응답: {"success": true, "message": "...", "settings": {...}}
    // 안전하게 접근하기 위해 옵셔널 체이닝 사용
    const settings = response.data.settings || response.data.data?.settings;
    if (!settings) {
      throw new Error('필터링 설정 데이터를 찾을 수 없습니다.');
    }
    return settings;
  },

  /**
   * 수정 기록 조회
   */
  async getRevisionHistory(page: number = 1, perPage: number = 20) {
    const response = await api.get('/api/v1/user/revision-history', {
      params: { page, per_page: perPage },
    });

    if (!response.data?.success) {
      // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
      throw new Error('수정 기록을 불러올 수 없습니다.');
    }

    // APIResponse.success에서 data={'records': ..., 'pagination': ...}를 update하므로
    // 최종 응답: {"success": true, "message": "...", "records": [...], "pagination": {...}}
    // records와 pagination이 최상위 레벨에 있음
    return {
      records: response.data.records || [],
      pagination: response.data.pagination || {}
    };
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
      // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
      throw new Error('수정 기록을 저장할 수 없습니다.');
    }

    // APIResponse.success에서 data={'record': ...}를 update하므로
    // 최종 응답: {"success": true, "message": "...", "record": {...}}
    return response.data.record;
  },
};

/**
 * 이메일 인증 (FastAPI 백엔드 사용)
 */
export const verifyEmail = async (data: {
  email: string;
  verification_code: string;
}): Promise<void> => {
  // FastAPI 백엔드 URL (환경 변수 또는 기본값)
  const fastApiUrl = import.meta.env.VITE_FASTAPI_BASE_URL || 'http://localhost:8000';
  
  try {
    const response = await axios.post(
      `${fastApiUrl}/api/v1/verify-email`,
      {
        email: data.email,
        verification_code: data.verification_code,
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
        timeout: 30000,
      }
    );

    // FastAPI는 성공 시 200 상태 코드 반환
    if (response.status !== 200) {
      // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
      throw new Error('이메일 인증에 실패했습니다. 인증 코드를 확인해주세요.');
    }
  } catch (error: any) {
    // 보안: 상세한 서버 에러 정보는 사용자에게 노출하지 않음
    // FastAPI 에러 응답 형식 처리
    if (error.response?.status === 400) {
      throw new Error('인증 코드가 올바르지 않습니다. 다시 확인해주세요.');
    } else if (error.response?.status === 404) {
      throw new Error('인증 요청을 찾을 수 없습니다. 다시 시도해주세요.');
    } else if (error.response?.status === 410) {
      throw new Error('인증 코드가 만료되었습니다. 다시 요청해주세요.');
    } else {
      throw new Error('이메일 인증에 실패했습니다. 잠시 후 다시 시도해주세요.');
    }
  }
};

