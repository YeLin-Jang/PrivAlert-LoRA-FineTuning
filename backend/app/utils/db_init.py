"""
데이터베이스 초기화 유틸리티
"""
import os
from app.extensions.database import db
# 모든 모델을 import하여 db.create_all()이 모든 테이블을 생성하도록 함
from app.models.user import User, UserFilteringSettings, RevisionHistory  # noqa: F401
from app.models.token import Token  # noqa: F401
from app.models.session import UserSession  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.utils.logger import get_logger

logger = get_logger(__name__)
_logged_error = False

def _create_mysql_user_with_root():
    """MySQL root 계정으로 사용자와 데이터베이스 자동 생성"""
    try:
        import pymysql
    except ImportError:
        return False
    
    root_password = os.getenv('MYSQL_ROOT_PASSWORD', '')
    if not root_password:
        return False
    
    config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', '3306')),
        'user': 'root',
        'password': root_password,
        'charset': 'utf8mb4'
    }
    
    try:
        conn = pymysql.connect(**config)
        with conn.cursor() as cursor:
            db_name = os.getenv('MYSQL_DATABASE', 'privalert')
            db_user = os.getenv('MYSQL_USER', 'privalert_user')
            db_password = os.getenv('MYSQL_PASSWORD', '')
            
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.execute(f"DROP USER IF EXISTS '{db_user}'@'localhost'")
            cursor.execute(f"DROP USER IF EXISTS '{db_user}'@'%'")
            
            password = db_password or 'privalert_default_password_change_me'
            for host in ['localhost', '%']:
                cursor.execute(f"CREATE USER '{db_user}'@'{host}' IDENTIFIED BY '{password}'")
                cursor.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'{host}'")
            
            cursor.execute("FLUSH PRIVILEGES")
        
        conn.commit()
        conn.close()
        logger.info(f"MySQL 사용자 '{db_user}' 및 데이터베이스 '{db_name}' 생성 완료")
        return True
    except Exception as e:
        logger.warning(f"MySQL 사용자 자동 생성 실패: {e}")
        return False

def init_database():
    """데이터베이스 초기화 및 테이블 생성"""
    global _logged_error
    
    try:
        db.create_all()
        logger.info("데이터베이스 테이블 생성 완료")
        _logged_error = False
        return True
    except Exception as e:
        if _logged_error:
            return False
        
        error_msg = str(e)
        is_access_denied = "Access denied" in error_msg or "1045" in error_msg
        
        if is_access_denied:
            logger.warning(f"데이터베이스 초기화 실패: {type(e).__name__} - {error_msg} | 원인: MySQL 사용자 권한 문제")
            
            logger.info("MySQL 사용자 자동 생성 시도 중...")
            if _create_mysql_user_with_root():
                try:
                    db.create_all()
                    logger.info("데이터베이스 테이블 생성 완료")
                    _logged_error = False
                    return True
                except Exception as retry_e:
                    logger.warning(f"사용자 생성 후 재시도 실패: {retry_e}")
            else:
                user = os.getenv('MYSQL_USER', 'privalert_user')
                db_name = os.getenv('MYSQL_DATABASE', 'privalert')
                logger.warning(
                    f"해결 방법: MySQL root로 접속하여 다음 SQL 실행:\n"
                    f"  CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n"
                    f"  CREATE USER IF NOT EXISTS '{user}'@'localhost' IDENTIFIED BY 'your-password';\n"
                    f"  CREATE USER IF NOT EXISTS '{user}'@'%' IDENTIFIED BY 'your-password';\n"
                    f"  GRANT ALL PRIVILEGES ON {db_name}.* TO '{user}'@'localhost';\n"
                    f"  GRANT ALL PRIVILEGES ON {db_name}.* TO '{user}'@'%';\n"
                    f"  FLUSH PRIVILEGES;"
                )
        else:
            logger.warning(f"데이터베이스 초기화 실패: {type(e).__name__} - {error_msg}")
        
        _logged_error = True
        try:
            if db.session:
                db.session.rollback()
        except Exception:
            pass
        
        return False
