"""
Flask 확장 모듈

이 패키지는 Flask 앱에서 사용하는 확장들을 정의합니다.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# DB 인스턴스
db = SQLAlchemy()

# 로그인 관리자
login_manager = LoginManager()

# CSRF 보호
csrf = CSRFProtect()

# 마이그레이션
migrate = Migrate()

# 레이트 리미터
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

__all__ = ["db", "login_manager", "csrf", "migrate", "limiter"]
