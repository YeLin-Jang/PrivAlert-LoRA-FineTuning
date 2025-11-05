"""
일반 사용자 모델 (HTTP 전용 환경)
보안: Argon2id 비밀번호 해싱, MFA 지원, 세션 추적
"""
from datetime import datetime, timedelta
from app.extensions.database import db
from typing import Optional
import secrets
import hashlib
import pyotp
import qrcode
import io
import base64

# Argon2id는 requirements.txt에 추가 필요
try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    # Fallback to werkzeug (bcrypt) if argon2 not available
    from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    """
    일반 사용자 모델
    보안: 
    - 비밀번호는 Argon2id 해시로 저장 (HTTP 환경이므로 추가 보안 조치)
    - MFA 지원 (TOTP)
    - 세션 추적 및 관리
    - 이메일 검증 필수
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # 이메일 검증
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verified_at = db.Column(db.DateTime, nullable=True)
    
    # MFA 설정
    mfa_enabled = db.Column(db.Boolean, default=False, nullable=False)
    mfa_secret = db.Column(db.String(255), nullable=True)  # 암호화된 TOTP 시크릿
    mfa_backup_codes_hash = db.Column(db.Text, nullable=True)  # 해시된 복구 코드들 (JSON 배열)
    
    # 계정 상태
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)
    deletion_requested_at = db.Column(db.DateTime, nullable=True)  # 계정 삭제 요청 시각 (7일 유예)
    
    # 로그인 실패 추적 (Rate limiting)
    login_failed_count = db.Column(db.Integer, default=0, nullable=False)
    login_locked_until = db.Column(db.DateTime, nullable=True)  # 일시 잠금 종료 시각
    
    # 계정 정보
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)  # IPv6 지원
    last_password_change = db.Column(db.DateTime, nullable=True)
    
    # 보안: 인덱스 추가
    __table_args__ = (
        db.Index('idx_email', 'email'),
        db.Index('idx_email_verified', 'email_verified'),
        db.Index('idx_is_active', 'is_active'),
        db.Index('idx_is_deleted', 'is_deleted'),
    )
    
    def set_password(self, password: str) -> None:
        """
        비밀번호 설정 (Argon2id 해시)
        보안: HTTP 환경에서 최대한 안전한 해싱 알고리즘 사용
        """
        if not password or len(password) < 12:
            raise ValueError("비밀번호는 최소 12자 이상이어야 합니다")
        
        if not any(c.isupper() for c in password):
            raise ValueError("비밀번호는 최소 1개의 대문자를 포함해야 합니다")
        if not any(c.islower() for c in password):
            raise ValueError("비밀번호는 최소 1개의 소문자를 포함해야 합니다")
        if not any(c.isdigit() for c in password):
            raise ValueError("비밀번호는 최소 1개의 숫자를 포함해야 합니다")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            raise ValueError("비밀번호는 최소 1개의 특수문자를 포함해야 합니다")
        
        if ARGON2_AVAILABLE:
            # Argon2id 사용 (권장 파라미터)
            # memory_cost=65536 (64MB), time_cost=3, parallelism=4
            ph = PasswordHasher(
                memory_cost=65536,  # 64MB
                time_cost=3,         # 3 iterations
                parallelism=4,      # 4 threads
                hash_len=32,        # 32 bytes
                salt_len=16          # 16 bytes salt
            )
            self.password_hash = ph.hash(password)
        else:
            # Fallback to werkzeug (bcrypt)
            self.password_hash = generate_password_hash(password, method='pbkdf2:sha256:600000')
        
        self.last_password_change = datetime.utcnow()
    
    def check_password(self, password: str) -> bool:
        """
        비밀번호 확인
        보안: 타임링 공격 방지를 위한 안전한 검증
        """
        if not self.password_hash:
            return False
        
        try:
            if ARGON2_AVAILABLE:
                ph = PasswordHasher()
                ph.verify(self.password_hash, password)
                # Argon2id는 해시 업그레이드 자동 처리 (더 강한 파라미터로 재해싱)
                if ph.check_needs_rehash(self.password_hash):
                    self.set_password(password)
                    db.session.commit()
                return True
            else:
                return check_password_hash(self.password_hash, password)
        except (VerifyMismatchError, ValueError):
            return False
        except Exception:
            # 기타 예외 (예: Fernet 복호화 실패 등)
            return False
    
    def generate_mfa_secret(self) -> str:
        """
        MFA TOTP 시크릿 생성
        보안: 서버에서 생성한 시크릿을 암호화하여 저장
        """
        # TOTP 시크릿 생성 (RFC 6238)
        secret = pyotp.random_base32()
        
        # 보안: 시크릿을 암호화하여 저장 (환경 변수 키 사용)
        # 실제로는 서버의 암호화 키로 암호화해야 하지만, 여기서는 해시로 저장
        # 프로덕션에서는 Fernet (symmetric encryption) 사용 권장
        import os
        from cryptography.fernet import Fernet
        
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if encryption_key:
            try:
                # Fernet 키로 암호화 (키는 bytes 또는 str 모두 가능)
                key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
                f = Fernet(key_bytes)
                self.mfa_secret = f.encrypt(secret.encode()).decode()
            except Exception as e:
                # Fallback: 해시로 저장 (복구 불가, 단지 검증용)
                logger.warning(f"MFA 시크릿 암호화 실패, 해시로 저장: {e}")
                self.mfa_secret = hashlib.sha256(secret.encode()).hexdigest()
        else:
            # 개발 환경: 해시로만 저장
            self.mfa_secret = hashlib.sha256(secret.encode()).hexdigest()
        
        return secret
    
    def get_mfa_secret(self) -> Optional[str]:
        """
        MFA 시크릿 복호화 (활성화 시에만)
        보안: 암호화된 시크릿을 복호화하여 반환
        """
        if not self.mfa_secret:
            return None
        
        # 암호화 키로 복호화 시도
        import os
        from cryptography.fernet import Fernet
        import logging
        logger = logging.getLogger(__name__)
        
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if encryption_key:
            try:
                key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
                f = Fernet(key_bytes)
                return f.decrypt(self.mfa_secret.encode()).decode()
            except Exception as e:
                # 해시로 저장된 경우 복구 불가
                logger.warning(f"MFA 시크릿 복호화 실패: {e}")
                return None
        return None
    
    def generate_mfa_qr_code(self, secret: str, issuer: str = "PrivAlert") -> str:
        """
        MFA QR 코드 생성 (Base64 인코딩된 이미지)
        """
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=self.email,
            issuer_name=issuer
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.read()).decode()
    
    def verify_totp(self, token: str) -> bool:
        """
        TOTP 토큰 검증
        """
        if not self.mfa_enabled or not self.mfa_secret:
            return False
        
        secret = self.get_mfa_secret()
        if not secret:
            return False
        
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # 1단계 허용 오차
    
    def generate_backup_codes(self, count: int = 10) -> list[str]:
        """
        MFA 복구 코드 생성 (해시하여 저장)
        보안: 복구 코드는 해시로 저장, 원문은 이메일 전송 후 폐기
        """
        codes = [secrets.token_urlsafe(16) for _ in range(count)]
        
        # 복구 코드 해시 저장
        import json
        code_hashes = [hashlib.sha256(code.encode()).hexdigest() for code in codes]
        self.mfa_backup_codes_hash = json.dumps(code_hashes)
        
        return codes
    
    def verify_backup_code(self, code: str) -> bool:
        """
        복구 코드 검증 (사용 후 삭제)
        """
        if not self.mfa_backup_codes_hash:
            return False
        
        import json
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        code_hashes = json.loads(self.mfa_backup_codes_hash)
        
        if code_hash in code_hashes:
            # 사용된 코드 제거
            code_hashes.remove(code_hash)
            self.mfa_backup_codes_hash = json.dumps(code_hashes) if code_hashes else None
            db.session.commit()
            return True
        return False
    
    def increment_login_failure(self):
        """
        로그인 실패 횟수 증가 (5회 실패 시 잠금)
        """
        self.login_failed_count += 1
        if self.login_failed_count >= 5:
            # 30분 잠금
            self.login_locked_until = datetime.utcnow() + timedelta(minutes=30)
        db.session.commit()
    
    def reset_login_failure(self):
        """
        로그인 성공 시 실패 횟수 초기화
        """
        self.login_failed_count = 0
        self.login_locked_until = None
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def is_locked(self) -> bool:
        """
        계정 잠금 상태 확인
        """
        if self.login_locked_until and self.login_locked_until > datetime.utcnow():
            return True
        if self.login_locked_until and self.login_locked_until <= datetime.utcnow():
            # 잠금 시간 경과 시 자동 해제
            self.login_locked_until = None
            self.login_failed_count = 0
            db.session.commit()
        return False
    
    def request_deletion(self):
        """
        계정 삭제 요청 (7일 유예)
        """
        self.is_deleted = False  # 아직 삭제되지 않음
        self.deletion_requested_at = datetime.utcnow()
        db.session.commit()
    
    def should_be_deleted(self) -> bool:
        """
        계정 삭제 시점 확인 (7일 경과)
        """
        if self.deletion_requested_at:
            return (datetime.utcnow() - self.deletion_requested_at) >= timedelta(days=7)
        return False
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        사용자 정보를 딕셔너리로 변환 (민감 정보 제외)
        보안: 비밀번호, MFA 시크릿 등은 절대 반환하지 않음
        """
        data = {
            'id': self.id,
            'email': self.email,
            'email_verified': self.email_verified,
            'email_verified_at': self.email_verified_at.isoformat() if self.email_verified_at else None,
            'mfa_enabled': self.mfa_enabled,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }
        
        if include_sensitive:
            # 관리자 전용 필드 (민감 정보)
            data.update({
                'login_failed_count': self.login_failed_count,
                'login_locked_until': self.login_locked_until.isoformat() if self.login_locked_until else None,
                'last_login_ip': self.last_login_ip,
                'last_password_change': self.last_password_change.isoformat() if self.last_password_change else None,
            })
        
        return data
    
    @staticmethod
    def find_by_email(email: str) -> Optional['User']:
        """
        이메일로 사용자 검색
        보안: SQLAlchemy ORM 사용으로 SQL 인젝션 방지
        """
        return User.query.filter_by(email=email.lower().strip(), is_deleted=False).first()
    
    @staticmethod
    def create_user(email: str, password: str) -> 'User':
        """
        새 사용자 생성
        """
        if User.find_by_email(email):
            raise ValueError("이미 등록된 이메일입니다")
        
        user = User(
            email=email.lower().strip(),
            email_verified=False,
            mfa_enabled=False,
            is_active=True,
            is_deleted=False
        )
        user.set_password(password)
        return user
    
    def __repr__(self):
        return f'<User {self.email}>'

