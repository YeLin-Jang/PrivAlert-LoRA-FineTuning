import axios, { type AxiosInstance, type AxiosError } from 'axios';
import type { ApiResponse, AnalysisResult, DetectionOptions } from '../types';
import { API_CONFIG } from '../constants';
import { secureFormDataCleanup } from '../utils/security';

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

  // 요청 인터셉터 (보안: 민감 정보 로깅 방지)
  instance.interceptors.request.use(
    (config) => {
      // 개발 환경에서만 로깅
      if (import.meta.env.DEV) {
        console.log('API 요청:', {
          method: config.method,
          url: config.url,
          // 파일 데이터는 로깅하지 않음
        });
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

  // 응답 인터셉터 (에러 처리)
  instance.interceptors.response.use(
    (response) => response,
    (error: AxiosError) => {
      if (error.response) {
        const data = error.response.data as any;
        
        // 일반적인 에러 메시지만 반환 (보안: 상세한 서버 정보 노출 방지)
        const errorMessage = data?.error || data?.message || '서버 오류가 발생했습니다';
        
        return Promise.reject(new Error(errorMessage));
      } else if (error.request) {
        // 네트워크 오류 (서버에 도달하지 못함)
        // 보안: 네트워크 오류는 민감 정보를 포함하지 않으므로 안전하게 표시 가능
        return Promise.reject(new Error('네트워크 오류가 발생했습니다. 인터넷 연결을 확인해주세요.'));
      } else {
        // 요청 설정 오류
        return Promise.reject(new Error('요청 처리 중 오류가 발생했습니다'));
      }
    }
  );

  return instance;
};

const api = createApiInstance();

// 파일 업로드용 Axios 인스턴스
const fileApi = axios.create({
  baseURL: API_CONFIG.BASE_URL,
  timeout: API_CONFIG.TIMEOUT * 2, // 파일 업로드는 더 긴 타임아웃
  withCredentials: true, // 쿠키 전송을 위해 필요 (세션 인증)
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

/**
 * 통합 분석 API
 */
export const analyzeContent = async (
  files: File[],
  text: string,
  blurFingers: boolean = true,
  showFaces: boolean = false,
  detectionOptions?: DetectionOptions
): Promise<AnalysisResult> => {
  const formData = new FormData();
  
  // 파일 추가 (최대 5개)
  files.slice(0, 5).forEach((file) => {
    formData.append('image', file);
  });
  
  // 텍스트 추가 (최대 3000자)
  if (text.trim()) {
    formData.append('text', text.substring(0, 3000));
  }
  
  // 옵션 추가
  formData.append('blur_fingers', blurFingers.toString());
  formData.append('show_faces', showFaces.toString());
  
  // 탐지 옵션 추가
  if (detectionOptions) {
    Object.entries(detectionOptions as Record<string, boolean>).forEach(([key, value]) => {
      if (value) {
        formData.append(`detect_${key}`, 'true');
      }
    });
  }

  const response = await fileApi.post<ApiResponse<AnalysisResult>>('/api/v1/analyze', formData);
  
  // 보안: FormData 사용 후 정리 (메모리 해제)
  secureFormDataCleanup(formData);
  
  if (!response.data.success) {
    throw new Error(response.data.message || '분석 중 오류가 발생했습니다.');
  }
  
  return response.data.data!;
};

/**
 * 비디오 분석 API
 */
export const analyzeVideo = async (
  videoFile: File,
  extractAudio: boolean = true,
  processFrames: boolean = true,
  frameInterval: number = 1.0
): Promise<any> => {
  const formData = new FormData();
  formData.append('video', videoFile);
  formData.append('extract_audio', extractAudio.toString());
  formData.append('process_frames', processFrames.toString());
  formData.append('frame_interval', frameInterval.toString());

  const response = await fileApi.post('/api/v1/video/analyze', formData);
  
  // 보안: FormData 사용 후 정리
  secureFormDataCleanup(formData);
  
  if (!response.data.success) {
    throw new Error(response.data.error || '비디오 분석 중 오류가 발생했습니다.');
  }
  
  return response.data;
};

/**
 * 교육/수정 제안 API
 */
export const suggestEducation = async (
  maskedText: string,
  categories: Record<string, any>,
  language: string = 'ko',
  tone: string = 'educational'
) => {
  try {
    const response = await api.post(`${API_CONFIG.BASE_URL}/api/v1/education/suggest`, {
      masked_text: maskedText,
      categories,
      language,
      tone,
    });
    
    // 디버깅: 응답 구조 확인 (개발 환경에서만)
    if (import.meta.env.DEV) {
      console.log('교육 제안 응답:', {
        success: response.data?.success,
        hasData: !!response.data?.data,
        dataKeys: response.data?.data ? Object.keys(response.data.data) : [],
        fullResponse: response.data,
      });
    }
    
    // 응답 데이터 구조 확인
    if (!response || !response.data) {
      throw new Error('서버로부터 응답을 받지 못했습니다');
    }
    
    if (!response.data.success) {
      const errorMsg = response.data.error || response.data.message || '교육 제안 생성 실패';
      throw new Error(errorMsg);
    }
    
    // 응답 데이터 확인
    if (!response.data.data) {
      throw new Error('교육 제안 데이터가 없습니다');
    }
    
    return response.data.data;
  } catch (error: any) {
    // 디버깅: 에러 상세 정보 (개발 환경에서만)
    if (import.meta.env.DEV) {
      console.error('교육 제안 API 에러 상세:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        statusText: error.response?.statusText,
        request: error.request,
        isNetworkError: !error.response && error.request,
        isTimeout: error.code === 'ECONNABORTED',
      });
    }
    
    // 네트워크 오류인 경우 더 명확한 메시지
    if (!error.response && error.request) {
      throw new Error('네트워크 오류가 발생했습니다. 서버 연결을 확인해주세요.');
    }
    
    throw error;
  }
};

/**
 * 정형 데이터 필터링 API
 */
export const filterStructuredData = async (
  text: string,
  detectionOptions: Record<string, boolean> = {}
): Promise<any> => {
  // 활성화된 필터들만 추출
  const activeFilters = Object.entries(detectionOptions)
    .filter(([key, value]) => value && [
      'phone', 'rrn', 'passport', 'ip_address', 'email', 'account', 
      'school', 'workplace', 'address', 'name'
    ].includes(key))
    .map(([key]) => key);
  
  const response = await api.post('/api/v1/filter/filter', {
    text: text.substring(0, 3000), // 최대 3000자
    use_replacements: true,
    filters: activeFilters
  });
  
  return response.data;
};

/**
 * 이름 탐지 API
 */
export const detectNames = async (text: string) => {
  const response = await api.post(`${API_CONFIG.BASE_URL}/api/v1/name/detect`, {
    text: text.substring(0, 3000) // 최대 3000자
  });
  
  if (!response.data?.success) {
    throw new Error(response.data?.message || '이름 탐지 실패');
  }
  
  return response.data.data;
};

/**
 * 이름 마스킹 API
 */
export const maskNames = async (text: string) => {
  const response = await api.post(`${API_CONFIG.BASE_URL}/api/v1/name/mask`, {
    text: text.substring(0, 3000) // 최대 3000자
  });
  
  if (!response.data?.success) {
    throw new Error(response.data?.message || '이름 마스킹 실패');
  }
  
  return response.data.data;
};

/**
 * 직장명 탐지 API
 */
export const detectWorkplaces = async (text: string) => {
  const response = await api.post(`${API_CONFIG.BASE_URL}/api/v1/workplace/detect`, {
    text: text.substring(0, 3000) // 최대 3000자
  });
  
  if (!response.data?.success) {
    throw new Error(response.data?.message || '직장명 탐지 실패');
  }
  
  return response.data.data;
};

/**
 * 얼굴 탐지 API
 */
export const detectFaces = async (imageFile: File, returnImage: boolean = false) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('return_image', returnImage.toString());

  const response = await fileApi.post('/api/v1/face/detect', formData);
  return response.data;
};

/**
 * 손가락 탐지 API
 */
export const detectHands = async (imageFile: File, returnImage: boolean = false) => {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('return_image', returnImage.toString());

  const response = await fileApi.post('/api/v1/hand/detect', formData);
  return response.data;
};

/**
 * OCR 텍스트 추출 API
 */
export const extractOCRText = async (imageFile: File) => {
  const formData = new FormData();
  formData.append('file', imageFile);

  const response = await fileApi.post('/api/v1/ocr/text', formData);
  return response.data;
};

/**
 * 이미지 정제 API
 */
export const sanitizeImage = async (
  imageFile: File,
  targetFormat?: string,
  keepIcc: boolean = true
) => {
  const formData = new FormData();
  formData.append('file', imageFile);
  if (targetFormat) {
    formData.append('target_format', targetFormat);
  }
  formData.append('keep_icc', keepIcc.toString());

  const response = await fileApi.post('/api/v1/images/sanitize', formData, {
    responseType: 'blob',
  });
  
  return response.data;
};


