"""사용자 프로필 관련 라우트"""
from flask import Blueprint, request
from app.utils.logger import get_logger
from app.models.user import User
from app.models.token import Token
from app.models.audit_log import AuditLog
from app.models.session import UserSession
from app.extensions.database import db
from app.utils.auth_utils import (
    validate_email, validate_password_strength, get_client_ip, get_user_agent
)
from app.utils.decorators import login_required
from app.utils.api_utils import APIResponse
from app.utils.user_route_helpers import (
    validate_csrf_from_request, check_user_active, get_session_id, validate_json_request
)
from app.utils.csrf_protection import generate_csrf_token
import os

logger = get_logger(__name__)

user_profile_bp = Blueprint('user_profile', __name__)


@user_profile_bp.route('/me', methods=['GET'])
@login_required
def get_profile():
    """현재 사용자 정보 조회"""
    try:
        user = request.current_user
        
        # 세션 ID 가져오기 (CSRF 토큰 생성에 사용)
        has_session, session_id, error = get_session_id()
        if not has_session:
            return error
        
        # CSRF 토큰 생성 (세션 ID 사용)
        csrf_token = generate_csrf_token(session_id)
        
        return APIResponse.success(
            data={
                **user.to_dict(),
                "csrf_token": csrf_token
            }
        )
    except Exception as e:
        logger.error(f"프로필 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("프로필 조회 중 오류가 발생했습니다")


@user_profile_bp.route('/me', methods=['PATCH'])
@login_required
def update_profile():
    """프로필 수정"""
    try:
        # CSRF 검증
        is_valid, error = validate_csrf_from_request()
        if not is_valid:
            return error
        
        user = request.current_user
        
        # JSON 요청 검증
        is_valid, data, error = validate_json_request()
        if not is_valid:
            return error
        
        new_email = data.get('email', '').strip().lower()
        
        # 이메일 변경 시
        if new_email and new_email != user.email:
            # 이메일 형식 검증
            if not validate_email(new_email):
                return APIResponse.error("올바른 이메일 형식이 아닙니다", code=400)
            
            # 중복 확인
            if User.find_by_email(new_email):
                return APIResponse.error("이미 사용 중인 이메일입니다", code=409)
            
            # 이메일 변경 및 재검증 필요
            user.email = new_email
            user.email_verified = False
            user.email_verified_at = None
            
            # 새 이메일 검증 토큰 생성
            token_plaintext, token = Token.create_token(
                user_id=user.id,
                token_type='email_verification',
                expiry_hours=24
            )
            
            # 이메일 변경 인증 메일 전송
            verification_url = f"{request.host_url.rstrip('/')}/api/v1/auth/verify?token={token_plaintext}"
            try:
                from app.services.email_service import EmailService
                email_sent = EmailService.send_verification_email(new_email, token_plaintext, verification_url)
                if email_sent:
                    logger.info(f"이메일 변경 인증 메일 전송 성공: {new_email}")
                else:
                    logger.warning(f"이메일 변경 인증 메일 전송 실패: {new_email}")
            except Exception as e:
                logger.error(f"이메일 변경 인증 메일 전송 중 오류: {e}", exc_info=True)
            
            db.session.commit()
            
            logger.info(f"이메일 변경: {user.email}")
            
            # 감사 로그
            AuditLog.log_event(
                user_id=user.id,
                event_type='email_changed',
                event_description='이메일 주소 변경',
                ip_address=get_client_ip(),
                user_agent=get_user_agent(),
                success=True
            )
            
            return APIResponse.success(
                message="이메일이 변경되었습니다. 새 이메일을 확인하여 계정을 활성화하세요",
                data={
                    "user": user.to_dict(),
                    "verification_token": token_plaintext if os.getenv("FLASK_ENV") == "development" else None
                }
            )
        
        # 프로필 업데이트 없음
        return APIResponse.success(
            message="변경사항이 없습니다",
            data=user.to_dict()
        )
        
    except Exception as e:
        logger.error(f"프로필 수정 오류: {e}", exc_info=True)
        return APIResponse.server_error("프로필 수정 중 오류가 발생했습니다")


@user_profile_bp.route('/password-change', methods=['POST'])
@login_required
def change_password():
    """비밀번호 변경 (현재 비밀번호 확인 필요)"""
    try:
        # CSRF 검증
        is_valid, error = validate_csrf_from_request()
        if not is_valid:
            return error
        
        user = request.current_user
        
        # JSON 요청 검증
        is_valid, data, error = validate_json_request()
        if not is_valid:
            return error
        
        current_password = data.get('currentPassword', '')
        new_password = data.get('newPassword', '')
        
        if not current_password or not new_password:
            return APIResponse.error("현재 비밀번호와 새 비밀번호를 입력하세요", code=400)
        
        # 현재 비밀번호 확인
        if not user.check_password(current_password):
            ip = get_client_ip()
            logger.warning(f"비밀번호 변경 실패 (현재 비밀번호 불일치): user_id={user.id}, ip={ip}")
            return APIResponse.unauthorized("현재 비밀번호가 올바르지 않습니다")
        
        # 새 비밀번호 강도 검증
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return APIResponse.error(error_msg, code=400)
        
        # 새 비밀번호가 현재 비밀번호와 같은지 확인
        if current_password == new_password:
            return APIResponse.error("새 비밀번호는 현재 비밀번호와 달라야 합니다", code=400)
        
        # 비밀번호 변경
        user.set_password(new_password)
        
        # 모든 세션 무효화 (보안)
        session_id = request.cookies.get('session_id')
        UserSession.revoke_all_user_sessions(user.id, except_session_id=session_id)
        
        db.session.commit()
        
        ip = get_client_ip()
        logger.info(f"비밀번호 변경 성공: user_id={user.id}, email={user.email[:3] if user.email else 'unknown'}..., ip={ip}")
        
        # 감사 로그
        AuditLog.log_password_change(
            user_id=user.id,
            ip_address=ip,
            user_agent=get_user_agent()
        )
        
        return APIResponse.success(message="비밀번호가 성공적으로 변경되었습니다")
        
    except ValueError as e:
        logger.warning(f"비밀번호 변경 실패: {e}")
        return APIResponse.error(str(e), code=400)
    except Exception as e:
        logger.error(f"비밀번호 변경 오류: {e}", exc_info=True)
        return APIResponse.server_error("비밀번호 변경 중 오류가 발생했습니다")


@user_profile_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """계정 삭제 요청 (7일 유예)"""
    try:
        # CSRF 검증
        is_valid, error = validate_csrf_from_request()
        if not is_valid:
            return error
        
        user = request.current_user
        
        # JSON 요청 검증
        is_valid, data, error = validate_json_request()
        if not is_valid:
            return error
        
        password = data.get('password', '')
        
        # 비밀번호 확인
        if not user.check_password(password):
            return APIResponse.unauthorized("비밀번호가 올바르지 않습니다")
        
        # 계정 삭제 요청
        user.request_deletion()
        
        # 감사 로그
        ip = get_client_ip()
        AuditLog.log_account_deletion(
            user_id=user.id,
            ip_address=ip,
            user_agent=get_user_agent()
        )
        logger.warning(f"계정 삭제 요청: user_id={user.id}, email={user.email[:3] if user.email else 'unknown'}..., ip={ip}")
        
        return APIResponse.success(
            message="계정 삭제가 요청되었습니다. 7일 후 계정이 영구적으로 삭제됩니다"
        )
        
    except Exception as e:
        logger.error(f"계정 삭제 요청 오류: {e}", exc_info=True)
        return APIResponse.server_error("계정 삭제 요청 중 오류가 발생했습니다")

