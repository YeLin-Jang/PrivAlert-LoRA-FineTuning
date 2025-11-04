"""
데이터베이스 초기화 유틸리티
보안: 기본 관리자 계정 생성 시 안전한 비밀번호 검증
"""
from app.extensions.database import db
from app.models.admin import AdminUser
from app.utils.logger import get_logger
import os

logger = get_logger(__name__)

def init_database():
    """
    데이터베이스 초기화
    - 테이블 생성
    - 기본 관리자 계정 생성 (없는 경우)
    """
    try:
        # 테이블 생성
        db.create_all()
        logger.info("데이터베이스 테이블 생성 완료")
        
        # 기본 관리자 계정 확인 및 생성
        admin_username = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin123!')
        
        existing_admin = AdminUser.find_by_username(admin_username)
        
        if not existing_admin:
            # 보안: 기본 관리자 계정 생성
            admin = AdminUser.create_default_admin(
                username=admin_username,
                password=admin_password,
                role='admin'
            )
            db.session.add(admin)
            
            # super_admin 계정도 생성
            super_admin_username = os.getenv('DEFAULT_SUPER_ADMIN_USERNAME', 'super_admin')
            super_admin_password = os.getenv('DEFAULT_SUPER_ADMIN_PASSWORD', 'super123!')
            
            existing_super_admin = AdminUser.find_by_username(super_admin_username)
            if not existing_super_admin:
                super_admin = AdminUser.create_default_admin(
                    username=super_admin_username,
                    password=super_admin_password,
                    role='super_admin'
                )
                db.session.add(super_admin)
            
            db.session.commit()
            logger.warning(
                f"기본 관리자 계정이 생성되었습니다. "
                f"프로덕션 환경에서는 반드시 비밀번호를 변경하세요! "
                f"사용자명: {admin_username}, {super_admin_username}"
            )
        else:
            logger.info("기본 관리자 계정이 이미 존재합니다")
        
        return True
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        db.session.rollback()
        return False

