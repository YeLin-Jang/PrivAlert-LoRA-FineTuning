// API 응답 타입
export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  error?: string;
  code?: number;
  data?: T;
}

// 분석 결과 타입
export interface AnalysisResult {
  face_detection?: any;
  hand_detection?: any;
  text_analysis?: any;
  summary?: any;
}

// 사용자 타입
export interface User {
  id: number;
  username: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  roles: string[];
  created_at?: string;
  last_login_at?: string;
}

// 로그인 요청
export interface LoginRequest {
  username: string;
  password: string;
}

// 회원가입 요청
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name?: string;
}

// 세션 상태
export interface SessionStatus {
  authenticated: boolean;
  user?: User;
}
