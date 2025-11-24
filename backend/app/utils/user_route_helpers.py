"""사용자 라우트 헬퍼 함수"""
from flask import request
from app.utils.api_utils import APIResponse
from app.utils.csrf_protection import validate_csrf_token
from app.utils.logger import get_logger
from typing import Tuple, Optional

logger = get_logger(__name__)


def validate_csrf_from_request() -> Tuple[bool, Optional[Tuple]]:
    """CSRF 토큰 검증"""
    csrf_token = request.headers.get('X-CSRF-Token') or (
        request.json.get('csrf_token') if request.is_json else None
    )
    if not csrf_token:
        return False, APIResponse.error("CSRF 토큰이 필요합니다", code=403)
    
    user = request.current_user
    user_id_str = str(user.id)
    
    is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
    if not is_valid:
        return False, APIResponse.error(
            error_msg or "CSRF 토큰이 유효하지 않습니다",
            code=403
        )
    
    return True, None


def validate_csrf_from_session() -> Tuple[bool, Optional[Tuple]]:
    """세션 기반 CSRF 토큰 검증"""
    csrf_token = request.headers.get('X-CSRF-Token') or (
        request.json.get('csrf_token') if request.is_json else None
    )
    if not csrf_token:
        return False, APIResponse.error("CSRF 토큰이 필요합니다", code=403)
    
    session_id = request.cookies.get('session_id')
    if not session_id:
        return False, APIResponse.unauthorized("세션이 없습니다. 다시 로그인해주세요.")
    
    is_valid, error_msg = validate_csrf_token(session_id, csrf_token)
    if not is_valid:
        return False, APIResponse.error(
            error_msg or "CSRF 토큰이 유효하지 않습니다",
            code=403
        )
    
    return True, None


def check_user_active(user) -> Tuple[bool, Optional[Tuple]]:
    """사용자 활성화 상태 확인"""
    if not user.is_active:
        logger.warning(f"비활성화된 사용자 접근 시도: user_id={user.id}")
        return False, APIResponse.forbidden("계정이 비활성화되었습니다")
    return True, None


def get_session_id() -> Tuple[bool, Optional[str], Optional[Tuple]]:
    """세션 ID 가져오기"""
    session_id = request.cookies.get('session_id')
    if not session_id:
        return False, None, APIResponse.unauthorized("세션이 없습니다. 다시 로그인해주세요.")
    return True, session_id, None


def validate_json_request() -> Tuple[bool, Optional[dict], Optional[Tuple]]:
    """JSON 요청 검증"""
    data = request.get_json()
    if not data:
        return False, None, APIResponse.error("요청 데이터가 없습니다", code=400)
    return True, data, None

