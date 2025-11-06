"""
인증번호 생성 및 검증 서비스
보안: 인증번호는 메모리/Redis에 저장, 만료 시간 관리
"""
import secrets
from datetime import datetime, timedelta
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Redis 클라이언트 (선택사항)
redis_client = None

# 메모리 기반 저장소 (Redis 미사용 시)
verification_codes: dict[str, dict] = {}


async def init_redis():
    """Redis 클라이언트 초기화"""
    global redis_client
    if settings.USE_REDIS:
        try:
            import redis.asyncio as redis  # noqa: F401
            redis_client = await redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            # 연결 테스트
            await redis_client.ping()
            logger.info("Redis 연결 성공")
        except ImportError:
            logger.warning("Redis 패키지가 설치되지 않았습니다. 메모리 저장소를 사용합니다.")
            redis_client = None
            settings.USE_REDIS = False
        except Exception as e:
            logger.warning(f"Redis 연결 실패, 메모리 저장소 사용: {e}")
            redis_client = None
            settings.USE_REDIS = False
    else:
        logger.info("Redis 미사용, 메모리 저장소 사용")


async def close_redis():
    """Redis 클라이언트 종료"""
    global redis_client
    if redis_client:
        try:
            await redis_client.close()
            logger.info("Redis 연결 종료")
        except Exception as e:
            logger.error(f"Redis 연결 종료 실패: {e}")


class VerificationService:
    """인증번호 생성 및 검증 서비스"""

    @staticmethod
    async def generate_code(email: str) -> str:
        """
        6자리 인증번호 생성 및 저장
        보안: 예측 불가능한 난수 생성 (secrets 모듈 사용)

        Args:
            email: 사용자 이메일 주소

        Returns:
            str: 6자리 인증번호
        """
        # 6자리 숫자 인증번호 생성 (0-9)
        code = ''.join([str(secrets.randbelow(10)) for _ in range(settings.VERIFICATION_CODE_LENGTH)])

        # 만료 시간 계산
        expiry_time = datetime.now() + timedelta(minutes=settings.VERIFICATION_CODE_EXPIRY_MINUTES)

        # 저장소에 저장
        if redis_client:
            # Redis에 저장 (키: email, 값: code, 만료 시간: 5분)
            await redis_client.setex(
                f"verification:{email}",
                settings.VERIFICATION_CODE_EXPIRY_MINUTES * 60,  # 초 단위
                code
            )
            logger.info(f"인증번호 생성 및 Redis 저장: {email}")
        else:
            # 메모리에 저장
            verification_codes[email] = {
                "code": code,
                "expiry_time": expiry_time
            }
            logger.info(f"인증번호 생성 및 메모리 저장: {email}")

        # 보안: 로그에 인증번호는 기록하지 않음
        return code

    @staticmethod
    async def verify_code(email: str, code: str) -> bool:
        """
        인증번호 검증
        보안: 검증 실패 횟수 제한 고려 (현재는 구현하지 않음)

        Args:
            email: 사용자 이메일 주소
            code: 입력한 인증번호

        Returns:
            bool: 검증 성공 여부
        """
        try:
            stored_code = None

            if redis_client:
                # Redis에서 조회
                stored_code = await redis_client.get(f"verification:{email}")
                if stored_code:
                    # 검증 성공 시 삭제 (일회용)
                    await redis_client.delete(f"verification:{email}")
            else:
                # 메모리에서 조회
                if email in verification_codes:
                    code_data = verification_codes[email]
                    # 만료 시간 확인
                    if datetime.now() < code_data["expiry_time"]:
                        stored_code = code_data["code"]
                        # 검증 성공 시 삭제 (일회용)
                        del verification_codes[email]
                    else:
                        # 만료된 코드 삭제
                        del verification_codes[email]
                        logger.warning(f"만료된 인증번호 검증 시도: {email}")
                        return False

            if not stored_code:
                logger.warning(f"인증번호 없음 또는 만료: {email}")
                return False

            # 안전한 문자열 비교 (타이밍 공격 방지)
            if secrets.compare_digest(stored_code, code):
                logger.info(f"인증번호 검증 성공: {email}")
                return True
            else:
                logger.warning(f"인증번호 불일치: {email}")
                return False

        except Exception as e:
            logger.error(f"인증번호 검증 오류: {e}")
            return False

    @staticmethod
    async def delete_code(email: str):
        """
        인증번호 삭제 (사용하지 않음)

        Args:
            email: 사용자 이메일 주소
        """
        if redis_client:
            await redis_client.delete(f"verification:{email}")
        else:
            if email in verification_codes:
                del verification_codes[email]
