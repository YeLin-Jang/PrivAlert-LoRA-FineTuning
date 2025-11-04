"""
비밀번호 변경 스크립트 (간단한 방법)

서버 실행 없이 DB에서 직접 비밀번호 변경
"""
import sys
import os

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User

def change_user_password(email: str, new_password: str):
    """사용자 비밀번호 변경"""
    app = create_app()
    
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"❌ 사용자를 찾을 수 없습니다: {email}")
            return False
        
        user.set_password(new_password)
        db.session.commit()
        
        print(f"✓ 비밀번호 변경 완료: {email}")
        return True


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("=" * 60)
        print("비밀번호 변경 스크립트")
        print("=" * 60)
        print("\n사용법:")
        print("  python scripts/change_password.py <이메일> <새비밀번호>")
        print("\n예시:")
        print("  python scripts/change_password.py admin@privalert.com newpass123")
        print("=" * 60)
        sys.exit(1)
    
    email = sys.argv[1]
    new_password = sys.argv[2]
    
    if len(new_password) < 8:
        print("⚠️  경고: 비밀번호는 최소 8자 이상 권장")
        confirm = input("계속하시겠습니까? (y/n): ")
        if confirm.lower() != 'y':
            print("취소되었습니다.")
            sys.exit(0)
    
    change_user_password(email, new_password)

