"""
관리자 계정 비밀번호 업데이트 스크립트
.env 파일의 비밀번호로 기존 계정 비밀번호를 업데이트합니다.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask

# 프로젝트 루트의 .env 파일 로드
root_dir = Path(__file__).parent.parent  # backend/update_admin_password.py -> 프로젝트 루트
env_path = root_dir / '.env'
load_dotenv(dotenv_path=env_path)

# 최소한의 Flask 앱 생성 (라우트 로드 없이)
app = Flask(__name__)

# 데이터베이스만 초기화
from app.extensions.database import init_db, db
from app.models.admin import AdminUser

# 데이터베이스 설정
# 로컬 실행 시 mysql 호스트를 localhost로 변경
if os.getenv('MYSQL_HOST') == 'mysql':
    os.environ['MYSQL_HOST'] = 'localhost'
    
init_db(app)

with app.app_context():
    try:
        # 환경 변수에서 비밀번호 가져오기
        admin_username = os.getenv('DEFAULT_ADMIN_USERNAME', 'admin')
        admin_password = os.getenv('DEFAULT_ADMIN_PASSWORD')
        super_admin_username = os.getenv('DEFAULT_SUPER_ADMIN_USERNAME', 'super_admin')
        super_admin_password = os.getenv('DEFAULT_SUPER_ADMIN_PASSWORD')
        
        if not admin_password:
            print("❌ 오류: DEFAULT_ADMIN_PASSWORD 환경 변수가 설정되지 않았습니다.")
            print(f"   .env 파일 위치: {env_path}")
            sys.exit(1)
        
        if not super_admin_password:
            print("❌ 오류: DEFAULT_SUPER_ADMIN_PASSWORD 환경 변수가 설정되지 않았습니다.")
            print(f"   .env 파일 위치: {env_path}")
            sys.exit(1)
        
        # admin 계정 업데이트
        admin = AdminUser.find_by_username(admin_username)
        if admin:
            admin.set_password(admin_password)
            print(f"✅ {admin_username} 계정 비밀번호 업데이트 완료")
        else:
            print(f"⚠️  {admin_username} 계정이 존재하지 않습니다. 새로 생성합니다.")
            new_admin = AdminUser.create_default_admin(
                username=admin_username,
                password=admin_password,
                role='admin'
            )
            db.session.add(new_admin)
        
        # super_admin 계정 업데이트
        super_admin = AdminUser.find_by_username(super_admin_username)
        if super_admin:
            super_admin.set_password(super_admin_password)
            print(f"✅ {super_admin_username} 계정 비밀번호 업데이트 완료")
        else:
            print(f"⚠️  {super_admin_username} 계정이 존재하지 않습니다. 새로 생성합니다.")
            new_super_admin = AdminUser.create_default_admin(
                username=super_admin_username,
                password=super_admin_password,
                role='super_admin'
            )
            db.session.add(new_super_admin)
        
        db.session.commit()
        print("\n✅ 모든 관리자 계정 비밀번호 업데이트 완료!")
        print(f"   - {admin_username}: .env 파일의 DEFAULT_ADMIN_PASSWORD 사용")
        print(f"   - {super_admin_username}: .env 파일의 DEFAULT_SUPER_ADMIN_PASSWORD 사용")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

