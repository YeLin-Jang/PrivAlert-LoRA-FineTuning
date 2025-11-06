"""
인증 데코레이터
보안: 세션 기반 인증, CSRF 보호
"""
from functools import wraps
from flask import request, jsonify
from app.utils.logger import get_logger
from app.models.session import UserSession
from app.models.user import User

logger = get_logger(__name__)


def login_required(f):
    """
    로그인 필요 데코레이터
    보안: 세션 쿠키 검증, Double Submit Cookie 검증
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            session_id = request.cookies.get('session_id')
            session_token = request.cookies.get('session_token')
            
            # 디버깅: 쿠키 확인
            if not session_id:
                logger.warning(f"인증 실패: session_id 쿠키가 없습니다. 요청 URL: {request.path}, 쿠키: {list(request.cookies.keys())}")
                return jsonify({
                    "success": False,
                    "error": "인증이 필요합니다",
                    "code": 401
                }), 401
            
            # 세션 조회
            session = UserSession.find_by_session_id(session_id)
            
            if not session:
                logger.warning(f"인증 실패: 세션을 찾을 수 없습니다. session_id: {session_id[:8]}..., 요청 URL: {request.path}")
                return jsonify({
                    "success": False,
                    "error": "유효하지 않은 세션입니다",
                    "code": 401
                }), 401
            
            # Double Submit Cookie 검증
            if not session_token:
                logger.warning(f"인증 실패: session_token 쿠키가 없습니다. session_id: {session_id[:8]}..., 요청 URL: {request.path}")
                return jsonify({
                    "success": False,
                    "error": "세션 토큰이 필요합니다",
                    "code": 401
                }), 401
            
            if session.session_token != session_token:
                logger.warning(f"세션 토큰 불일치: session_id={session_id[:8]}..., 요청 URL: {request.path}, DB 토큰: {session.session_token[:8] if session.session_token else None}..., 쿠키 토큰: {session_token[:8] if session_token else None}...")
                return jsonify({
                    "success": False,
                    "error": "세션 토큰이 유효하지 않습니다",
                    "code": 401
                }), 401
            
            # 사용자 조회
            user = User.query.get(session.user_id)
            
            if not user or not user.is_active or user.is_deleted:
                session.revoke()
                return jsonify({
                    "success": False,
                    "error": "사용자 계정이 비활성화되었습니다",
                    "code": 403
                }), 403
            
            # 세션 활동 업데이트
            session.update_activity()
            
            # 요청 컨텍스트에 사용자 정보 추가
            request.current_user = user
            request.current_session = session
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"인증 오류: {e}")
            return jsonify({
                "success": False,
                "error": "인증 중 오류가 발생했습니다",
                "code": 401
            }), 401
    
    return decorated_function

