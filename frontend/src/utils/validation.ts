import { UPLOAD_LIMITS, ERROR_MESSAGES } from '../constants';

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

/**
 * 비디오 길이 검증
 */
export const validateVideoDuration = async (file: File): Promise<ValidationResult> => {
  return new Promise((resolve) => {
    const video = document.createElement('video');
    video.preload = 'metadata';
    
    video.onloadedmetadata = () => {
      window.URL.revokeObjectURL(video.src);
      const duration = video.duration;
      
      if (duration > UPLOAD_LIMITS.MAX_VIDEO_DURATION) {
        resolve({
          isValid: false,
          error: ERROR_MESSAGES.VIDEO_TOO_LONG,
        });
      } else {
        resolve({ isValid: true });
      }
    };
    
    video.onerror = () => {
      window.URL.revokeObjectURL(video.src);
      // 비디오 메타데이터를 읽을 수 없는 경우 경고하지만 허용
      resolve({
        isValid: true,
      });
    };
    
    video.src = URL.createObjectURL(file);
  });
};

/**
 * 파일 타입 검증
 */
export const validateFileType = (file: File, isVideo: boolean = false): ValidationResult => {
  const allowedTypes = isVideo ? UPLOAD_LIMITS.ALLOWED_VIDEO_TYPES : UPLOAD_LIMITS.ALLOWED_IMAGE_TYPES;
  const fileType: string = file.type;
  
  // 타입 안전성을 위해 배열을 string 배열로 변환하여 체크
  const allowedTypesArray: readonly string[] = allowedTypes;
  
  if (!allowedTypesArray.includes(fileType)) {
    const imageTypesArray: readonly string[] = UPLOAD_LIMITS.ALLOWED_IMAGE_TYPES;
    const isImageType = imageTypesArray.includes(fileType);
    return {
      isValid: false,
      error: isImageType 
        ? '이미지 파일만 업로드할 수 있습니다'
        : '비디오 파일만 업로드할 수 있습니다',
    };
  }
  
  return { isValid: true };
};

/**
 * 파일 크기 검증
 */
export const validateFileSize = (file: File, isVideo: boolean = false): ValidationResult => {
  const maxSize = isVideo ? UPLOAD_LIMITS.MAX_VIDEO_SIZE : UPLOAD_LIMITS.MAX_FILE_SIZE;
  
  if (file.size > maxSize) {
    const maxSizeMB = Math.round(maxSize / (1024 * 1024));
    return {
      isValid: false,
      error: `파일 크기는 최대 ${maxSizeMB}MB까지 업로드할 수 있습니다`,
    };
  }
  
  return { isValid: true };
};

/**
 * 파일 개수 검증
 */
export const validateFileCount = (files: File[]): ValidationResult => {
  if (files.length > UPLOAD_LIMITS.MAX_FILES) {
    return {
      isValid: false,
      error: `파일은 최대 ${UPLOAD_LIMITS.MAX_FILES}개까지 업로드할 수 있습니다`,
    };
  }
  
  return { isValid: true };
};

/**
 * 텍스트 길이 검증
 */
export const validateTextLength = (text: string): ValidationResult => {
  if (text.length > UPLOAD_LIMITS.MAX_TEXT_LENGTH) {
    return {
      isValid: false,
      error: `텍스트는 최대 ${UPLOAD_LIMITS.MAX_TEXT_LENGTH}자까지 입력할 수 있습니다`,
    };
  }
  
  return { isValid: true };
};

/**
 * 파일명 정제 (XSS 방지)
 */
export const sanitizeFileName = (fileName: string): string => {
  // 경로 조작 방지
  const sanitized = fileName.replace(/[<>:"/\\|?*\x00-\x1f]/g, '_');
  // 파일명 길이 제한
  return sanitized.length > 255 ? sanitized.substring(0, 255) : sanitized;
};

/**
 * 파일 전체 검증 (비디오는 동기 검증)
 */
export const validateFile = (file: File, isVideo: boolean = false): ValidationResult => {
  // 파일명 검증
  const sanitized = sanitizeFileName(file.name);
  if (sanitized !== file.name) {
    return {
      isValid: false,
      error: '파일명에 허용되지 않은 문자가 포함되어 있습니다',
    };
  }
  
  // 파일 타입 검증
  const typeCheck = validateFileType(file, isVideo);
  if (!typeCheck.isValid) {
    return typeCheck;
  }
  
  // 파일 크기 검증
  const sizeCheck = validateFileSize(file, isVideo);
  if (!sizeCheck.isValid) {
    return sizeCheck;
  }
  
  return { isValid: true };
};

/**
 * 비디오 파일 전체 검증 (비동기 - 길이 검증 포함)
 */
export const validateVideoFile = async (file: File): Promise<ValidationResult> => {
  // 기본 파일 검증
  const basicValidation = validateFile(file, true);
  if (!basicValidation.isValid) {
    return basicValidation;
  }
  
  // 비디오 길이 검증
  const durationValidation = await validateVideoDuration(file);
  if (!durationValidation.isValid) {
    return durationValidation;
  }
  
  return { isValid: true };
};

