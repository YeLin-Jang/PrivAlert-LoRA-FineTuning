"""
Flask-Login 확장
- 세션 관리
- 사용자 로드
"""

import logging
from flask_login import LoginManager, UserMixin
from app.extensions.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    """사용자 로드 (Flask-Login용)"""
    try:
        db = get_db()
        user = db.query(User).filter_by(id=int(user_id)).first()
        return user if user and user.is_active else None
    except Exception as e:
        logger.error(f"사용자 로드 실패: {e}")
        return None


def init_login_manager(app):
    """Flask-Login 초기화"""
    login_manager.init_app(app)
    
    # 세션 보안 설정
    login_manager.session_protection = "strong"  # 세션 하이재킹 방지
    login_manager.login_view = "auth.login"  # 로그인 필요 시 리다이렉트할 뷰
    login_manager.login_message = "로그인이 필요합니다"
    login_manager.login_message_category = "info"
    
    # 세션 설정
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS에서만 쿠키 전송
    app.config['SESSION_COOKIE_HTTPONLY'] = True  # JavaScript 접근 차단
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF 방지
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1시간 (초)
    
    logger.info("Flask-Login 초기화 완료")

