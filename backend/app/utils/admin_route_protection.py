"""
관리자 경로 접근 보호 유틸리티
보안: 일반 사용자가 관리자 API에 접근하지 못하도록 차단
"""
from flask import request, jsonify
from app.utils.logger import get_logger

logger = get_logger(__name__)


def check_admin_route_access():
    """
    관리자 경로 접근 차단
    일반 사용자 인증 시스템으로는 관리자 경로에 접근할 수 없도록 보호
    
    Returns:
        (is_blocked, error_response, status_code) - 차단 여부와 에러 응답
    """
    # 관리자 API 경로 확인
    if request.path.startswith('/api/v1/admin'):
        # 관리자 로그인 엔드포인트는 허용
        if request.path.endswith('/auth/login') and request.method == 'POST':
            return False, None, None
        
        # 일반 사용자 세션 쿠키 확인
        session_id = request.cookies.get('session_id')
        
        # 관리자 JWT 토큰 확인 (Authorization 헤더 또는 쿠키)
        admin_token = request.headers.get('Authorization') or request.cookies.get('admin_token')
        
        # 일반 사용자 세션이 있고 관리자 토큰이 없으면 차단
        if session_id and not admin_token:
            logger.warning(
                f"일반 사용자가 관리자 API 접근 시도: "
                f"path={request.path}, method={request.method}, "
                f"session_id={session_id[:8]}..., ip={request.remote_addr}"
            )
            return True, jsonify({
                "success": False,
                "error": "접근 권한이 없습니다",
                "code": 403
            }), 403
        
        # 관리자 토큰이 있으면 관리자 인증 데코레이터에서 처리
        if admin_token:
            return False, None, None
    
    # 관리자 프론트엔드 경로는 프론트엔드에서 처리
    # (백엔드에서는 관리자 인증 API만 보호)
    
    return False, None, None


def require_admin_authentication():
    """
    관리자 인증 필요 여부 확인
    관리자 경로는 항상 관리자 JWT 토큰 필요
    """
    if request.path.startswith('/api/v1/admin') and request.method != 'OPTIONS':
        # 관리자 API는 관리자 JWT 토큰 필요 (admin_decorators에서 처리)
        # 여기서는 로깅만 수행
        if not request.headers.get('Authorization'):
            logger.warning(
                f"관리자 API 접근 시도 (인증 없음): "
                f"path={request.path}, method={request.method}, ip={request.remote_addr}"
            )

