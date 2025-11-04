"""
데이터베이스 모델
"""
from app.extensions.database import db
from app.models.admin import AdminUser

__all__ = ['db', 'AdminUser']

