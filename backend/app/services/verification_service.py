"""
인증 코드 생성 및 검증 서비스
보안: 예측 불가능한 난수 생성, 만료 시간 설정
"""
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from app.models.token import Token
from app.extensions.database import db

logger = logging.getLogger(__name__)

# 인증 코드 저장소 (메모리, key: email, value: {code, token_id, expires_at})
# 프로덕션에서는 Redis 사용 권장
_verification_codes: Dict[str, Dict] = {}


class VerificationService:
    """인증 코드 생성 및 검증 서비스"""
    
    CODE_LENGTH = 6  # 6자리 숫자 코드
    CODE_EXPIRY_MINUTES = 10  # 10분 만료
    
    @staticmethod
    def generate_code(email: str, token_id: int) -> str:
        """
        6자리 숫자 인증 코드 생성 및 저장
        
        Args:
            email: 사용자 이메일 주소
            token_id: 연결된 토큰 ID
        
        Returns:
            str: 6자리 인증 코드
        """
        # 6자리 숫자 코드 생성 (0-9)
        code = ''.join([str(secrets.randbelow(10)) for _ in range(VerificationService.CODE_LENGTH)])
        
        # 만료 시간 계산
        expires_at = datetime.utcnow() + timedelta(minutes=VerificationService.CODE_EXPIRY_MINUTES)
        
        # 메모리에 저장 (key: email, value: {code, token_id, expires_at})
        _verification_codes[email] = {
            'code': code,
            'token_id': token_id,
            'expires_at': expires_at
        }
        
        logger.info(f"인증 코드 생성: email={email[:3]}..., token_id={token_id}, 만료={expires_at}")
        
        return code
    
    @staticmethod
    def verify_code(email: str, code: str) -> Optional[int]:
        """
        인증 코드 검증
        
        Args:
            email: 사용자 이메일 주소
            code: 입력한 인증 코드
        
        Returns:
            Optional[int]: 검증 성공 시 연결된 token_id, 실패 시 None
        """
        if email not in _verification_codes:
            logger.warning(f"인증 코드 없음: email={email[:3]}...")
            return None
        
        code_data = _verification_codes[email]
        
        # 만료 확인
        if datetime.utcnow() > code_data['expires_at']:
            del _verification_codes[email]
            logger.warning(f"만료된 인증 코드: email={email[:3]}...")
            return None
        
        # 안전한 문자열 비교 (타이밍 공격 방지)
        if secrets.compare_digest(code_data['code'], code):
            token_id = code_data['token_id']
            # 검증 성공 시 메모리에서 삭제 (일회용)
            del _verification_codes[email]
            logger.info(f"인증 코드 검증 성공: email={email[:3]}..., token_id={token_id}")
            return token_id
        else:
            logger.warning(f"인증 코드 불일치: email={email[:3]}...")
            return None
    
    @staticmethod
    def cleanup_expired_codes():
        """만료된 인증 코드 정리"""
        now = datetime.utcnow()
        expired_emails = [
            email for email, data in _verification_codes.items()
            if now > data['expires_at']
        ]
        
        for email in expired_emails:
            del _verification_codes[email]
        
        if expired_emails:
            logger.info(f"만료된 인증 코드 {len(expired_emails)}개 정리 완료")
        
        return len(expired_emails)

