// 백엔드 API 응답 타입
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  error?: string;
  code?: number;
}

// 통합 분석 결과 타입
export interface AnalysisResult {
  face_detection?: {
    total_count: number;
    message: string;
    images: FaceImage[];
  };
  hand_detection?: {
    total_count: number;
    message: string;
    images: HandImage[];
  };
  text_analysis?: {
    original_text: string;
    masked_text: string;
    statistics: FilterStats;
    structured_data?: {
      detected: boolean;
      total_count: number;
      categories: {
        [key: string]: {
          count: number;
          items: Array<{
            type: string;
            value: string;
            category: string;
          }>;
        };
      };
    };
  };
  summary: {
    faces_detected: number;
    fingers_detected: number;
    sensitive_text_found: boolean;
    message: string;
  };
  image_sanitization?: {
    message: string;
    items: SanitizedItem[];
  };
  ocr_text?: {
    texts: string[];
    total_count: number;
    message: string;
  };
}

export interface SanitizedItem {
  image_index: number;
  filename: string;
  sanitized_filename: string;
  sanitized_url: string;
  report: {
    source_format: string;
    target_format: string;
    exif_removed: boolean;
    gps_removed: boolean;
    size: number;
  };
  summary_ko?: string;
  details_ko?: {
    exif?: string;
    gps?: string;
    format?: string;
    size?: string | null;
  };
}

// 얼굴 감지 이미지
export interface FaceImage {
  image_index: number;
  filename: string;
  count: number;
  faces?: Face[];
  result_image_url?: string;
}

// 손가락 감지 이미지
export interface HandImage {
  image_index: number;
  filename: string;
  count: number;
  fingers?: Finger[];
  result_image_url?: string;
}

// 얼굴 정보
export interface Face {
  index: number;
  box: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
  score: number;
}

// 손가락 정보
export interface Finger {
  index: number;
  pos: {
    x: number;
    y: number;
  };
}


// 필터 통계
export interface FilterStats {
  total_detected: number;
  total_words: number;
  detection_rate: number;
  applied_filters: string[];
}
