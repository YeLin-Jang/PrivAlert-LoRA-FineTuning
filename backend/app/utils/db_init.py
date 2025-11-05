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
    - 더미 사용자 데이터 생성 (데모용)
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
        
        # 더미 사용자 데이터 생성 (데모용)
        dummy_username = 'demo_user'
        existing_dummy_user = User.find_by_username(dummy_username)
        
        if not existing_dummy_user:
            dummy_user = User(
                username=dummy_username,
                email='demo@privalert.com',
                is_active=True
            )
            dummy_user.set_password('demo123!')  # 비밀번호는 실제로 사용하지 않지만 보안을 위해 설정
            db.session.add(dummy_user)
            db.session.flush()  # ID 생성
            
            # 더미 사용자 필터링 설정 생성
            dummy_settings = UserFilteringSettings(user_id=dummy_user.id)
            dummy_settings.set_detection_options({
                'phone': True,
                'email': True,
                'name': True,
                'address': True,
                'rrn': False,
                'passport': False,
                'ip_address': False,
                'face': False,
                'fingerprint': False,
                'account': False,
                'school': False,
                'workplace': False,
                'driverLicense': False,
                'postalCode': False
            })
            db.session.add(dummy_settings)
            
            # 더미 수정 기록 생성
            dummy_revisions = [
                {
                    'revised_sentence': '이것은 LLM이 생성한 안전한 수정 문장입니다. 개인정보가 포함되지 않았습니다.',
                    'categories': ['phone', 'email']
                },
                {
                    'revised_sentence': '민감한 정보를 제거한 안전한 문장으로 수정되었습니다.',
                    'categories': ['name', 'address']
                },
                {
                    'revised_sentence': '개인정보 보호를 위해 텍스트가 수정되었습니다.',
                    'categories': ['rrn']
                }
            ]
            
            for rev in dummy_revisions:
                revision = RevisionHistory(
                    user_id=dummy_user.id,
                    revised_sentence=rev['revised_sentence']
                )
                revision.set_categories(rev['categories'])
                db.session.add(revision)
            
            logger.info(f"더미 사용자 데이터 생성 완료: {dummy_username}")
        else:
            logger.info(f"더미 사용자 이미 존재: {dummy_username}")
        
        db.session.commit()
        logger.warning(
            f"기본 관리자 계정 설정 완료. " 
            f"프로덕션 환경에서는 반드시 비밀번호를 변경하세요! " 
            f"사용자명: {admin_username}, {super_admin_username}"
        )
        
        return True
    except Exception as e:
        logger.error(f"데이터베이스 초기화 실패: {e}")
        db.session.rollback()
        return False

