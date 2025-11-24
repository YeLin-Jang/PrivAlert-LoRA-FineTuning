"""
인증 유틸리티 함수
보안: HTTP 환경에서 가능한 최대한의 보안 조치
"""
from flask import request
from typing import Optional
import re


def validate_email(email: str) -> bool:
    """
    이메일 형식 검증
    보안: 서버 측 검증 필수
    """
    if not email or len(email) > 255:
        return False
    
    # 간단한 이메일 정규식 (RFC 5322 완전 호환은 아니지만 실용적)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    비밀번호 강도 검증
    반환: (유효 여부, 오류 메시지)
    """
    if not password:
        return False, "비밀번호를 입력하세요"
    
    if len(password) < 12:
        return False, "비밀번호는 최소 12자 이상이어야 합니다"
    
    if len(password) > 128:
        return False, "비밀번호는 최대 128자까지 가능합니다"
    
    if not any(c.isupper() for c in password):
        return False, "비밀번호는 최소 1개의 대문자를 포함해야 합니다"
    
    if not any(c.islower() for c in password):
        return False, "비밀번호는 최소 1개의 소문자를 포함해야 합니다"
    
    if not any(c.isdigit() for c in password):
        return False, "비밀번호는 최소 1개의 숫자를 포함해야 합니다"
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "비밀번호는 최소 1개의 특수문자를 포함해야 합니다"
    
    # 일반적인 약한 비밀번호 패턴 체크
    weak_patterns = [
        r'(.)\1{3,}',  # 같은 문자 4번 이상 반복
        r'(012|123|234|345|456|567|678|789|890)',  # 연속 숫자
        r'(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)',  # 연속 알파벳
    ]
    
    for pattern in weak_patterns:
        if re.search(pattern, password.lower()):
            return False, "너무 예측 가능한 비밀번호 패턴입니다"
    
    return True, ""


def get_client_ip() -> str:
    """
    클라이언트 IP 주소 추출 (프록시 환경 고려)
    """
    # X-Forwarded-For 헤더 확인 (프록시 환경)
    if request.headers.get('X-Forwarded-For'):
        # 첫 번째 IP 사용 (원본 클라이언트)
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    # X-Real-IP 헤더 확인
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    
    # 직접 연결
    return request.remote_addr or 'unknown'


def get_user_agent() -> str:
    """
    User-Agent 헤더 추출
    """
    return request.headers.get('User-Agent', '')[:500]  # 최대 500자


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    입력값 정제 (XSS 방지)
    보안: HTML 특수 문자 이스케이프
    """
    if not text:
        return ""
    
    # 길이 제한
    text = text[:max_length]
    
    # HTML 이스케이프 (프론트엔드에서도 처리하지만 서버 측 검증 필수)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#x27;')
    
    return text


def is_rate_limited(identifier: str, limit: int, window_seconds: int) -> bool:
    """
    Rate limiting 체크
    주의: 이 함수는 현재 사용되지 않습니다. Flask-Limiter가 직접 처리합니다.
    Flask-Limiter는 __init__.py에서 설정되며, REDIS_URL이 설정되어 있으면 Redis를 사용합니다.
    """
    # Flask-Limiter가 직접 처리하므로 이 함수는 사용되지 않음
    return False

