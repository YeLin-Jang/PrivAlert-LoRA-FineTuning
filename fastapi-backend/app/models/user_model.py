"""
사용자 스키마 (Pydantic 모델)
보안: 비밀번호는 응답 스키마에 포함하지 않음
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime
from typing import Optional

class UserRegisterRequest(BaseModel):
    """회원가입 요청 스키마"""
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., min_length=12, description="비밀번호 (최소 12자)")
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """비밀번호 강도 검증"""
        if len(v) < 12:
            raise ValueError("비밀번호는 최소 12자 이상이어야 합니다")
        if not any(c.isupper() for c in v):
            raise ValueError("비밀번호는 최소 1개의 대문자를 포함해야 합니다")
        if not any(c.islower() for c in v):
            raise ValueError("비밀번호는 최소 1개의 소문자를 포함해야 합니다")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호는 최소 1개의 숫자를 포함해야 합니다")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("비밀번호는 최소 1개의 특수문자를 포함해야 합니다")
        return v

class UserVerifyRequest(BaseModel):
    """이메일 인증 요청 스키마"""
    email: EmailStr = Field(..., description="이메일 주소")
    verification_code: str = Field(..., min_length=6, max_length=6, description="6자리 인증번호")

class UserResponse(BaseModel):
    """사용자 응답 스키마 (비밀번호 제외)"""
    id: int
    email: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class MessageResponse(BaseModel):
    """일반 메시지 응답 스키마"""
    message: str
    success: bool = True
    verification_code: str | None = None  # 개발 모드에서만 포함
    debug_message: str | None = None  # 개발 모드에서만 포함

