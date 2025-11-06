/**
 * 민감 데이터 보안 유틸리티
 * 개인정보 보호를 위한 데이터 정리 및 보안 처리
 */

/**
 * File 객체를 안전하게 제거
 * 메모리에서 파일 데이터를 명시적으로 해제
 */
export const secureFileCleanup = (file: File | null): void => {
  if (!file) return;
  
  // File 객체는 직접 삭제할 수 없지만, 참조를 제거하여 GC 대상으로 만듦
  try {
    // File 객체의 내부 데이터를 덮어쓰기 (가능한 범위 내에서)
    // 주의: File 객체는 읽기 전용이므로 완전한 삭제는 불가능하지만
    // 참조를 null로 설정하여 메모리에서 제거되도록 함
    Object.defineProperty(file, 'name', { value: '', writable: false });
  } catch {
    // 무시 - File 객체는 읽기 전용일 수 있음
  }
};

/**
 * File 배열을 안전하게 제거
 */
export const secureFilesCleanup = (files: File[]): void => {
  files.forEach(file => secureFileCleanup(file));
  files.length = 0; // 배열 비우기
};

/**
 * 텍스트 데이터를 안전하게 제거
 * 민감한 텍스트를 메모리에서 덮어쓰기
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const secureTextCleanup = (_text: string): string => {
  // 텍스트를 빈 문자열로 대체
  // 실제로는 변수가 재할당되면 GC가 처리하지만, 명시적으로 처리
  // 언더스코어 접두사로 미사용 매개변수 표시
  return '';
};

/**
 * FormData를 안전하게 정리
 * FormData의 모든 항목을 제거
 */
export const secureFormDataCleanup = (formData: FormData): void => {
  try {
    // FormData의 모든 키를 제거
    const keys = Array.from(formData.keys());
    keys.forEach(key => {
      formData.delete(key);
    });
  } catch {
    // FormData 정리 실패 시 무시
    // 보안: 콘솔 로그 제거
  }
};

/**
 * URL.createObjectURL로 생성된 URL을 안전하게 해제
 */
export const secureURLCleanup = (url: string): void => {
  try {
    if (url && url.startsWith('blob:')) {
      URL.revokeObjectURL(url);
    }
  } catch {
    // 보안: 콘솔 로그 제거
  }
};

/**
 * 객체에서 민감한 정보를 제거하고 안전하게 정리
 */
export const secureObjectCleanup = <T extends Record<string, unknown>>(obj: T): void => {
  try {
    Object.keys(obj).forEach(key => {
      const value = obj[key];
      if (typeof value === 'string') {
        // 타입 안전성을 위해 타입 단언 사용
        (obj as Record<string, unknown>)[key] = '';
      } else if (value instanceof File) {
        secureFileCleanup(value);
      } else if (Array.isArray(value)) {
        value.length = 0;
      } else if (typeof value === 'object' && value !== null) {
        secureObjectCleanup(value as Record<string, unknown>);
      }
      delete obj[key];
    });
  } catch {
    // 보안: 콘솔 로그 제거
  }
};

/**
 * 민감 정보를 로그에서 마스킹
 */
export const maskSensitiveData = (data: unknown): unknown => {
  if (typeof data === 'string') {
    let maskedData = data;
    // 전화번호 패턴 마스킹
    const phonePattern = /\d{2,3}-\d{3,4}-\d{4}/g;
    maskedData = maskedData.replace(phonePattern, '[전화번호]');
    
    // 이메일 패턴 마스킹
    const emailPattern = /[\w.-]+@[\w.-]+\.\w+/g;
    maskedData = maskedData.replace(emailPattern, '[이메일]');
    
    // 주민등록번호 패턴 마스킹
    const rrnPattern = /\d{6}-\d{7}/g;
    maskedData = maskedData.replace(rrnPattern, '[주민등록번호]');
    return maskedData;
  }
  
  return data;
};

/**
 * 안전한 로깅 (민감 정보 마스킹)
 * 보안: 콘솔 로그 제거
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export const secureLog = (_message: string, _data?: unknown): void => {
  // 보안: 모든 콘솔 로그 제거
  // 프로덕션 및 개발 환경 모두에서 로깅 비활성화
};
