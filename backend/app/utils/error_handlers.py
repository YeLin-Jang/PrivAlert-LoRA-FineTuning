"""에러 핸들러 모듈"""
from flask import Flask, request
from app.utils.api_utils import APIResponse
import logging

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask):
    """에러 핸들러 등록"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """잘못된 요청"""
        return APIResponse.error("잘못된 요청입니다", code=400)
    
    @app.errorhandler(401)
    def unauthorized(error):
        """인증 필요"""
        return APIResponse.unauthorized()
    
    @app.errorhandler(403)
    def forbidden(error):
        """접근 거부"""
        return APIResponse.forbidden()
    
    @app.errorhandler(404)
    def not_found(error):
        """리소스 없음"""
        return APIResponse.not_found(
            "요청한 리소스를 찾을 수 없습니다. 사용 가능한 엔드포인트 목록은 루트 경로(/)를 참조하세요."
        )
    
    @app.errorhandler(413)
    def payload_too_large(error):
        """페이로드 크기 초과"""
        return APIResponse.error("파일 크기가 너무 큽니다 (최대 10MB)", code=413)
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Rate Limiting 위반"""
        ip = request.remote_addr if request else 'unknown'
        path = request.path if request else 'unknown'
        app.logger.warning(f"Rate Limiting 위반: ip={ip}, path={path}")
        return APIResponse.error(
            "요청 횟수가 초과되었습니다. 잠시 후 다시 시도해주세요",
            code=429
        )
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """서버 오류"""
        app.logger.error(f"서버 오류: {error}", exc_info=True)
        return APIResponse.server_error()
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """예외 처리"""
        app.logger.error(f"예외 발생: {error}", exc_info=True)
        return APIResponse.server_error()

