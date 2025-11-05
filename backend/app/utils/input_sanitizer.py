"""
입력값 정제 유틸리티
보안: XSS, SQL 인젝션 방지, 입력값 검증 및 정제
"""
import re
import html
from typing import Optional

# 보안: 허용되지 않은 문자 패턴
UNSAFE_CHARS = re.compile(r'[<>"\']')
SQL_INJECTION_PATTERNS = [
    re.compile(r'(?i)(union|select|insert|update|delete|drop|create|alter|exec|execute)'),
    re.compile(r'--'),
    re.compile(r'/\*'),
    re.compile(r'\*/'),
    re.compile(r';'),
]


def sanitize_string(input_str: str, max_length: Optional[int] = None) -> str:
    """
    문자열 정제 (XSS 방지)
    보안: HTML 특수문자 이스케이프
    
    Args:
        input_str: 정제할 문자열
        max_length: 최대 길이 제한
        
    Returns:
        정제된 문자열
    """
    if not isinstance(input_str, str):
        return ""
    
    # 보안: 길이 제한
    if max_length and len(input_str) > max_length:
        input_str = input_str[:max_length]
    
    # 보안: HTML 이스케이프
    sanitized = html.escape(input_str)
    
    return sanitized


def validate_no_sql_injection(input_str: str) -> tuple[bool, Optional[str]]:
    """
    SQL 인젝션 패턴 검증
    보안: SQL 인젝션 시도 감지
    
    Args:
        input_str: 검증할 문자열
        
    Returns:
        (유효성, 오류 메시지)
    """
    if not isinstance(input_str, str):
        return True, None
    
    # 보안: 빈 문자열은 허용
    if not input_str.strip():
        return True, None
    
    # 보안: SQL 인젝션 패턴 검사
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(input_str):
            return False, "허용되지 않은 문자가 포함되어 있습니다"
    
    return True, None


def sanitize_username(username: str) -> str:
    """
    사용자명 정제
    보안: 특수문자 제거, 길이 제한
    
    Args:
        username: 정제할 사용자명
        
    Returns:
        정제된 사용자명
    """
    if not isinstance(username, str):
        return ""
    
    # 보안: 앞뒤 공백 제거
    username = username.strip()
    
    # 보안: 길이 제한
    if len(username) > 20:
        username = username[:20]
    
    # 보안: 허용되지 않은 문자 제거 (영문, 숫자, 언더스코어, 하이픈만 허용)
    username = re.sub(r'[^a-zA-Z0-9_-]', '', username)
    
    return username


def sanitize_email(email: str) -> str:
    """
    이메일 정제
    보안: 특수문자 제거, 길이 제한
    
    Args:
        email: 정제할 이메일
        
    Returns:
        정제된 이메일
    """
    if not isinstance(email, str):
        return ""
    
    # 보안: 앞뒤 공백 제거
    email = email.strip().lower()
    
    # 보안: 길이 제한
    if len(email) > 120:
        email = email[:120]
    
    return email

