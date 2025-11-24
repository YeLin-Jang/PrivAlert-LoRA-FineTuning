"""API 공통 유틸리티"""

from flask import jsonify, Response
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def _add_security_headers(response: Response) -> Response:
    """보안 헤더 추가"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response


class APIResponse:
    """API 응답 표준화 클래스"""
    
    @staticmethod
    def success(data: Dict[str, Any] = None, message: str = "성공", status_code: int = 200) -> Tuple[Response, int]:
        """성공 응답"""
        response_data = {
            "success": True,
            "message": message
        }
        if data:
            response_data.update(data)
        response = jsonify(response_data)
        return _add_security_headers(response), status_code
    
    @staticmethod
    def error(error: str, code: int = 400, details: Optional[Dict[str, Any]] = None) -> Tuple[Response, int]:
        """에러 응답"""
        response_data = {
            "success": False,
            "error": error,
            "code": code
        }
        if details:
            response_data.update(details)
        response = jsonify(response_data)
        return _add_security_headers(response), code
    
    @staticmethod
    def validation_error(field: str, message: str) -> Tuple[Response, int]:
        """입력 검증 에러"""
        return APIResponse.error(
            f"입력 검증 실패: {field} - {message}",
            code=400
        )
    
    @staticmethod
    def server_error(error: str = "서버 내부 오류가 발생했습니다") -> Tuple[Response, int]:
        """서버 에러"""
        logger.error(f"서버 에러: {error}")
        return APIResponse.error(error, code=500)
    
    @staticmethod
    def unauthorized(message: str = "인증이 필요합니다") -> Tuple[Response, int]:
        """인증 필요 응답"""
        return APIResponse.error(message, code=401)
    
    @staticmethod
    def forbidden(message: str = "접근이 거부되었습니다") -> Tuple[Response, int]:
        """접근 거부 응답"""
        return APIResponse.error(message, code=403)
    
    @staticmethod
    def not_found(message: str = "요청한 리소스를 찾을 수 없습니다") -> Tuple[Response, int]:
        """리소스 없음 응답"""
        return APIResponse.error(message, code=404)


def validate_text_input(data, field: str = "text", max_length: int = 3000) -> tuple:
    """텍스트 입력 검증"""
    if not data:
        return False, APIResponse.error("요청 데이터가 없습니다")
    
    # data가 딕셔너리가 아닌 경우 처리
    if not isinstance(data, dict):
        return False, APIResponse.error("요청 데이터 형식이 올바르지 않습니다")
    
    text = data.get(field, '').strip()
    if not text:
        return False, APIResponse.error(f"{field}가 필요합니다")
    
    if len(text) > max_length:
        return False, APIResponse.error(f"{field}가 너무 깁니다 (최대 {max_length:,}자)")
    
    return True, text




def handle_api_exception(func):
    """API 예외 처리 데코레이터"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"API 에러 발생 ({func.__name__}): {e}")
            return APIResponse.server_error(str(e))
    return wrapper



