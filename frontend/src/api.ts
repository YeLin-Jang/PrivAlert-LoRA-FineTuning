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
  showFaces: boolean = false
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

  const response = await api.post<ApiResponse<AnalysisResult>>('/api/v1/analyze', formData);
  
  if (!response.data.success) {
    throw new Error(response.data.message || '분석 중 오류가 발생했습니다.');
  }
  
  return response.data.data!;
};

// 종교 필터링 API
export const filterText = async (
  text: string,
  useReplacements: boolean = true
): Promise<any> => {
  const response = await api.post('/api/filter/text', {
    text,
    use_replacements: useReplacements
  });
  
  return response.data;
};
