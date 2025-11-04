// API 설정
export const API_CONFIG = {
  BASE_URL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  TIMEOUT: 30000, // 30초
  MAX_RETRIES: 3,
} as const;

// 파일 업로드 제한
export const UPLOAD_LIMITS = {
  MAX_FILES: 5,
  MAX_FILE_SIZE: 20 * 1024 * 1024, // 20MB (이미지)
  MAX_VIDEO_SIZE: 100 * 1024 * 1024, // 100MB (비디오)
  MAX_VIDEO_DURATION: 60, // 60초 (1분) - 비디오 길이 제한
  MAX_TEXT_LENGTH: 3000, // 3000자
  ALLOWED_IMAGE_TYPES: ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/heic', 'image/heif'],
  ALLOWED_VIDEO_TYPES: ['video/mp4', 'video/avi', 'video/mov', 'video/mkv', 'video/webm', 'video/flv', 'video/wmv'],
} as const;

// 탐지 옵션 타입
export const DETECTION_OPTIONS = {
  FACE: 'face',
  FINGERPRINT: 'fingerprint',
  PHONE: 'phone',
  RRN: 'rrn',
  PASSPORT: 'passport',
  IP_ADDRESS: 'ip_address',
  EMAIL: 'email',
  ACCOUNT: 'account',
  SCHOOL: 'school',
  WORKPLACE: 'workplace',
  NAME: 'name',
  ADDRESS: 'address',
  DRIVER_LICENSE: 'driverLicense',
  POSTAL_CODE: 'postalCode',
} as const;

// 에러 메시지
export const ERROR_MESSAGES = {
  FILE_TOO_LARGE: '파일 크기가 너무 큽니다',
  TOO_MANY_FILES: '파일은 최대 5개까지 업로드할 수 있습니다',
  INVALID_FILE_TYPE: '지원하지 않는 파일 형식입니다',
  VIDEO_TOO_LONG: '비디오는 최대 1분(60초)까지 업로드할 수 있습니다',
  TEXT_TOO_LONG: '텍스트는 최대 3,000자까지 입력할 수 있습니다',
  NETWORK_ERROR: '네트워크 오류가 발생했습니다',
  SERVER_ERROR: '서버 오류가 발생했습니다',
  VALIDATION_ERROR: '입력값 검증에 실패했습니다',
} as const;

// 성공 메시지
export const SUCCESS_MESSAGES = {
  UPLOAD_SUCCESS: '파일 업로드가 완료되었습니다',
  ANALYSIS_SUCCESS: '분석이 완료되었습니다',
} as const;


