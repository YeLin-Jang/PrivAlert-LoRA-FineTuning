"""
환경 변수 및 설정 관리
보안: 민감 정보는 환경 변수로 관리
"""
from typing import List
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings:
    """애플리케이션 설정"""
    
    def __init__(self):
        """환경 변수에서 설정 로드"""
        # 애플리케이션 설정
        self.APP_NAME: str = "PrivAlert FastAPI Backend"
        self.DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
        
        # 데이터베이스 설정 (MySQL 사용)
        # Flask 백엔드와 같은 MySQL 데이터베이스 사용
        mysql_host = os.getenv("MYSQL_HOST", "localhost")
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_user = os.getenv("MYSQL_USER", "privalert_user")
        mysql_password = os.getenv("MYSQL_PASSWORD", "")
        mysql_database = os.getenv("MYSQL_DATABASE", "privalert")
        
        # DATABASE_URL이 명시적으로 설정되어 있으면 사용, 아니면 MySQL 연결 문자열 생성
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            f"mysql+aiomysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_database}?charset=utf8mb4"
        )
        
        # CORS 설정
        # 환경 변수에서 쉼표로 구분된 문자열을 읽어서 리스트로 변환
        cors_origins_str = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173"
        )
        self.CORS_ORIGINS: List[str] = [origin.strip() for origin in cors_origins_str.split(",") if origin.strip()]
        
        # SMTP 설정 (Gmail 예시)
        self.SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_EMAIL: str = os.getenv("SMTP_EMAIL", "")
        self.SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
        self.SMTP_FROM: str = os.getenv("SMTP_FROM", os.getenv("SMTP_EMAIL", "noreply@privalert.com") or "noreply@privalert.com")
        
        # 인증번호 설정
        self.VERIFICATION_CODE_LENGTH: int = int(os.getenv("VERIFICATION_CODE_LENGTH", "6"))
        self.VERIFICATION_CODE_EXPIRY_MINUTES: int = int(os.getenv("VERIFICATION_CODE_EXPIRY_MINUTES", "5"))
        
        # Redis 설정 (선택사항)
        self.REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() == "true"
        
        # 보안 설정
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        self.BCRYPT_ROUNDS: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

# 전역 설정 인스턴스
settings = Settings()

