"""
CSRF 보호 유틸리티
쿠키 탈취 공격 방지를 위한 CSRF 토큰 생성 및 검증
"""
import os
import secrets
import time
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from threading import Lock
from app.utils.logger import get_logger

logger = get_logger(__name__)

# CSRF 토큰 저장소 (메모리)
# {session_id: {"token": str, "created_at": datetime, "used": bool}}
_csrf_tokens: Dict[str, Dict] = {}

# 락 (스레드 안전성)
_lock = Lock()

# 토큰 유효 시간 (기본 1시간)
CSRF_TOKEN_EXPIRY_HOURS = int(os.getenv("CSRF_TOKEN_EXPIRY_HOURS", "1"))

# 토큰 길이 (기본 32바이트 = 64 hex 문자)
CSRF_TOKEN_LENGTH = 32


def generate_csrf_token(session_id: str) -> str:
    """
    CSRF 토큰 생성
    
    Args:
        session_id: 세션 ID (사용자별 고유 식별자)
    
    Returns:
        CSRF 토큰 (hex 문자열)
    """
    if not session_id:
        raise ValueError("session_id가 필요합니다")
    
    # 암호학적으로 안전한 랜덤 토큰 생성
    token = secrets.token_hex(CSRF_TOKEN_LENGTH)
    
    with _lock:
        _csrf_tokens[session_id] = {
            "token": token,
            "created_at": datetime.now(),
            "used": False
        }
    
    logger.debug(f"CSRF 토큰 생성: session_id={session_id[:8]}...")
    return token


def validate_csrf_token(session_id: str, token: str) -> Tuple[bool, Optional[str]]:
    """
    CSRF 토큰 검증
    
    Args:
        session_id: 세션 ID
        token: 검증할 CSRF 토큰
    
    Returns:
        (is_valid, error_message)
    """
    if not session_id or not token:
        return False, "CSRF 토큰과 세션 ID가 필요합니다"
    
    with _lock:
        if session_id not in _csrf_tokens:
            logger.warning(f"CSRF 토큰을 찾을 수 없음: session_id={session_id[:8]}...")
            return False, "CSRF 토큰을 찾을 수 없습니다. 새로 발급받아주세요."
        
        token_data = _csrf_tokens[session_id]
        stored_token = token_data["token"]
        created_at = token_data["created_at"]
        
        # 토큰 일치 확인
        if not secrets.compare_digest(token, stored_token):
            logger.warning(f"CSRF 토큰 불일치: session_id={session_id[:8]}...")
            return False, "CSRF 토큰이 일치하지 않습니다"
        
        # 토큰 만료 확인
        expiry_time = created_at + timedelta(hours=CSRF_TOKEN_EXPIRY_HOURS)
        if datetime.now() > expiry_time:
            logger.warning(f"CSRF 토큰 만료: session_id={session_id[:8]}...")
            del _csrf_tokens[session_id]
            return False, "CSRF 토큰이 만료되었습니다. 새로 발급받아주세요."
        
        # 토큰 사용 표시 (한 번만 사용 가능하도록 설정 가능)
        # 현재는 재사용 가능하지만, 필요시 이 부분을 활성화
        # token_data["used"] = True
    
    logger.debug(f"CSRF 토큰 검증 성공: session_id={session_id[:8]}...")
    return True, None


def revoke_csrf_token(session_id: str) -> None:
    """
    CSRF 토큰 무효화 (로그아웃 등에서 사용)
    
    Args:
        session_id: 세션 ID
    """
    with _lock:
        if session_id in _csrf_tokens:
            del _csrf_tokens[session_id]
            logger.debug(f"CSRF 토큰 무효화: session_id={session_id[:8]}...")


def cleanup_expired_tokens() -> int:
    """
    만료된 CSRF 토큰 정리
    
    Returns:
        삭제된 토큰 개수
    """
    deleted_count = 0
    now = datetime.now()
    
    with _lock:
        expired_sessions = []
        for session_id, token_data in list(_csrf_tokens.items()):
            expiry_time = token_data["created_at"] + timedelta(hours=CSRF_TOKEN_EXPIRY_HOURS)
            if now > expiry_time:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del _csrf_tokens[session_id]
            deleted_count += 1
    
    if deleted_count > 0:
        logger.info(f"만료된 CSRF 토큰 {deleted_count}개 정리 완료")
    
    return deleted_count


def get_csrf_token(session_id: str) -> Optional[str]:
    """
    현재 세션의 CSRF 토큰 조회 (없으면 None)
    
    Args:
        session_id: 세션 ID
    
    Returns:
        CSRF 토큰 또는 None
    """
    with _lock:
        if session_id in _csrf_tokens:
            token_data = _csrf_tokens[session_id]
            # 만료 확인
            expiry_time = token_data["created_at"] + timedelta(hours=CSRF_TOKEN_EXPIRY_HOURS)
            if datetime.now() <= expiry_time:
                return token_data["token"]
            else:
                # 만료된 토큰 제거
                del _csrf_tokens[session_id]
    return None

