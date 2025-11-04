"""
데이터베이스 초기화 스크립트
- 테이블 생성
- 기본 역할 생성
- 관리자 계정 생성 (선택)
"""

import os
import sys
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 프로젝트 루트 경로 찾기 (PrivAlert/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT_DIR, '.env')

# 프로젝트 루트의 .env 파일 우선 로드
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)
else:
    # Fallback: 현재 디렉토리의 .env 파일
    load_dotenv()

from app import create_app
from app.extensions.database import db, Database
from app.models.user import User, Role
from app.services.password_service import password_service

def init_database():
    """데이터베이스 초기화"""
    import time
    
    # 데이터베이스 연결 대기 (Docker 환경)
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            app = create_app()
            with app.app_context():
                # 연결 테스트
                from app.extensions.database import db_engine
                from sqlalchemy import text
                if db_engine:
                    with db_engine.connect() as conn:
                        conn.execute(text("SELECT 1"))
                        conn.commit()
                break
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                print(f"❌ 데이터베이스 연결 실패: {e}")
                raise
            print(f"⏳ 데이터베이스 연결 대기 중... ({retry_count}/{max_retries})")
            time.sleep(2)
    
    app = create_app()
    
    with app.app_context():
        # 테이블 생성
        print("테이블 생성 중...")
        Database.create_all()
        print("✓ 테이블 생성 완료")
        
        # 기본 역할 생성
        print("\n기본 역할 생성 중...")
        roles_data = [
            {'name': 'admin', 'description': '관리자 - 모든 권한'},
            {'name': 'moderator', 'description': '모더레이터 - 콘텐츠 관리 권한'},
            {'name': 'user', 'description': '일반 사용자'}
        ]
        
        for role_data in roles_data:
            role = db.query(Role).filter_by(name=role_data['name']).first()
            if not role:
                role = Role(**role_data)
                db.add(role)
                print(f"  ✓ 역할 생성: {role_data['name']}")
            else:
                print(f"  - 역할 이미 존재: {role_data['name']}")
        
        db.commit()
        print("✓ 기본 역할 생성 완료")
        
        # 관리자 계정 생성 (환경 변수에서)
        admin_username = os.getenv('ADMIN_USERNAME')
        admin_email = os.getenv('ADMIN_EMAIL')
        admin_password = os.getenv('ADMIN_PASSWORD')
        
        if admin_username and admin_email and admin_password:
            print("\n관리자 계정 생성 중...")
            admin_user = db.query(User).filter_by(username=admin_username).first()
            
            if not admin_user:
                # 비밀번호 해싱
                password_hash, salt = password_service.hash_password(admin_password)
                
                admin_user = User(
                    username=admin_username,
                    email=admin_email,
                    password_hash=password_hash,
                    salt=salt,
                    is_active=True,
                    is_verified=True,
                    is_locked=False
                )
                
                # 관리자 역할 할당
                admin_role = db.query(Role).filter_by(name='admin').first()
                if admin_role:
                    admin_user.roles.append(admin_role)
                
                db.add(admin_user)
                db.commit()
                print(f"  ✓ 관리자 계정 생성: {admin_username}")
            else:
                print(f"  - 관리자 계정 이미 존재: {admin_username}")
        else:
            print("\n관리자 계정 생성 건너뜀 (환경 변수 미설정)")
        
        print("\n✓ 데이터베이스 초기화 완료!")


if __name__ == '__main__':
    init_database()

