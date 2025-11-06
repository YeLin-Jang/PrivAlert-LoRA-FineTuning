"""
세션 모델 (사용자 세션 관리)
보안: HTTP 환경에서 세션 회전 및 추적
"""
from datetime import datetime, timedelta
from app.extensions.database import db
from typing import Optional
import secrets


class UserSession(db.Model):
    """
    사용자 세션 모델
    보안:
    - 세션 ID는 예측 불가능하게 생성
    - 세션 회전 지원 (주기적 갱신)
    - HttpOnly, SameSite=Strict 쿠키 (Secure 미설정 - HTTP 환경)
    """
    __tablename__ = 'user_sessions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False, index=True)  # 예측 불가능한 세션 ID
    session_token = db.Column(db.String(64), nullable=False, index=True)  # 세션 검증 토큰 (Double Submit Cookie)
    
    # 세션 정보
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 지원
    user_agent = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # 세션 회전
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    
    # 보안: 인덱스 추가
    __table_args__ = (
        db.Index('idx_session_id', 'session_id'),
        db.Index('idx_user_id', 'user_id'),
        db.Index('idx_expires_at', 'expires_at'),
    )
    
    # 관계 설정
    user = db.relationship('User', backref='sessions')
    
    @staticmethod
    def generate_session_id() -> str:
        """
        안전한 세션 ID 생성
        보안: 예측 불가능한 세션 ID
        """
        return secrets.token_urlsafe(32)  # 32바이트 = 44자
    
    @staticmethod
    def generate_session_token() -> str:
        """
        세션 토큰 생성 (Double Submit Cookie용)
        """
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def create_session(user_id: int, ip_address: str = None, user_agent: str = None, 
                      expiry_hours: int = 24) -> 'UserSession':
        """
        새 세션 생성
        """
        session_id = UserSession.generate_session_id()
        session_token = UserSession.generate_session_token()
        
        session = UserSession(
            user_id=user_id,
            session_id=session_id,
            session_token=session_token,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        db.session.add(session)
        db.session.commit()
        
        return session
    
    def rotate_session(self) -> 'UserSession':
        """
        세션 회전 (보안 강화)
        기존 세션 무효화 후 새 세션 생성
        """
        self.is_active = False
        
        # 새 세션 생성
        new_session = UserSession.create_session(
            user_id=self.user_id,
            ip_address=self.ip_address,
            user_agent=self.user_agent
        )
        
        db.session.commit()
        return new_session
    
    def update_activity(self):
        """
        마지막 활동 시간 업데이트
        """
        self.last_activity = datetime.utcnow()
        db.session.commit()
    
    def is_expired(self) -> bool:
        """
        세션 만료 확인
        """
        return self.expires_at < datetime.utcnow() or not self.is_active
    
    def revoke(self):
        """
        세션 무효화
        """
        self.is_active = False
        db.session.commit()
    
    @staticmethod
    def find_by_session_id(session_id: str) -> Optional['UserSession']:
        """
        세션 ID로 세션 검색
        """
        session = UserSession.query.filter_by(
            session_id=session_id,
            is_active=True
        ).first()
        
        if session and session.is_expired():
            session.revoke()
            return None
        
        return session
    
    @staticmethod
    def revoke_all_user_sessions(user_id: int, except_session_id: str = None):
        """
        사용자의 모든 세션 무효화 (현재 세션 제외)
        """
        query = UserSession.query.filter_by(user_id=user_id, is_active=True)
        if except_session_id:
            query = query.filter(UserSession.session_id != except_session_id)
        
        sessions = query.all()
        for session in sessions:
            session.revoke()
        
        db.session.commit()
    
    @staticmethod
    def cleanup_expired_sessions():
        """
        만료된 세션 정리 (백그라운드 작업)
        """
        deleted = UserSession.query.filter(
            UserSession.expires_at < datetime.utcnow()
        ).delete()
        db.session.commit()
        return deleted
    
    def to_dict(self) -> dict:
        """
        세션 정보를 딕셔너리로 변환
        """
        return {
            'id': self.id,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'is_active': self.is_active,
        }
    
    def __repr__(self):
        return f'<UserSession {self.session_id[:8]}... for user {self.user_id}>'



