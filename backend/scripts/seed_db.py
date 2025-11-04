"""
초기 데이터 시드 스크립트

역할(admin, user) 생성 및 초기 관리자 계정 생성
"""
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import Role, User, UserRole

def seed_roles():
    """역할 시드"""
    roles_to_create = [
        {"name": "admin", "description": "관리자"},
        {"name": "user", "description": "일반 사용자"}
    ]
    
    created = 0
    for role_data in roles_to_create:
        role = Role.query.filter_by(name=role_data["name"]).first()
        if not role:
            role = Role(**role_data)
            db.session.add(role)
            created += 1
            print(f"✓ 역할 생성: {role_data['name']}")
        else:
            print(f"- 역할 이미 존재: {role_data['name']}")
    
    db.session.commit()
    print(f"\n역할 시드 완료: {created}개 생성")
    return created


def seed_admin_user(email: str, password: str):
    """초기 관리자 계정 생성"""
    # 이미 존재하는지 확인
    user = User.query.filter_by(email=email).first()
    if user:
        print(f"- 관리자 계정 이미 존재: {email}")
        return False
    
    # 사용자 생성
    user = User(email=email)
    user.set_password(password)
    db.session.add(user)
    
    # 관리자 역할 부여
    admin_role = Role.query.filter_by(name="admin").first()
    if not admin_role:
        print("❌ 오류: 'admin' 역할이 없습니다. 먼저 역할을 시드하세요.")
        return False
    
    user_role = UserRole(user=user, role=admin_role)
    db.session.add(user_role)
    db.session.commit()
    
    print(f"✓ 관리자 계정 생성: {email}")
    return True


def main():
    """메인 실행 함수"""
    app = create_app()
    
    with app.app_context():
        print("=" * 50)
        print("초기 데이터 시드 시작")
        print("=" * 50)
        
        # 역할 시드
        seed_roles()
        
        # 관리자 계정 생성 (환경변수 또는 기본값)
        admin_email = os.getenv("ADMIN_EMAIL", "admin@privalert.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123!")
        
        if admin_password == "admin123!":
            print("\n⚠️  경고: 기본 비밀번호를 사용하고 있습니다.")
            print("   운영 환경에서는 반드시 ADMIN_PASSWORD 환경변수를 설정하세요.")
        
        seed_admin_user(admin_email, admin_password)
        
        print("\n" + "=" * 50)
        print("초기 데이터 시드 완료")
        print("=" * 50)
        print(f"\n관리자 계정:")
        print(f"  이메일: {admin_email}")
        print(f"  비밀번호: {admin_password if admin_password != 'admin123!' else 'admin123! (변경 권장)'}")
        print("\n")


if __name__ == "__main__":
    main()

