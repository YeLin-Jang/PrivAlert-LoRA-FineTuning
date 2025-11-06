"""
데이터베이스 초기화 유틸리티
"""
from app.extensions.database import db
# 보안: 모든 모델을 import하여 테이블 생성 보장
from app.models.user import User, UserFilteringSettings, RevisionHistory
from app.utils.logger import get_logger

logger = get_logger(__name__)

def init_database():
    """
    데이터베이스 초기화
    보안: 시큐어 코딩 가이드 준수
    - 테이블 생성
    """
    try:
        # 보안: 테이블 생성 (SQLAlchemy ORM 사용으로 SQL 인젝션 방지)
        db.create_all()
        logger.info("데이터베이스 테이블 생성 완료")
        
        return True
    except Exception as e:
        # 데이터베이스 연결 실패는 개발 환경에서 자주 발생하므로 WARNING으로 처리
        error_type = type(e).__name__
        error_msg = str(e)
        
        # 보안: 상세 오류 로그 기록 (문제 진단용) - 중복 출력 방지
        if "Access denied" in error_msg or "1045" in error_msg:
            logger.warning(
                f"데이터베이스 초기화 실패: {error_type} - {error_msg} | "
                f"원인: MySQL 사용자 권한 문제 | "
                f"해결: fix_mysql_user.bat 실행 또는 MySQL root로 사용자 생성 및 권한 부여"
            )
        else:
            logger.warning(
                f"데이터베이스 초기화 실패: {error_type} - {error_msg} | "
                f"가능한 원인: MySQL 서버 미실행, DB 미생성, 연결 정보 오류, 권한 문제"
            )
        db.session.rollback()
        return False

