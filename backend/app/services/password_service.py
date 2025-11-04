"""
비밀번호 해싱 서비스
- Argon2id 사용 (권장)
- PBKDF2 대체 옵션 제공
- Pepper는 환경 변수 또는 KMS에서 관리
"""

import os
import hashlib
import secrets
import logging
from typing import Tuple, Optional

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError, HashingError
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False
    logging.warning("argon2-cffi가 설치되지 않았습니다. PBKDF2를 사용합니다.")

logger = logging.getLogger(__name__)


class PasswordService:
    """
    비밀번호 해싱 및 검증 서비스
    - Argon2id 권장 (메모리 하드 함수)
    - PBKDF2 대체 옵션
    """
    
    def __init__(self):
        # Argon2id 설정 (OWASP 권장)
        if ARGON2_AVAILABLE:
            # 시간 비용: 2, 메모리 비용: 65536 (64MB), 병렬도: 4
            self.argon2_hasher = PasswordHasher(
                time_cost=2,           # 반복 횟수
                memory_cost=65536,     # 메모리 사용량 (KB)
                parallelism=4,        # 병렬 스레드 수
                hash_len=32,          # 해시 길이
                salt_len=16           # Salt 길이
            )
        else:
            self.argon2_hasher = None
        
        # PBKDF2 설정 (대체 옵션)
        self.pbkdf2_iterations = 600000  # OWASP 권장: 최소 600,000회
        
        # Pepper (KMS 또는 환경 변수에서 로드)
        self.pepper = self._load_pepper()
        
        logger.info(f"비밀번호 서비스 초기화 완료 (Argon2id: {ARGON2_AVAILABLE})")
    
    def _load_pepper(self) -> Optional[bytes]:
        """
        Pepper 로드
        - 프로덕션: KMS 또는 HashiCorp Vault에서 로드 권장
        - 개발: 환경 변수에서 로드
        """
        pepper_str = os.getenv('PASSWORD_PEPPER')
        if pepper_str:
            # 환경 변수에서 로드 (개발 환경)
            return pepper_str.encode('utf-8')
        else:
            # 프로덕션에서는 KMS를 통해 로드해야 함
            logger.warning("Pepper가 설정되지 않았습니다. KMS 또는 환경 변수에서 설정하세요.")
            return None
    
    def hash_password(self, password: str, use_argon2: bool = True) -> Tuple[str, str]:
        """
        비밀번호 해싱
        
        Args:
            password: 원본 비밀번호
            use_argon2: Argon2id 사용 여부 (False면 PBKDF2 사용)
        
        Returns:
            (password_hash, salt): 해시된 비밀번호와 salt
        """
        if not password:
            raise ValueError("비밀번호가 제공되지 않았습니다")
        
        # Pepper 적용
        if self.pepper:
            password = self._apply_pepper(password)
        
        if use_argon2 and ARGON2_AVAILABLE:
            try:
                # Argon2id는 자체 salt 포함
                password_hash = self.argon2_hasher.hash(password)
                # Argon2 해시에는 salt가 포함되어 있으므로 별도 salt 불필요
                # 하지만 호환성을 위해 빈 문자열 반환
                return password_hash, ""
            except HashingError as e:
                logger.error(f"Argon2 해싱 실패: {e}")
                raise ValueError("비밀번호 해싱 중 오류가 발생했습니다")
        else:
            # PBKDF2 사용
            salt = secrets.token_bytes(32)  # 32바이트 salt
            password_hash = self._hash_pbkdf2(password, salt)
            return password_hash, salt.hex()
    
    def verify_password(self, password: str, password_hash: str, salt: str = "") -> bool:
        """
        비밀번호 검증
        
        Args:
            password: 검증할 비밀번호
            password_hash: 저장된 해시
            salt: PBKDF2용 salt (Argon2는 불필요)
        
        Returns:
            검증 성공 여부
        """
        if not password or not password_hash:
            return False
        
        # Pepper 적용
        if self.pepper:
            password = self._apply_pepper(password)
        
        try:
            # Argon2id 해시 확인 (형식: $argon2id$...)
            if password_hash.startswith('$argon2id$'):
                if not ARGON2_AVAILABLE:
                    logger.error("Argon2id 해시가 있지만 라이브러리가 설치되지 않았습니다")
                    return False
                try:
                    self.argon2_hasher.verify(password_hash, password)
                    return True
                except VerifyMismatchError:
                    return False
            else:
                # PBKDF2 해시 검증
                if not salt:
                    logger.warning("PBKDF2 해시인데 salt가 제공되지 않았습니다")
                    return False
                
                salt_bytes = bytes.fromhex(salt)
                computed_hash = self._hash_pbkdf2(password, salt_bytes)
                return secrets.compare_digest(computed_hash, password_hash)
        
        except Exception as e:
            logger.error(f"비밀번호 검증 중 오류: {e}")
            return False
    
    def _hash_pbkdf2(self, password: str, salt: bytes) -> str:
        """PBKDF2 해싱"""
        password_bytes = password.encode('utf-8')
        hash_bytes = hashlib.pbkdf2_hmac(
            'sha256',
            password_bytes,
            salt,
            self.pbkdf2_iterations
        )
        return hash_bytes.hex()
    
    def _apply_pepper(self, password: str) -> str:
        """Pepper 적용 (HMAC-SHA256)"""
        if not self.pepper:
            return password
        
        password_bytes = password.encode('utf-8')
        hmac_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password_bytes,
            self.pepper,
            100000  # Pepper 적용용 반복 횟수
        )
        return hmac_hash.hex()
    
    def needs_rehash(self, password_hash: str) -> bool:
        """
        비밀번호 재해싱 필요 여부 확인
        (Argon2 파라미터 변경 시 사용)
        """
        if not ARGON2_AVAILABLE:
            return False
        
        try:
            return self.argon2_hasher.check_needs_rehash(password_hash)
        except Exception:
            return False


# 싱글톤 인스턴스
password_service = PasswordService()

