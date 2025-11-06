"""
데이터베이스 초기화 유틸리티
보안: 기본 관리자 계정 생성 시 안전한 비밀번호 검증
"""
from app.extensions.database import db
from app.models.admin import AdminUser
# 보안: 모든 모델을 import하여 테이블 생성 보장
from app.models.user import User, UserFilteringSettings, RevisionHistory
from app.utils.logger import get_logger
import os

logger = get_logger(__name__)

def init_database():
    """
    데이터베이스 초기화
    보안: 시큐어 코딩 가이드 준수
    - 테이블 생성
    - 기본 관리자 계정 생성 (없는 경우)
    """
    try:
        # 보안: 테이블 생성 (SQLAlchemy ORM 사용으로 SQL 인젝션 방지)
        db.create_all()
        logger.info("데이터베이스 테이블 생성 완료")
        
        # 기본 관리자 계정 확인 및 생성
        admin_username = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('DEFAULT_ADMIN_PASSWORD')
        
        if not admin_password:
            raise ValueError("DEFAULT_ADMIN_PASSWORD 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        existing_admin = AdminUser.find_by_username(admin_username)
        
        if not existing_admin:
            # 보안: 기본 관리자 계정 생성 (비밀번호는 해시화되어 저장됨)
            admin = AdminUser.create_default_admin(
                username=admin_username,
                password=admin_password,
                role='admin'
            )
            db.session.add(admin)
            logger.info(f"기본 관리자 계정 생성: {admin_username}")
        else:
            # 기존 계정이 있으면 .env 파일의 비밀번호로 업데이트
            existing_admin.set_password(admin_password)
            logger.info(f"기본 관리자 계정 비밀번호 업데이트: {admin_username}")
        
        # super_admin 계정도 생성
        super_admin_username = os.getenv('DEFAULT_SUPER_ADMIN_USERNAME', 'super_admin')
        super_admin_password = os.getenv('DEFAULT_SUPER_ADMIN_PASSWORD')
        
        if not super_admin_password:
            raise ValueError("DEFAULT_SUPER_ADMIN_PASSWORD 환경 변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
            
        existing_super_admin = AdminUser.find_by_username(super_admin_username)
        if not existing_super_admin:
            super_admin = AdminUser.create_default_admin(
                username=super_admin_username,
                password=super_admin_password,
                role='super_admin'
            )
            db.session.add(super_admin)
            logger.info(f"기본 super_admin 계정 생성: {super_admin_username}")
        else:
            # 기존 계정이 있으면 .env 파일의 비밀번호로 업데이트
            existing_super_admin.set_password(super_admin_password)
            logger.info(f"기본 super_admin 계정 비밀번호 업데이트: {super_admin_username}")
        
        db.session.commit()
        logger.warning(
            f"기본 관리자 계정 설정 완료. " 
            f"프로덕션 환경에서는 반드시 비밀번호를 변경하세요! " 
            f"관리자명: {admin_username}, {super_admin_username}"
        )
        
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

