import { useState, useCallback } from 'react';
import { validateFile, validateFileCount, validateTextLength } from '../utils/validation';
import type { ValidationResult } from '../utils/validation';
import { UPLOAD_LIMITS } from '../constants';

export const useFileValidation = () => {
  const [errors, setErrors] = useState<string[]>([]);

  const validateFiles = useCallback((files: File[], isVideo: boolean = false): boolean => {
    const newErrors: string[] = [];

    // 파일 개수 검증
    const countCheck = validateFileCount(files);
    if (!countCheck.isValid) {
      newErrors.push(countCheck.error || '파일 개수 초과');
      setErrors(newErrors);
      return false;
    }

    // 각 파일 검증
    files.forEach((file) => {
      const validation = validateFile(file, isVideo);
      if (!validation.isValid) {
        newErrors.push(`${file.name}: ${validation.error}`);
      }
    });

    if (newErrors.length > 0) {
      setErrors(newErrors);
      return false;
    }

    setErrors([]);
    return true;
  }, []);

  const validateText = useCallback((text: string): boolean => {
    const textCheck = validateTextLength(text);
    if (!textCheck.isValid) {
      setErrors([textCheck.error || '텍스트 길이 초과']);
      return false;
    }
    setErrors([]);
    return true;
  }, []);

  const clearErrors = useCallback(() => {
    setErrors([]);
  }, []);

  return {
    errors,
    validateFiles,
    validateText,
    clearErrors,
  };
};


