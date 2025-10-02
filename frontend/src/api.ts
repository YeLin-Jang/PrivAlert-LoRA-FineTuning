import axios from 'axios';
import type { 
  ApiResponse, 
  AnalysisResult, 
  NameDetectionResult, 
  NameMaskingResult, 
  NameRewritingResult, 
  NameProcessingResult 
} from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

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
    .filter(([key, value]) => value && ['phone', 'rrn', 'passport', 'ip_address', 'email', 'account', 'school'].includes(key))
    .map(([key]) => key);
  
  const response = await api.post('/api/v1/filter/filter', {
    text,
    use_replacements: true,
    filters: activeFilters
  });
  
  return response.data;
};

// 이름 탐지 API
export const detectNames = async (text: string): Promise<NameDetectionResult> => {
  const response = await api.post<ApiResponse<NameDetectionResult>>('/api/v1/name/detect', {
    text
  });
  
  if (!response.data.success) {
    throw new Error(response.data.error || '이름 탐지 중 오류가 발생했습니다.');
  }
  
  return response.data.data!;
};

// 이름 마스킹 API
export const maskNames = async (text: string, maskChar: string = '*'): Promise<NameMaskingResult> => {
  const response = await api.post<ApiResponse<NameMaskingResult>>('/api/v1/name/mask', {
    text,
    mask_char: maskChar
  });
  
  if (!response.data.success) {
    throw new Error(response.data.error || '이름 마스킹 중 오류가 발생했습니다.');
  }
  
  return response.data.data!;
};

// 텍스트 리라이팅 API
export const rewriteText = async (text: string, useOpenAI: boolean = false): Promise<NameRewritingResult> => {
  const response = await api.post<ApiResponse<NameRewritingResult>>('/api/v1/name/rewrite', {
    text,
    use_openai: useOpenAI
  });
  
  if (!response.data.success) {
    throw new Error(response.data.error || '텍스트 리라이팅 중 오류가 발생했습니다.');
  }
  
  return response.data.data!;
};

// 이름 처리 통합 API
export const processNames = async (
  text: string, 
  maskChar: string = '*', 
  useOpenAI: boolean = false
): Promise<NameProcessingResult> => {
  const response = await api.post<ApiResponse<NameProcessingResult>>('/api/v1/name/process', {
    text,
    mask_char: maskChar,
    use_openai: useOpenAI
  });
  
  if (!response.data.success) {
    throw new Error(response.data.error || '이름 처리 중 오류가 발생했습니다.');
  }
  
  return response.data.data!;
};

// 이름 탐지 서비스 상태 확인 API
export const getNameDetectionStatus = async () => {
  const response = await api.get<ApiResponse<{
    model_loaded: boolean;
    device: string;
    service_status: string;
  }>>('/api/v1/name/status');
  
  if (!response.data.success) {
    throw new Error(response.data.error || '서비스 상태 확인 중 오류가 발생했습니다.');
  }
  
  return response.data.data!;
};
