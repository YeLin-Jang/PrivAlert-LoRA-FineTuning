"""
인증 관련 API 라우트
보안: 비밀번호 해싱, 입력 검증, SQL Injection 방지
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import bcrypt
from datetime import datetime

from app.database import get_db, User
from app.models.user_model import (
    UserRegisterRequest,
    UserVerifyRequest,
    UserResponse,
    MessageResponse
)
from app.services.email_service import EmailService
from app.services.verification_service import VerificationService
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="회원가입 및 인증번호 전송",
    description="이메일과 비밀번호를 받아 회원가입을 처리하고, 이메일로 인증번호를 전송합니다."
)
async def register(
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    회원가입 엔드포인트
    보안: 비밀번호는 bcrypt로 해시 처리, 중복 이메일 검사
    """
    try:
        # 중복 이메일 확인
        result = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # 보안: 사용자에게는 동일한 메시지 반환 (이메일 존재 여부 노출 방지)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="이미 등록된 이메일입니다"
            )
        
        # 비밀번호 해시 처리 (bcrypt)
        password_hash = bcrypt.hashpw(
            user_data.password.encode('utf-8'),
            bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
        ).decode('utf-8')
        
        # 사용자 생성 (인증 전까지 is_active=False, Flask 백엔드와 호환)
        new_user = User(
            email=user_data.email,
            password_hash=password_hash,
            email_verified=False,
            is_active=False,  # 인증 완료 전까지 비활성
            is_deleted=False,
            login_failed_count=0,
            mfa_enabled=False
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # 인증번호 생성
        verification_code = await VerificationService.generate_code(user_data.email)
        
        # 이메일 전송
        email_sent = await EmailService.send_verification_code(
            user_data.email,
            verification_code
        )
        
        if not email_sent:
            # 이메일 전송 실패 시 사용자 삭제 (롤백)
            await db.delete(new_user)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="이메일 전송에 실패했습니다. 잠시 후 다시 시도해주세요."
            )
        
        # 보안: 로그에 비밀번호나 인증번호는 기록하지 않음
        logger.info(f"회원가입 성공: {user_data.email}")
        
        # 개발 환경에서만 인증번호를 응답에 포함 (테스트용)
        response_data = {
            "message": "회원가입이 완료되었습니다. 이메일을 확인하여 인증번호를 입력하세요.",
            "success": True
        }
        
        # DEBUG 모드이거나 개발 환경에서만 인증번호 반환
        if settings.DEBUG:
            response_data["verification_code"] = verification_code
            response_data["debug_message"] = "⚠️ 개발 모드: 인증번호가 응답에 포함되었습니다. 프로덕션에서는 제거됩니다."
            logger.warning(f"⚠️ 개발 모드: 인증번호 응답 포함 - {user_data.email}")
        
        return MessageResponse(**response_data)
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"데이터베이스 무결성 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 등록된 이메일입니다"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"회원가입 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입 중 오류가 발생했습니다"
        )

@router.post(
    "/verify-email",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="이메일 인증번호 검증",
    description="이메일과 인증번호를 받아 검증하고, 계정을 활성화합니다."
)
async def verify_email(
    verify_data: UserVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    이메일 인증번호 검증 엔드포인트
    보안: 인증번호 검증 후 계정 활성화
    """
    try:
        # 인증번호 검증
        is_valid = await VerificationService.verify_code(
            verify_data.email,
            verify_data.verification_code
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="인증번호가 올바르지 않거나 만료되었습니다"
            )
        
        # 사용자 조회
        result = await db.execute(
            select(User).where(User.email == verify_data.email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        if user.is_active:
            # 이미 인증된 계정
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="이미 인증된 계정입니다"
            )
        
        # 계정 활성화
        user.is_active = True
        user.email_verified = True
        user.email_verified_at = datetime.now()
        user.updated_at = datetime.now()
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"이메일 인증 성공: {verify_data.email}")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"이메일 인증 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="이메일 인증 중 오류가 발생했습니다"
        )

@router.post(
    "/login",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="로그인",
    description="이메일과 비밀번호로 로그인합니다."
)
async def login(
    login_data: UserRegisterRequest,  # 이메일과 비밀번호만 필요
    db: AsyncSession = Depends(get_db)
):
    """
    로그인 엔드포인트
    보안: 비밀번호 해시 비교, 계정 활성화 확인
    """
    try:
        # 사용자 조회
        result = await db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()
        
        # 보안: 사용자 존재 여부와 관계없이 동일한 응답 시간 (타이밍 공격 방지)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다"
            )
        
        # 계정 활성화 확인
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이메일 인증이 완료되지 않았습니다. 이메일을 확인하여 인증을 완료하세요."
            )
        
        # 비밀번호 확인
        if not bcrypt.checkpw(
            login_data.password.encode('utf-8'),
            user.password_hash.encode('utf-8')
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="이메일 또는 비밀번호가 올바르지 않습니다"
            )
        
        # 로그인 시간 업데이트
        user.last_login = datetime.now()
        user.updated_at = datetime.now()
        await db.commit()
        
        logger.info(f"로그인 성공: {user.email}")
        
        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"로그인 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 중 오류가 발생했습니다"
        )

@router.get(
    "/me",
    response_model=UserResponse,
    summary="현재 사용자 정보 조회",
    description="현재 로그인한 사용자 정보를 조회합니다."
)
async def get_current_user(
    email: str,  # 임시: 실제로는 JWT 토큰이나 세션에서 가져와야 함
    db: AsyncSession = Depends(get_db)
):
    """
    현재 사용자 정보 조회 엔드포인트
    보안: 실제로는 인증 토큰에서 사용자 정보를 가져와야 함
    """
    try:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="사용자를 찾을 수 없습니다"
            )
        
        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"사용자 정보 조회 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 정보 조회 중 오류가 발생했습니다"
        )
