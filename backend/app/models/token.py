"""
토큰 모델 (이메일 검증, 비밀번호 재설정)
보안: 토큰 원문은 DB에 저장하지 않고 해시만 저장
"""
from datetime import datetime, timedelta
from app.extensions.database import db
from typing import Optional
import secrets
import hashlib
import json


class Token(db.Model):
    """
    토큰 모델 (이메일 검증, 비밀번호 재설정)
    보안: 
    - 토큰 원문은 이메일 전송 후 폐기
    - DB에는 SHA256 해시만 저장
    - 단발성 토큰 (사용 후 삭제)
    - 만료 시간 설정
    """
    __tablename__ = 'tokens'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)  # SHA256 해시
    token_type = db.Column(db.String(50), nullable=False, index=True)  # 'email_verification', 'password_reset'
    used = db.Column(db.Boolean, default=False, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    
    # 보안: 인덱스 추가
    __table_args__ = (
        db.Index('idx_token_hash', 'token_hash'),
        db.Index('idx_token_type', 'token_type'),
        db.Index('idx_expires_at', 'expires_at'),
        db.Index('idx_user_id_type', 'user_id', 'token_type'),
    )
    
    # 관계 설정
    user = db.relationship('User', backref='tokens')
    
    @staticmethod
    def generate_token() -> str:
        """
        안전한 토큰 생성 (URL-safe)
        보안: secrets 모듈 사용으로 예측 불가능한 토큰 생성
        """
        return secrets.token_urlsafe(32)  # 32바이트 = 44자 URL-safe 문자열
    
    @staticmethod
    def hash_token(token: str) -> str:
        """
        토큰 해시 생성 (SHA256)
        보안: 토큰 원문은 저장하지 않고 해시만 저장
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def create_token(user_id: int, token_type: str, expiry_hours: int = 24) -> tuple[str, 'Token']:
        """
        새 토큰 생성 및 저장
        반환: (토큰 원문, Token 객체)
        보안: 토큰 원문은 이메일 전송용으로만 반환, DB에는 해시 저장
        """
        # 기존 미사용 토큰 무효화
        Token.query.filter_by(
            user_id=user_id,
            token_type=token_type,
            used=False
        ).delete()
        
        # 새 토큰 생성
        token_plaintext = Token.generate_token()
        token_hash = Token.hash_token(token_plaintext)
        
        token = Token(
            user_id=user_id,
            token_hash=token_hash,
            token_type=token_type,
            used=False,
            expires_at=datetime.utcnow() + timedelta(hours=expiry_hours)
        )
        
        db.session.add(token)
        db.session.commit()
        
        return token_plaintext, token
    
    @staticmethod
    def verify_token(token_plaintext: str, token_type: str) -> Optional['Token']:
        """
        토큰 검증
        보안: 원문 토큰을 해시하여 DB의 해시와 비교
        """
        token_hash = Token.hash_token(token_plaintext)
        
        token = Token.query.filter_by(
            token_hash=token_hash,
            token_type=token_type,
            used=False
        ).first()
        
        if not token:
            return None
        
        # 만료 확인
        if token.expires_at < datetime.utcnow():
            return None
        
        return token
    
    def mark_as_used(self):
        """
        토큰 사용 처리 (단발성)
        """
        self.used = True
        self.used_at = datetime.utcnow()
        db.session.commit()
    
    @staticmethod
    def cleanup_expired_tokens():
        """
        만료된 토큰 정리 (백그라운드 작업)
        """
        deleted = Token.query.filter(
            Token.expires_at < datetime.utcnow()
        ).delete()
        db.session.commit()
        return deleted
    
    def __repr__(self):
        return f'<Token {self.token_type} for user {self.user_id}>'

