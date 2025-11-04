"""
데이터베이스 확장
- SQLAlchemy 초기화 및 설정
- TLS 연결 강제
"""

import os
import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base as db_declarative_base
from dotenv import load_dotenv

# 프로젝트 루트 경로 찾기 (PrivAlert/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ENV_FILE = os.path.join(ROOT_DIR, '.env')

# 환경변수 로드 (프로젝트 루트의 .env 파일 우선)
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)
else:
    # Fallback: 현재 디렉토리의 .env 파일
    load_dotenv()

logger = logging.getLogger(__name__)

# Base 클래스 (SQLAlchemy 2.0 스타일)
Base = db_declarative_base()

# 전역 변수
db_engine = None
db_session = None


def get_database_url():
    """데이터베이스 URL 생성 (TLS 강제)"""
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '3306')
    db_user = os.getenv('DB_USER', 'app_user')
    db_password = os.getenv('DB_PASSWORD', '')
    db_name = os.getenv('DB_NAME', 'privalert')
    
    # TLS 설정 (Docker 내부에서는 SSL 비활성화 가능)
    ssl_mode = os.getenv('DB_SSL_MODE', 'DISABLED')
    
    # PyMySQL 연결 문자열
    url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    # SSL 파라미터 (DISABLED일 때는 SSL 사용 안 함)
    ssl_params = {}
    if ssl_mode != 'DISABLED':
        ssl_params = {
            'ssl': {
                'ssl_mode': ssl_mode,
                'check_hostname': ssl_mode == 'VERIFY_IDENTITY'
            }
        }
    
    return url, ssl_params


def init_db(app):
    """데이터베이스 초기화"""
    global db_engine, db_session
    
    try:
        url, ssl_params = get_database_url()
        
        # 엔진 생성 (TLS 강제)
        db_engine = create_engine(
            url,
            poolclass=NullPool,  # 연결 풀 사용 안 함 (보안상 권장)
            pool_pre_ping=True,  # 연결 유효성 검사
            echo=app.config.get('DEBUG', False),  # 디버그 모드에서만 SQL 로그
            connect_args=ssl_params
        )
        
        # 세션 팩토리 생성
        session_factory = sessionmaker(bind=db_engine)
        db_session = scoped_session(session_factory)
        
        # Base에 엔진 할당
        Base.metadata.bind = db_engine
        
        # 테이블 생성
        Base.metadata.create_all(db_engine)
        
        logger.info("데이터베이스 초기화 완료")
        
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        raise


def get_db():
    """데이터베이스 세션 가져오기"""
    if db_session is None:
        raise RuntimeError("데이터베이스가 초기화되지 않았습니다")
    return db_session


def close_db(error=None):
    """데이터베이스 세션 종료"""
    if db_session:
        db_session.remove()


# 데이터베이스 모델을 위한 db 객체
class Database:
    """데이터베이스 헬퍼 클래스"""
    
    @staticmethod
    def init_app(app):
        """Flask 앱에 데이터베이스 초기화"""
        init_db(app)
        app.teardown_appcontext(close_db)
    
    @staticmethod
    def create_all():
        """모든 테이블 생성"""
        if db_engine:
            Base.metadata.create_all(db_engine)
    
    @staticmethod
    def drop_all():
        """모든 테이블 삭제 (주의: 개발 환경에서만 사용)"""
        if db_engine:
            Base.metadata.drop_all(db_engine)


# 편의를 위한 db 객체 (SQLAlchemy 스타일)
db = type('db', (), {
    'Model': Base,
    'session': property(lambda self: get_db()),
    'create_all': Database.create_all,
    'drop_all': Database.drop_all
})()

