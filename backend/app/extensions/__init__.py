"""
Flask 확장 모듈

이 패키지는 Flask 앱에서 사용하는 확장들을 정의합니다.
"""

from app.extensions.database import db

__all__ = ['db']
