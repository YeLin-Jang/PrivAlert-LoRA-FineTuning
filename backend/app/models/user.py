"""
일반 사용자 모델
보안: 비밀번호는 해시화되어 저장됨
"""
from datetime import datetime
from app.extensions.database import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from typing import Optional
import json

class User(db.Model):
    """
    일반 사용자 모델
    보안: SQLAlchemy ORM 사용으로 SQL 인젝션 방지
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # 관계: 필터링 설정 (1:1)
    filtering_settings = db.relationship(
        'UserFilteringSettings', 
        backref='user', 
        uselist=False, 
        cascade='all, delete-orphan'
    )
    
    # 관계: 수정 기록 (1:N)
    revision_histories = db.relationship(
        'RevisionHistory',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='desc(RevisionHistory.created_at)'
    )
    
    # 보안: 인덱스 추가 (조회 성능 향상)
    __table_args__ = (
        db.Index('idx_username', 'username'),
        db.Index('idx_email', 'email'),
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
        보안: role 클레임 포함 (일반 사용자)
        """
        return create_access_token(
            identity=self.id,
            additional_claims={'username': self.username, 'email': self.email, 'role': 'user'}
        )
    
    def to_dict(self) -> dict:
        """
        사용자 정보를 딕셔너리로 변환 (비밀번호 제외)
        보안: 민감 정보 제외
        """
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
    
    @staticmethod
    def find_by_username(username: str) -> Optional['User']:
        """
        사용자명으로 사용자 검색
        보안: SQLAlchemy ORM 사용으로 SQL 인젝션 방지
        """
        return User.query.filter_by(username=username).first()
    
    @staticmethod
    def find_by_email(email: str) -> Optional['User']:
        """
        이메일로 사용자 검색
        보안: SQLAlchemy ORM 사용으로 SQL 인젝션 방지
        """
        return User.query.filter_by(email=email).first()
    
    def __repr__(self):
        return f'<User {self.username}>'


class UserFilteringSettings(db.Model):
    """
    사용자 필터링 설정 모델
    보안: 민감 정보는 저장하지 않음
    """
    __tablename__ = 'user_filtering_settings'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    
    # 필터링 옵션 (JSON으로 저장)
    # 보안: 민감 정보가 아닌 설정만 저장
    detection_options = db.Column(db.Text, nullable=False, default='{}')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def set_detection_options(self, options: dict) -> None:
        """
        탐지 옵션 설정
        보안: JSON 직렬화 전 검증
        """
        # 허용된 옵션 키만 저장
        allowed_keys = {
            'face', 'fingerprint', 'phone', 'rrn', 'passport', 'ip_address',
            'email', 'account', 'school', 'workplace', 'name', 'address',
            'driverLicense', 'postalCode'
        }
        
        # 필터링: 허용된 키만 저장
        filtered_options = {k: bool(v) for k, v in options.items() if k in allowed_keys}
        self.detection_options = json.dumps(filtered_options, ensure_ascii=False)
    
    def get_detection_options(self) -> dict:
        """
        탐지 옵션 가져오기
        """
        try:
            return json.loads(self.detection_options)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    def to_dict(self) -> dict:
        """
        설정을 딕셔너리로 변환
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'detection_options': self.get_detection_options(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def __repr__(self):
        return f'<UserFilteringSettings user_id={self.user_id}>'


class RevisionHistory(db.Model):
    """
    LLM 수정 문장 기록 모델
    보안: 민감 데이터는 저장하지 않고 수정된 문장만 저장
    """
    __tablename__ = 'revision_histories'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # 보안: 원본 텍스트는 저장하지 않음, 수정된 문장만 저장
    revised_sentence = db.Column(db.Text, nullable=False)
    
    # 카테고리 정보 (어떤 종류의 민감 정보가 수정되었는지)
    categories = db.Column(db.Text, nullable=True)  # JSON 형식
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # 보안: 인덱스 추가 (조회 성능 향상)
    __table_args__ = (
        db.Index('idx_user_created', 'user_id', 'created_at'),
    )
    
    def set_categories(self, categories: list) -> None:
        """
        카테고리 설정
        """
        if categories:
            self.categories = json.dumps(categories, ensure_ascii=False)
        else:
            self.categories = None
    
    def get_categories(self) -> list:
        """
        카테고리 가져오기
        """
        if not self.categories:
            return []
        try:
            return json.loads(self.categories)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def to_dict(self) -> dict:
        """
        기록을 딕셔너리로 변환
        보안: 민감 정보 제외
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'revised_sentence': self.revised_sentence,
            'categories': self.get_categories(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
    
    def __repr__(self):
        return f'<RevisionHistory id={self.id} user_id={self.user_id}>'

