"""
사용자 및 권한 모델 (RBAC)

시큐어코딩 가이드 준수:
- 권한은 서버 측(DB)에서 판단, 쿠키에는 세션 ID만 저장
- 비밀번호는 솔트+해시로 저장 (werkzeug.security 또는 passlib)
- 모든 보안 관련 상태는 서버 측에서 관리
"""
from datetime import datetime
from flask_login import UserMixin
from app.extensions import db


class Role(db.Model):
    """역할 모델 (RBAC)"""
    __tablename__ = "roles"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True, nullable=False, index=True)  # 'admin' / 'user'
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 관계
    users = db.relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Role {self.name}>"


class User(db.Model, UserMixin):
    """사용자 모델"""
    __tablename__ = "users"
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)  # bcrypt/argon2/PBKDF2 결과
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # 서버 측에서 권한 판단 (쿠키에 role 안 넣음 - 가이드 권고 반영)
    roles = db.relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    
    def set_password(self, password: str):
        """비밀번호 설정 (솔트 포함 해시)"""
        from werkzeug.security import generate_password_hash
        # werkzeug는 PBKDF2 사용 (솔트 내장)
        # 필요시 passlib[bcrypt]로 교체 가능
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """비밀번호 확인"""
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)
    
    def has_role(self, role_name: str) -> bool:
        """특정 역할 보유 여부 확인 (서버 측 판단)"""
        return any(ur.role.name == role_name for ur in self.roles)
    
    def is_admin(self) -> bool:
        """관리자 여부 확인"""
        return self.has_role("admin")
    
    def __repr__(self):
        return f"<User {self.email}>"


class UserRole(db.Model):
    """사용자-역할 매핑 테이블 (다대다)"""
    __tablename__ = "user_roles"
    __table_args__ = (
        db.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    role_id = db.Column(
        db.Integer, 
        db.ForeignKey("roles.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 관계
    user = db.relationship("User", back_populates="roles")
    role = db.relationship("Role", back_populates="users")
    
    def __repr__(self):
        return f"<UserRole user_id={self.user_id} role_id={self.role_id}>"

