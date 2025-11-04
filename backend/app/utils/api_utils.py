"""
API 공통 유틸리티
"""

from flask import jsonify
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class APIResponse:
    """API 응답 표준화 클래스"""
    
    @staticmethod
    def success(data: Dict[str, Any] = None, message: str = "성공", status_code: int = 200) -> tuple:
        """성공 응답 생성"""
        response_data = {
            "success": True,
            "message": message
        }
        if data:
            response_data.update(data)
        return jsonify(response_data), status_code
    
    @staticmethod
    def error(error: str, code: int = 400, details: Dict[str, Any] = None) -> tuple:
        """에러 응답 생성"""
        response_data = {
            "success": False,
            "error": error,
            "code": code
        }
        if details:
            response_data.update(details)
        return jsonify(response_data), code
    
    @staticmethod
    def validation_error(field: str, message: str) -> tuple:
        """입력 검증 에러 응답 생성"""
        return APIResponse.error(
            f"입력 검증 실패: {field} - {message}",
            code=400
        )
    
    @staticmethod
    def server_error(error: str = "서버 내부 오류가 발생했습니다") -> tuple:
        """서버 에러 응답 생성"""
        logger.error(f"서버 에러: {error}")
        return APIResponse.error(error, code=500)


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



