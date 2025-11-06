"""
토큰 테이블 마이그레이션 스크립트
- metadata 컬럼 추가 (이메일 인증 토큰용)
- user_id를 nullable로 변경
- 일반 사용자 데이터는 삭제 (관리자 계정 보존)
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

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask
from app.extensions.database import db
from app.models.admin import AdminUser
# User 모델은 nickname 컬럼 추가 후에 import (nickname 컬럼이 없으면 에러 발생)
# from app.models.user import User
# Token 모델은 스키마 변경 후에 import (metadata 컬럼이 없으면 에러 발생)
# from app.models.token import Token
from app.models.session import UserSession
from app.models.audit_log import AuditLog
from app.utils.logger import get_logger

logger = get_logger(__name__)

def create_app_for_migration():
    """마이그레이션용 Flask 앱 생성"""
    app = Flask(__name__)
    
    # 환경 변수에서 데이터베이스 설정 로드
    import os
    from urllib.parse import quote_plus
    
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        # Docker 컨테이너 호스트명 'mysql'을 로컬 실행 시 'localhost'로 변경
        if mysql_host == 'mysql' and not os.path.exists('/.dockerenv'):
            mysql_host = 'localhost'
            logger.info(f"[정보] Docker 호스트명 'mysql'을 'localhost'로 변경 (로컬 실행)")
        
        mysql_port = os.getenv('MYSQL_PORT', '3306')
        mysql_database = os.getenv('MYSQL_DATABASE', 'privalert')
        mysql_user = os.getenv('MYSQL_USER', 'privalert_user')
        mysql_password = os.getenv('MYSQL_PASSWORD', '')
        
        mysql_password_encoded = quote_plus(mysql_password)
        
        database_url = (
            f"mysql+pymysql://{mysql_user}:{mysql_password_encoded}"
            f"@{mysql_host}:{mysql_port}/{mysql_database}"
            f"?charset=utf8mb4"
        )
        
        logger.info(f"[정보] 데이터베이스 연결: {mysql_host}:{mysql_port}/{mysql_database}")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    return app

def migrate_tokens_table():
    """토큰 테이블 마이그레이션"""
    app = create_app_for_migration()
    
    with app.app_context():
        try:
            # 1. users 테이블에 nickname 컬럼 추가 (먼저 추가해야 User 모델 사용 가능)
            try:
                result = db.session.execute(db.text("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                      AND TABLE_NAME = 'users' 
                      AND COLUMN_NAME = 'nickname'
                """))
                col_exists = result.scalar() > 0
                
                if not col_exists:
                    db.session.execute(db.text("""
                        ALTER TABLE users 
                        ADD COLUMN nickname VARCHAR(50) NULL 
                        COMMENT '별명 (이메일 대신 표시용)'
                    """))
                    db.session.commit()
                    logger.info("[성공] users.nickname 컬럼 추가 완료")
                else:
                    logger.info("[정보] users.nickname 컬럼이 이미 존재합니다")
            except Exception as e:
                logger.error(f"[실패] users.nickname 컬럼 추가 실패: {e}")
                raise
            
            # 2. User 모델 import (nickname 컬럼 추가 후)
            from app.models.user import User
            
            # 3. 관리자 계정 확인 및 백업
            admin_users = AdminUser.query.all()
            admin_count = len(admin_users)
            logger.info(f"관리자 계정 {admin_count}개 발견")
            
            if admin_count == 0:
                logger.warning("[경고] 관리자 계정이 없습니다. 마이그레이션 후 기본 관리자 계정을 생성하세요.")
            
            # 4. 기존 사용자 데이터 삭제 (관리자 계정 제외)
            user_count = User.query.count()
            logger.info(f"일반 사용자 {user_count}개 발견")
            
            if user_count > 0:
                deleted = User.query.delete()
                db.session.commit()
                logger.info(f"[성공] 일반 사용자 {deleted}개 삭제 완료")
            
            # 5. 기존 토큰 데이터 삭제 (관리자 관련 토큰은 없으므로 모두 삭제)
            # SQLAlchemy 모델 없이 직접 SQL로 삭제 (metadata 컬럼이 없어도 가능)
            result = db.session.execute(db.text("SELECT COUNT(*) FROM tokens"))
            token_count = result.scalar()
            logger.info(f"토큰 {token_count}개 발견")
            
            if token_count > 0:
                db.session.execute(db.text("DELETE FROM tokens"))
                db.session.commit()
                logger.info(f"[성공] 토큰 {token_count}개 삭제 완료")
            
            # 6. 테이블 스키마 변경 (먼저 스키마 변경 후 모델 사용)
            # metadata 컬럼 추가
            try:
                result = db.session.execute(db.text("""
                    SELECT COUNT(*) as count 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                      AND TABLE_NAME = 'tokens' 
                      AND COLUMN_NAME = 'metadata'
                """))
                col_exists = result.scalar() > 0
                
                if not col_exists:
                    db.session.execute(db.text("""
                        ALTER TABLE tokens 
                        ADD COLUMN metadata TEXT NULL 
                        COMMENT '이메일 인증 토큰용: 회원가입 정보 임시 저장 (JSON: {email, password_hash})'
                    """))
                    db.session.commit()
                    logger.info("[성공] metadata 컬럼 추가 완료")
                else:
                    logger.info("[정보] metadata 컬럼이 이미 존재합니다")
            except Exception as e:
                logger.error(f"[실패] metadata 컬럼 추가 실패: {e}")
                raise
            
            # user_id를 nullable로 변경
            try:
                result = db.session.execute(db.text("""
                    SELECT IS_NULLABLE 
                    FROM information_schema.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                      AND TABLE_NAME = 'tokens' 
                      AND COLUMN_NAME = 'user_id'
                """))
                is_nullable = result.scalar()
                
                if is_nullable == 'NO':
                    db.session.execute(db.text("""
                        ALTER TABLE tokens 
                        MODIFY COLUMN user_id INT NULL
                    """))
                    db.session.commit()
                    logger.info("[성공] user_id 컬럼을 nullable로 변경 완료")
                else:
                    logger.info("[정보] user_id 컬럼이 이미 nullable입니다")
            except Exception as e:
                logger.error(f"[실패] user_id 컬럼 변경 실패: {e}")
                raise
            
            # 7. Token 모델 import (스키마 변경 후)
            from app.models.token import Token
            
            # 8. 테이블 재생성 확인 (SQLAlchemy가 새 스키마로 생성)
            db.create_all()
            logger.info("[성공] 테이블 스키마 확인 완료")
            
            # 8. 관리자 계정 확인
            admin_users_after = AdminUser.query.all()
            admin_count_after = len(admin_users_after)
            
            if admin_count_after == admin_count:
                logger.info(f"[성공] 관리자 계정 {admin_count_after}개 보존 확인")
            else:
                logger.error(f"[실패] 관리자 계정 수가 변경되었습니다: {admin_count} -> {admin_count_after}")
                raise Exception("관리자 계정 보존 실패")
            
            logger.info("=" * 60)
            logger.info("[성공] 마이그레이션 완료!")
            logger.info("=" * 60)
            logger.info(f"   - 관리자 계정: {admin_count_after}개 보존")
            logger.info(f"   - 일반 사용자: 삭제 완료")
            logger.info(f"   - 토큰: 삭제 완료")
            logger.info(f"   - tokens.metadata 컬럼: 추가 완료")
            logger.info(f"   - tokens.user_id: nullable로 변경 완료")
            logger.info(f"   - users.nickname 컬럼: 추가 완료")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"[실패] 마이그레이션 실패: {e}", exc_info=True)
            return False

if __name__ == '__main__':
    # Windows 콘솔 인코딩 설정
    import sys
    import io
    if sys.platform == 'win32':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except:
            pass
    
    print("=" * 60)
    print("토큰 테이블 마이그레이션 시작")
    print("=" * 60)
    print("[주의] 이 스크립트는 다음을 수행합니다:")
    print("   1. 일반 사용자 데이터 삭제")
    print("   2. 토큰 데이터 삭제")
    print("   3. tokens 테이블에 metadata 컬럼 추가")
    print("   4. tokens.user_id를 nullable로 변경")
    print("   5. users 테이블에 nickname 컬럼 추가")
    print("   6. 관리자 계정 보존 확인")
    print("=" * 60)
    
    # 자동 실행 옵션 (환경 변수 또는 명령줄 인자)
    auto_yes = os.getenv('AUTO_YES', '').lower() == 'true'
    if len(sys.argv) > 1 and sys.argv[1] in ['--yes', '-y', '--auto']:
        auto_yes = True
    
    if not auto_yes:
        try:
            response = input("\n계속하시겠습니까? (yes/no): ")
            if response.lower() != 'yes':
                print("마이그레이션 취소됨")
                sys.exit(0)
        except (EOFError, KeyboardInterrupt):
            print("\n마이그레이션 취소됨")
            sys.exit(0)
    else:
        print("\n[자동 모드] 확인 없이 진행합니다...")
    
    success = migrate_tokens_table()
    
    if success:
        print("\n[성공] 마이그레이션 성공!")
        sys.exit(0)
    else:
        print("\n[실패] 마이그레이션 실패!")
        sys.exit(1)

