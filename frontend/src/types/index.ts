// 백엔드 API 응답 타입
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  error?: string;
  code?: number;
}

// 개별 서비스 결과 타입들
export interface FaceResult {
  success: boolean;
  count: number;
  faces: Array<{
    index: number;
    box: {
      x: number;
      y: number;
      w: number;
      h: number;
    };
    score: number;
  }>;
  message: string;
  result_image_url?: string;
}

export interface HandResult {
  success: boolean;
  count: number;
  fingers: Array<{
    index: number;
    pos: {
      x: number;
      y: number;
    };
  }>;
  message: string;
  result_image_url?: string;
}

export interface OCRResult {
  success: boolean;
  count: number;
  text: string;
  char_count: number;
  line_count: number;
  message: string;
  file_url?: string;
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

// 탐지 옵션 타입
export interface DetectionOptions extends Record<string, boolean> {
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
}

// 비디오 분석 결과
export interface VideoAnalysisResult {
  success: boolean;
  video_info: {
    fps: number;
    frame_count: number;
    duration: number;
    width: number;
    height: number;
  };
  audio_transcription?: {
    success: boolean;
    text: string;
    language: string;
    segments: Array<{
      start: number;
      end: number;
      text: string;
    }>;
  };
  audio_text_analysis?: {
    has_sensitive_content: boolean;
    filtered_text: string;
    detected_categories: string[];
  };
  frames: Array<{
    frame_index: number;
    timestamp: number;
    ocr?: {
      text: string;
      char_count: number;
    };
    face?: {
      count: number;
      faces: Array<{
        index: number;
        box: { x: number; y: number; w: number; h: number };
        score: number;
      }>;
    };
    hand?: {
      count: number;
      fingers: Array<{
        index: number;
        pos: { x: number; y: number };
      }>;
    };
    text_analysis?: {
      has_sensitive_content: boolean;
      filtered_text: string;
      detected_categories: string[];
    };
  }>;
  summary: {
    total_frames_processed: number;
    total_faces_detected: number;
    total_fingers_detected: number;
    total_ocr_text_length: number;
    frames_with_sensitive_content: number;
  };
}


