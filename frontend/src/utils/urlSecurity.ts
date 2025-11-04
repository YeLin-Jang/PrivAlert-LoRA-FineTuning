/**
 * URL 보안 유틸리티
 * URL에서 민감한 정보를 제거하고 보호하는 함수들
 */

/**
 * URL에서 민감한 파라미터 제거
 */
export const removeSensitiveParams = (url: string): string => {
  try {
    const urlObj = new URL(url, window.location.origin);
    const sensitiveParams = [
      'token',
      'access_token',
      'refresh_token',
      'auth_token',
      'password',
      'secret',
      'key',
      'api_key',
      'apikey',
      'session_id',
      'sessionid',
      'csrf_token',
      'csrftoken',
    ];

    sensitiveParams.forEach(param => {
      urlObj.searchParams.delete(param);
    });

    return urlObj.pathname + urlObj.search;
  } catch (error) {
    // URL 파싱 실패 시 원본 반환
    return url;
  }
};

/**
 * 현재 URL에서 민감한 정보 제거
 */
export const cleanCurrentUrl = (): void => {
  const currentUrl = window.location.href;
  const cleanUrl = removeSensitiveParams(currentUrl);
  
  if (currentUrl !== cleanUrl) {
    // 보안: URL에 민감 정보가 포함되어 있으면 제거
    window.history.replaceState({}, '', cleanUrl);
  }
};

/**
 * 리다이렉트 시 안전한 URL 사용
 */
export const safeRedirect = (url: string): void => {
  const cleanUrl = removeSensitiveParams(url);
  window.location.href = cleanUrl;
  // 브라우저 히스토리에서도 제거
  window.history.replaceState({}, '', cleanUrl);
};

/**
 * URL에 민감한 정보가 포함되어 있는지 확인
 */
export const hasSensitiveParams = (url: string): boolean => {
  try {
    const urlObj = new URL(url, window.location.origin);
    const sensitiveParams = [
      'token',
      'access_token',
      'refresh_token',
      'auth_token',
      'password',
      'secret',
      'key',
      'api_key',
      'apikey',
      'session_id',
      'sessionid',
      'csrf_token',
      'csrftoken',
    ];

    return sensitiveParams.some(param => urlObj.searchParams.has(param));
  } catch (error) {
    return false;
  }
};

