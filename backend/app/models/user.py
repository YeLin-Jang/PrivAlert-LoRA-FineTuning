"""
사용자 및 RBAC 모델
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from app.extensions.database import db, Base

# 다대다 관계 테이블
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
    Column('created_at', DateTime, default=datetime.utcnow, nullable=False)
)


class User(Base, UserMixin):
    """
    사용자 모델
    - 민감 정보는 암호화되어 저장 (애플리케이션 레벨)
    - 비밀번호는 Argon2id로 해싱
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # Argon2id 해시
    salt = Column(String(255), nullable=False)  # Argon2는 자체 salt 포함하지만 추가 보안을 위해
    
    # 사용자 정보 (암호화 권장)
    full_name = Column(String(100), nullable=True)
    
    # 계정 상태
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # 이메일 인증 여부
    is_locked = Column(Boolean, default=False, nullable=False)  # 계정 잠금
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    
    # 세션 보안
    last_login_at = Column(DateTime, nullable=True)
    last_login_ip = Column(String(45), nullable=True)  # IPv6 지원
    current_session_id = Column(String(255), nullable=True)  # 세션 추적
    
    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # RBAC 관계
    roles = relationship('Role', secondary=user_roles, back_populates='users')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def has_role(self, role_name: str) -> bool:
        """사용자가 특정 역할을 가지고 있는지 확인"""
        return any(role.name == role_name for role in self.roles)
    
    def has_any_role(self, role_names: list) -> bool:
        """사용자가 여러 역할 중 하나라도 가지고 있는지 확인"""
        user_role_names = [role.name for role in self.roles]
        return any(role_name in user_role_names for role_name in role_names)
    
    def is_admin(self) -> bool:
        """관리자 여부 확인"""
        return self.has_role('admin')
    
    def to_dict(self, include_sensitive: bool = False):
        """사용자 정보를 딕셔너리로 변환 (민감 정보 제외)"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email if include_sensitive else self._mask_email(self.email),
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'roles': [role.name for role in self.roles],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None
        }
        if include_sensitive:
            data['full_name'] = self.full_name
        return data
    
    @staticmethod
    def _mask_email(email: str) -> str:
        """이메일 마스킹 (개인정보 보호)"""
        if '@' not in email:
            return email
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = '*' * len(local)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"


class Role(Base):
    """
    역할 모델 (RBAC)
    """
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    permissions = Column(Text, nullable=True)  # JSON 형태로 권한 저장 가능
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # RBAC 관계
    users = relationship('User', secondary=user_roles, back_populates='roles')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def to_dict(self):
        """역할 정보를 딕셔너리로 변환"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'permissions': self.permissions,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class UserRole(Base):
    """
    사용자-역할 관계 모델 (추가 메타데이터 필요 시 사용)
    """
    __tablename__ = 'user_role_metadata'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    
    # 추가 메타데이터
    assigned_by = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # 역할 만료 시간
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<UserRole user_id={self.user_id} role_id={self.role_id}>'

