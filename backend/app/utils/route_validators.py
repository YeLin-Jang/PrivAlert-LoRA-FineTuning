"""
라우트 검증 유틸리티
공통 검증 로직을 재사용 가능한 함수로 추출
"""
from flask import request
from app.utils.api_utils import APIResponse
from app.utils.auth_utils import validate_email, validate_password_strength
from typing import Tuple, Optional, Dict, Any


def validate_json_request() -> Tuple[bool, Optional[Dict[str, Any]], Optional[Tuple]]:
    """JSON 요청 검증"""
    data = request.get_json()
    if not data:
        return False, None, APIResponse.error("요청 데이터가 필요합니다", code=400)
    return True, data, None


def validate_email_field(email: str) -> Tuple[bool, Optional[Tuple]]:
    """이메일 필드 검증"""
    if not email:
        return False, APIResponse.error("이메일을 입력하세요", code=400)
    if not validate_email(email):
        return False, APIResponse.error("올바른 이메일 형식이 아닙니다", code=400)
    return True, None


def validate_password_field(password: str) -> Tuple[bool, Optional[Tuple]]:
    """비밀번호 필드 검증"""
    if not password:
        return False, APIResponse.error("비밀번호를 입력하세요", code=400)
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        return False, APIResponse.error(error_msg, code=400)
    return True, None


def validate_nickname(nickname: str, min_length: int = 2, max_length: int = 20) -> Tuple[bool, Optional[Tuple]]:
    """별명 검증"""
    nickname = nickname.strip() if nickname else ""
    if not nickname or len(nickname) < min_length:
        return False, APIResponse.error(f"별명은 최소 {min_length}자 이상이어야 합니다", code=400)
    if len(nickname) > max_length:
        return False, APIResponse.error(f"별명은 최대 {max_length}자까지 가능합니다", code=400)
    return True, None


def validate_signup_data(data: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, str]], Optional[Tuple]]:
    """회원가입 데이터 검증"""
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    nickname = data.get('nickname', '').strip()
    
    # 이메일 검증
    is_valid, error = validate_email_field(email)
    if not is_valid:
        return False, None, error
    
    # 비밀번호 검증
    is_valid, error = validate_password_field(password)
    if not is_valid:
        return False, None, error
    
    # 별명 검증
    is_valid, error = validate_nickname(nickname)
    if not is_valid:
        return False, None, error
    
    return True, {'email': email, 'password': password, 'nickname': nickname}, None

