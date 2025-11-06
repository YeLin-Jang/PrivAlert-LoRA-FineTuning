"""
데이터베이스 연결 및 초기화
보안: SQL Injection 방지를 위한 ORM 사용
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# 비동기 엔진 생성
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base 클래스
Base = declarative_base()


# User 모델 정의 (Flask 백엔드와 동일한 구조)
class User(Base):
    """사용자 모델 (Flask 백엔드와 동일한 테이블 구조)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # 이메일 검증
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)

    # MFA 설정 (FastAPI에서는 사용하지 않지만 테이블 구조 호환성)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    mfa_secret = Column(String(255), nullable=True)
    mfa_backup_codes_hash = Column(String(255), nullable=True)

    # 계정 상태
    is_active = Column(Boolean, default=False, nullable=False)  # 인증 완료 전까지 False
    is_deleted = Column(Boolean, default=False, nullable=False)
    deletion_requested_at = Column(DateTime, nullable=True)

    # 로그인 실패 추적
    login_failed_count = Column(Integer, default=0, nullable=False)
    login_locked_until = Column(DateTime, nullable=True)

    # 계정 정보
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)
    last_password_change = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_active={self.is_active})>"


async def init_db():
    """데이터베이스 초기화 (테이블 생성)
    Flask 백엔드와 같은 MySQL 데이터베이스를 사용하므로,
    테이블이 이미 존재할 수 있습니다.
    """
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("데이터베이스 초기화 완료")
    except Exception as e:
        # 테이블이 이미 존재하는 경우는 정상 (Flask 백엔드가 생성했을 수 있음)
        if "already exists" in str(e).lower() or "Table" in str(e):
            logger.info("테이블이 이미 존재합니다 (Flask 백엔드와 공유)")
        else:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise


async def close_db():
    """데이터베이스 연결 종료"""
    try:
        await engine.dispose()
        logger.info("데이터베이스 연결 종료")
    except Exception as e:
        logger.error(f"데이터베이스 연결 종료 실패: {e}")


async def get_db() -> AsyncSession:
    """데이터베이스 세션 의존성"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
