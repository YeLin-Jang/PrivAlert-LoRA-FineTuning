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
import os
import logging

logger = logging.getLogger(__name__)

# 암호화 키 로드 (Fernet 사용)
try:
    from cryptography.fernet import Fernet
    FERNET_AVAILABLE = True
except ImportError:
    FERNET_AVAILABLE = False
    logger.warning("cryptography.fernet이 설치되지 않았습니다. 토큰 metadata 암호화이 작동하지 않습니다.")


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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True, index=True)  # 이메일 인증 토큰은 user_id 없음
    token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)  # SHA256 해시
    token_type = db.Column(db.String(50), nullable=False, index=True)  # 'email_verification', 'password_reset'
    # 이메일 인증 토큰용: 회원가입 정보 임시 저장 (암호화된 JSON)
    # 주의: SQLAlchemy에서 'metadata'는 예약어이므로 'token_metadata' 사용
    # 보안: Fernet 암호화를 사용하여 email과 password_hash를 암호화하여 저장
    token_metadata = db.Column('metadata', db.Text, nullable=True)  # 암호화된 JSON: {email, password_hash}
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
    def _encrypt_metadata(metadata: dict) -> Optional[str]:
        """
        metadata 암호화 (Fernet 사용)
        보안: 민감한 정보(이메일, 비밀번호 해시)를 암호화하여 저장
        """
        if not metadata:
            return None
        
        if not FERNET_AVAILABLE:
            logger.warning("Fernet이 사용 불가능합니다. metadata를 평문으로 저장합니다 (보안 경고)")
            return json.dumps(metadata)
        
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            logger.warning("ENCRYPTION_KEY 환경 변수가 설정되지 않았습니다. metadata를 평문으로 저장합니다 (보안 경고)")
            return json.dumps(metadata)
        
        try:
            # Fernet 키로 암호화
            key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
            # Fernet 키는 32바이트 URL-safe base64-encoded 문자열이어야 함
            # 만약 키가 올바른 형식이 아니면 새로 생성하거나 에러 처리
            try:
                f = Fernet(key_bytes)
            except ValueError:
                # 키가 올바른 형식이 아닌 경우, 키를 해시하여 32바이트 키 생성
                import base64
                key_hash = hashlib.sha256(key_bytes).digest()
                key_base64 = base64.urlsafe_b64encode(key_hash)
                f = Fernet(key_base64)
            
            # JSON 문자열로 변환 후 암호화
            json_str = json.dumps(metadata)
            encrypted = f.encrypt(json_str.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"metadata 암호화 실패: {e}")
            # 암호화 실패 시 평문 저장 (보안 경고, 하지만 기능은 작동)
            return json.dumps(metadata)
    
    @staticmethod
    def _decrypt_metadata(encrypted_metadata: str) -> Optional[dict]:
        """
        metadata 복호화
        """
        if not encrypted_metadata:
            return None
        
        if not FERNET_AVAILABLE:
            # Fernet이 없으면 평문 JSON으로 간주
            try:
                return json.loads(encrypted_metadata)
            except:
                return None
        
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            # 키가 없으면 평문 JSON으로 간주
            try:
                return json.loads(encrypted_metadata)
            except:
                return None
        
        try:
            # Fernet 키로 복호화
            key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
            try:
                f = Fernet(key_bytes)
            except ValueError:
                # 키가 올바른 형식이 아닌 경우
                import base64
                key_hash = hashlib.sha256(key_bytes).digest()
                key_base64 = base64.urlsafe_b64encode(key_hash)
                f = Fernet(key_base64)
            
            # 복호화 시도
            try:
                decrypted = f.decrypt(encrypted_metadata.encode())
                return json.loads(decrypted.decode())
            except:
                # 암호화된 데이터가 아닌 경우 (이전 버전 호환)
                return json.loads(encrypted_metadata)
        except Exception as e:
            logger.warning(f"metadata 복호화 실패, 평문으로 시도: {e}")
            # 복호화 실패 시 평문 JSON으로 시도 (이전 버전 호환)
            try:
                return json.loads(encrypted_metadata)
            except:
                return None
    
    @staticmethod
    def hash_token(token: str) -> str:
        """
        토큰 해시 생성 (SHA256)
        보안: 토큰 원문은 저장하지 않고 해시만 저장
        """
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def create_token(user_id: Optional[int], token_type: str, expiry_hours: int = 24, metadata: Optional[dict] = None) -> tuple[str, 'Token']:
        """
        새 토큰 생성 및 저장
        반환: (토큰 원문, Token 객체)
        보안: 토큰 원문은 이메일 전송용으로만 반환, DB에는 해시 저장
        
        Args:
            user_id: 사용자 ID (이메일 인증 토큰은 None)
            token_type: 토큰 타입 ('email_verification', 'password_reset')
            expiry_hours: 만료 시간 (시간)
            metadata: 메타데이터 (이메일 인증 토큰용: {email, password_hash})
        """
        # 기존 미사용 토큰 무효화 (같은 이메일 또는 user_id)
        if metadata and 'email' in metadata:
            # 같은 이메일의 미사용 토큰 삭제
            existing_tokens = Token.query.filter_by(
                token_type=token_type,
                used=False
            ).all()
            for existing_token in existing_tokens:
                if existing_token.token_metadata:
                    try:
                        existing_metadata = Token._decrypt_metadata(existing_token.token_metadata)
                        if existing_metadata and existing_metadata.get('email') == metadata.get('email'):
                            db.session.delete(existing_token)
                    except:
                        pass
        elif user_id:
            Token.query.filter_by(
                user_id=user_id,
                token_type=token_type,
                used=False
            ).delete()
        
        # 새 토큰 생성
        token_plaintext = Token.generate_token()
        token_hash = Token.hash_token(token_plaintext)
        
        # metadata 암호화 (보안)
        encrypted_metadata = None
        if metadata:
            encrypted_metadata = Token._encrypt_metadata(metadata)
        
        token = Token(
            user_id=user_id,
            token_hash=token_hash,
            token_type=token_type,
            token_metadata=encrypted_metadata,
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

