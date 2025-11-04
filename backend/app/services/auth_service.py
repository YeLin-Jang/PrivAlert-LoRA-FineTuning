"""
인증 서비스
- 회원가입, 로그인, 로그아웃 처리
- 계정 잠금, 실패 시도 추적
- 세션 관리
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import request
from app.extensions.database import get_db
from app.models.user import User, Role
from app.models.audit_log import AuditLog, AuditAction
from app.services.password_service import password_service
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)

# 보안 설정
MAX_LOGIN_ATTEMPTS = 5  # 최대 로그인 시도 횟수
LOCKOUT_DURATION = timedelta(minutes=30)  # 계정 잠금 지속 시간


class AuthService:
    """인증 서비스"""
    
    def __init__(self):
        self.password_service = password_service
        self.audit_service = audit_service
    
    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        사용자 회원가입
        
        Args:
            username: 사용자명
            email: 이메일
            password: 비밀번호
            full_name: 전체 이름 (선택)
            ip_address: IP 주소
        
        Returns:
            회원가입 결과
        """
        db = get_db()
        
        try:
            # 입력 검증
            validation_error = self._validate_registration(username, email, password)
            if validation_error:
                return {
                    'success': False,
                    'error': validation_error
                }
            
            # 중복 확인
            if db.query(User).filter_by(username=username).first():
                return {
                    'success': False,
                    'error': '이미 사용 중인 사용자명입니다'
                }
            
            if db.query(User).filter_by(email=email).first():
                return {
                    'success': False,
                    'error': '이미 사용 중인 이메일입니다'
                }
            
            # 비밀번호 해싱
            password_hash, salt = self.password_service.hash_password(password)
            
            # 사용자 생성
            user = User(
                username=username,
                email=email,
                password_hash=password_hash,
                salt=salt,
                full_name=full_name,
                is_active=True,
                is_verified=False,  # 이메일 인증 필요
                is_locked=False,
                failed_login_attempts=0
            )
            
            # 기본 역할 할당 (일반 사용자)
            default_role = db.query(Role).filter_by(name='user').first()
            if default_role:
                user.roles.append(default_role)
            
            db.add(user)
            db.commit()
            
            # 감사 로그 기록
            self.audit_service.log_action(
                user_id=user.id,
                action=AuditAction.REGISTER,
                ip_address=ip_address,
                success=True,
                message=f"사용자 회원가입: {username}"
            )
            
            logger.info(f"사용자 회원가입 성공: {username}")
            
            return {
                'success': True,
                'message': '회원가입이 완료되었습니다',
                'user': user.to_dict()
            }
        
        except Exception as e:
            db.rollback()
            logger.error(f"회원가입 실패: {e}")
            return {
                'success': False,
                'error': '회원가입 중 오류가 발생했습니다'
            }
    
    def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        사용자 인증 (로그인)
        
        Args:
            username: 사용자명 또는 이메일
            password: 비밀번호
            ip_address: IP 주소
            user_agent: User-Agent
        
        Returns:
            인증 결과
        """
        db = get_db()
        
        try:
            # 사용자 조회 (사용자명 또는 이메일)
            user = db.query(User).filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if not user:
                # 사용자가 없어도 실패 시도로 기록하지 않음 (정보 노출 방지)
                self.audit_service.log_action(
                    user_id=None,
                    action=AuditAction.LOGIN_FAILED,
                    ip_address=ip_address,
                    success=False,
                    message="존재하지 않는 사용자"
                )
                return {
                    'success': False,
                    'error': '사용자명 또는 비밀번호가 올바르지 않습니다'
                }
            
            # 계정 잠금 확인
            if user.is_locked:
                # 잠금 해제 시간 확인
                if user.updated_at and (datetime.utcnow() - user.updated_at) < LOCKOUT_DURATION:
                    self.audit_service.log_action(
                        user_id=user.id,
                        action=AuditAction.LOGIN_FAILED,
                        ip_address=ip_address,
                        success=False,
                        message="잠금된 계정 로그인 시도"
                    )
                    return {
                        'success': False,
                        'error': '계정이 잠금되었습니다. 잠시 후 다시 시도해주세요'
                    }
                else:
                    # 잠금 해제
                    user.is_locked = False
                    user.failed_login_attempts = 0
            
            # 비밀번호 검증
            if not self.password_service.verify_password(password, user.password_hash, user.salt):
                # 실패 시도 증가
                user.failed_login_attempts += 1
                
                # 최대 시도 횟수 초과 시 계정 잠금
                if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                    user.is_locked = True
                    user.failed_login_attempts = 0
                    db.commit()
                    
                    self.audit_service.log_action(
                        user_id=user.id,
                        action=AuditAction.USER_LOCK,
                        ip_address=ip_address,
                        success=True,
                        message=f"로그인 실패로 인한 계정 잠금 ({MAX_LOGIN_ATTEMPTS}회 실패)"
                    )
                    
                    return {
                        'success': False,
                        'error': f'로그인 실패가 {MAX_LOGIN_ATTEMPTS}회 누적되어 계정이 잠금되었습니다'
                    }
                
                db.commit()
                
                self.audit_service.log_action(
                    user_id=user.id,
                    action=AuditAction.LOGIN_FAILED,
                    ip_address=ip_address,
                    success=False,
                    message=f"비밀번호 오류 (시도: {user.failed_login_attempts}/{MAX_LOGIN_ATTEMPTS})"
                )
                
                return {
                    'success': False,
                    'error': '사용자명 또는 비밀번호가 올바르지 않습니다'
                }
            
            # 활성 상태 확인
            if not user.is_active:
                self.audit_service.log_action(
                    user_id=user.id,
                    action=AuditAction.LOGIN_FAILED,
                    ip_address=ip_address,
                    success=False,
                    message="비활성 계정 로그인 시도"
                )
                return {
                    'success': False,
                    'error': '비활성화된 계정입니다'
                }
            
            # 로그인 성공
            user.failed_login_attempts = 0
            user.last_login_at = datetime.utcnow()
            user.last_login_ip = ip_address
            user.is_locked = False
            
            db.commit()
            
            # 감사 로그 기록
            self.audit_service.log_action(
                user_id=user.id,
                action=AuditAction.LOGIN,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
                message=f"로그인 성공: {user.username}"
            )
            
            logger.info(f"로그인 성공: {user.username} from {ip_address}")
            
            return {
                'success': True,
                'message': '로그인 성공',
                'user': user.to_dict()
            }
        
        except Exception as e:
            db.rollback()
            logger.error(f"인증 실패: {e}")
            return {
                'success': False,
                'error': '로그인 중 오류가 발생했습니다'
            }
    
    def _validate_registration(self, username: str, email: str, password: str) -> Optional[str]:
        """회원가입 입력 검증"""
        # 사용자명 검증
        if not username or len(username) < 3:
            return '사용자명은 최소 3자 이상이어야 합니다'
        if len(username) > 50:
            return '사용자명은 최대 50자까지 가능합니다'
        if not username.isalnum() and '_' not in username:
            return '사용자명은 영문, 숫자, 언더스코어만 사용할 수 있습니다'
        
        # 이메일 검증
        if not email or '@' not in email:
            return '유효한 이메일 주소를 입력하세요'
        if len(email) > 255:
            return '이메일은 최대 255자까지 가능합니다'
        
        # 비밀번호 검증
        if not password or len(password) < 8:
            return '비밀번호는 최소 8자 이상이어야 합니다'
        if len(password) > 128:
            return '비밀번호는 최대 128자까지 가능합니다'
        
        # 비밀번호 복잡도 (선택적)
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return '비밀번호는 대문자, 소문자, 숫자를 포함해야 합니다'
        
        return None


# 싱글톤 인스턴스
auth_service = AuthService()

