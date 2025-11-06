#!/usr/bin/env python3
"""
특정 이메일 주소의 사용자 삭제 스크립트
"""
import sys
import os
from pathlib import Path

# 환경 변수 로드 (.env 파일)
env_file = Path(__file__).parent.parent.parent / '.env'
if env_file.exists():
    with open(env_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import create_app
from app.extensions.database import db
from app.models.user import User
from app.models.session import UserSession
from app.models.token import Token

def delete_users_by_email(emails):
    """지정된 이메일 주소의 사용자들을 삭제"""
    app = create_app()
    
    with app.app_context():
        try:
            # 삭제할 사용자 조회
            users = User.query.filter(User.email.in_(emails)).all()
            
            if not users:
                print(f"삭제할 사용자를 찾을 수 없습니다: {emails}")
                return
            
            print(f"삭제할 사용자 {len(users)}명을 찾았습니다:")
            for user in users:
                print(f"  - ID: {user.id}, Email: {user.email}")
            
            # 사용자 삭제 (관련 데이터를 먼저 삭제)
            for user in users:
                user_id = user.id
                user_email = user.email
                
                # 관련 데이터 확인 및 삭제
                sessions = UserSession.query.filter_by(user_id=user_id).all()
                tokens = Token.query.filter_by(user_id=user_id).all()
                
                print(f"\n사용자 {user_email} 삭제 중...")
                print(f"  - 세션: {len(sessions)}개")
                print(f"  - 토큰: {len(tokens)}개")
                
                # autoflush 방지
                with db.session.no_autoflush:
                    # 관련 세션 먼저 삭제
                    for session in sessions:
                        db.session.delete(session)
                    
                    # 관련 토큰 삭제
                    for token in tokens:
                        db.session.delete(token)
                    
                    # 사용자 삭제
                    db.session.delete(user)
            
            # 변경사항 커밋
            db.session.commit()
            
            print(f"\n✅ 성공적으로 {len(users)}명의 사용자를 삭제했습니다.")
            
            # 삭제 확인
            remaining = User.query.filter(User.email.in_(emails)).count()
            if remaining == 0:
                print("✅ 삭제 확인 완료: 모든 사용자가 삭제되었습니다.")
            else:
                print(f"⚠️  경고: {remaining}명의 사용자가 여전히 존재합니다.")
                
        except Exception as e:
            db.session.rollback()
            print(f"❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    emails_to_delete = [
        'securingring@gmail.com',
        'honghhj66@ewhain.net'
    ]
    
    print("=" * 60)
    print("사용자 삭제 스크립트")
    print("=" * 60)
    print(f"삭제할 이메일: {emails_to_delete}")
    print()
    
    delete_users_by_email(emails_to_delete)

