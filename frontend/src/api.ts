import axios from 'axios';
import type { ApiResponse, AnalysisResult } from './types';

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
