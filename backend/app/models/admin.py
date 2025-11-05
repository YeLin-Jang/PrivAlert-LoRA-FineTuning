"""
관리자 사용자 모델
보안: 비밀번호는 해시화되어 저장됨
"""
from datetime import datetime
from app.extensions.database import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from typing import Optional

class AdminUser(db.Model):
    """
    관리자 사용자 모델
    보안: SQLAlchemy ORM 사용으로 SQL 인젝션 방지
    """
    __tablename__ = 'admin_users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='admin')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # 보안: 인덱스 추가 (조회 성능 향상)
    __table_args__ = (
        db.Index('idx_username', 'username'),
        db.Index('idx_role', 'role'),
    )
    
    def set_password(self, password: str) -> None:
        """
        비밀번호 설정 (해시화)
        보안: bcrypt를 통한 안전한 해시 저장
        """
        if len(password) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다")
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """
        비밀번호 확인
        보안: 타임링 공격 방지를 위한 안전한 검증
        """
        return check_password_hash(self.password_hash, password)
    
    def generate_token(self) -> str:
        """
        JWT 토큰 생성
        """
        return create_access_token(
            identity=self.id,
            additional_claims={'role': self.role, 'username': self.username}
        )
    
    def to_dict(self) -> dict:
        """
        사용자 정보를 딕셔너리로 변환 (비밀번호 제외)
        보안: 민감 정보 제외
        """
        return {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
    
    @staticmethod
    def find_by_username(username: str) -> Optional['AdminUser']:
        """
        사용자명으로 사용자 검색
        보안: SQLAlchemy ORM 사용으로 SQL 인젝션 방지
        """
        return AdminUser.query.filter_by(username=username).first()
    
    @staticmethod
    def create_default_admin(username: str = 'admin', password: str = None, role: str = 'admin') -> 'AdminUser':
        """
        기본 관리자 계정 생성 (초기화용)
        보안: 비밀번호는 환경 변수에서 가져와야 하며, 해시화되어 저장됨
        """
        if not password:
            raise ValueError("비밀번호는 필수입니다. 환경 변수에서 설정하세요.")
        admin = AdminUser(
            username=username,
            role=role,
            is_active=True
        )
        admin.set_password(password)
        return admin
    
    def __repr__(self):
        return f'<AdminUser {self.username}>'

