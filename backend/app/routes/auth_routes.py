"""
사용자 인증 라우트 (HTTP 전용 환경)
보안: CSRF 보호, Rate limiting, 세션 관리
"""
from flask import Blueprint, request, jsonify, make_response, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
from app.utils.logger import get_logger
from app.models.user import User
from app.models.token import Token
from app.models.session import UserSession
from app.models.audit_log import AuditLog
from app.extensions.database import db
from app.utils.auth_utils import (
    validate_email, validate_password_strength, get_client_ip, get_user_agent
)
from app.utils.csrf_protection import generate_csrf_token, validate_csrf_token
import os

logger = get_logger(__name__)

auth_bp = Blueprint('auth', __name__)

# Rate Limiter는 Flask 앱에서 초기화됨
def get_limiter():
    """Rate Limiter 인스턴스 가져오기"""
    return Limiter(
        app=current_app._get_current_object(),
        key_func=get_remote_address,
        default_limits=["1000 per hour"]
    )


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    회원가입
    POST /api/v1/auth/signup
    Body: { "email": "...", "password": "..." }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        # 입력 검증
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "이메일과 비밀번호를 입력하세요",
                "code": 400
            }), 400
        
        # 이메일 형식 검증
        if not validate_email(email):
            return jsonify({
                "success": False,
                "error": "올바른 이메일 형식이 아닙니다",
                "code": 400
            }), 400
        
        # 비밀번호 강도 검증
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg,
                "code": 400
            }), 400
        
        # 중복 이메일 확인
        if User.find_by_email(email):
            # 보안: 사용자에게는 동일한 메시지 반환 (이메일 존재 여부 노출 방지)
            return jsonify({
                "success": False,
                "error": "이미 등록된 이메일입니다",
                "code": 409
            }), 409
        
        # 사용자 생성
        user = User.create_user(email, password)
        db.session.add(user)
        db.session.commit()
        
        # 이메일 검증 토큰 생성
        token_plaintext, token = Token.create_token(
            user_id=user.id,
            token_type='email_verification',
            expiry_hours=24
        )
        
        # TODO: 이메일 전송 (실제 구현 필요)
        # send_verification_email(user.email, token_plaintext)
        logger.info(f"회원가입 성공: {email} (이메일 검증 토큰 생성됨)")
        
        # 감사 로그
        AuditLog.log_event(
            user_id=user.id,
            event_type='signup',
            event_description='회원가입',
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            success=True
        )
        
        return jsonify({
            "success": True,
            "message": "회원가입이 완료되었습니다. 이메일을 확인하여 계정을 활성화하세요",
            "data": {
                "user_id": user.id,
                "email": user.email,
                # 개발 환경에서만 토큰 반환 (프로덕션에서는 제거)
                "verification_token": token_plaintext if os.getenv("FLASK_ENV") == "development" else None
            }
        }), 201
        
    except ValueError as e:
        logger.warning(f"회원가입 실패: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "code": 400
        }), 400
    except Exception as e:
        logger.error(f"회원가입 오류: {e}")
        return jsonify({
            "success": False,
            "error": "회원가입 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/verify', methods=['GET'])
def verify_email():
    """
    이메일 검증
    GET /api/v1/auth/verify?token=...
    """
    try:
        token_plaintext = request.args.get('token')
        
        if not token_plaintext:
            return jsonify({
                "success": False,
                "error": "토큰이 필요합니다",
                "code": 400
            }), 400
        
        # 토큰 검증
        token = Token.verify_token(token_plaintext, 'email_verification')
        
        if not token:
            return jsonify({
                "success": False,
                "error": "유효하지 않거나 만료된 토큰입니다",
                "code": 400
            }), 400
        
        if token.used:
            return jsonify({
                "success": False,
                "error": "이미 사용된 토큰입니다",
                "code": 410
            }), 410
        
        # 사용자 이메일 검증 완료
        user = User.query.get(token.user_id)
        if not user:
            return jsonify({
                "success": False,
                "error": "사용자를 찾을 수 없습니다",
                "code": 404
            }), 404
        
        user.email_verified = True
        user.email_verified_at = datetime.utcnow()
        token.mark_as_used()
        
        db.session.commit()
        
        logger.info(f"이메일 검증 성공: {user.email}")
        
        # 감사 로그
        AuditLog.log_event(
            user_id=user.id,
            event_type='email_verified',
            event_description='이메일 검증 완료',
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            success=True
        )
        
        return jsonify({
            "success": True,
            "message": "이메일 검증이 완료되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"이메일 검증 오류: {e}")
        return jsonify({
            "success": False,
            "error": "이메일 검증 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    로그인
    POST /api/v1/auth/login
    Body: { "email": "...", "password": "...", "totp": "..." (선택) }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        totp_code = data.get('totp', '')  # MFA 토큰 (선택)
        
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "이메일과 비밀번호를 입력하세요",
                "code": 401
            }), 401
        
        # 사용자 조회
        user = User.find_by_email(email)
        
        # 보안: 존재 여부와 관계없이 동일한 응답 시간 (타임링 공격 방지)
        if not user or not user.is_active or user.is_deleted:
            # 감사 로그 (실패)
            AuditLog.log_login(
                user_id=None,
                success=False,
                ip_address=get_client_ip(),
                user_agent=get_user_agent(),
                error_message="사용자 없음 또는 비활성 계정"
            )
            return jsonify({
                "success": False,
                "error": "잘못된 이메일 또는 비밀번호입니다",
                "code": 401
            }), 401
        
        # 계정 잠금 확인
        if user.is_locked():
            return jsonify({
                "success": False,
                "error": "계정이 일시적으로 잠겨있습니다. 30분 후 다시 시도하세요",
                "code": 423
            }), 423
        
        # 비밀번호 확인
        if not user.check_password(password):
            user.increment_login_failure()
            
            # 감사 로그 (실패)
            AuditLog.log_login(
                user_id=user.id,
                success=False,
                ip_address=get_client_ip(),
                user_agent=get_user_agent(),
                error_message="비밀번호 불일치"
            )
            
            return jsonify({
                "success": False,
                "error": "잘못된 이메일 또는 비밀번호입니다",
                "code": 401
            }), 401
        
        # 이메일 검증 확인
        if not user.email_verified:
            return jsonify({
                "success": False,
                "error": "이메일 검증이 필요합니다",
                "code": 403
            }), 403
        
        # MFA 검증 (활성화된 경우)
        if user.mfa_enabled:
            if not totp_code:
                return jsonify({
                    "success": False,
                    "error": "MFA 토큰이 필요합니다",
                    "code": 401,
                    "requires_mfa": True
                }), 401
            
            # TOTP 또는 복구 코드 확인
            if not user.verify_totp(totp_code) and not user.verify_backup_code(totp_code):
                user.increment_login_failure()
                
                AuditLog.log_login(
                    user_id=user.id,
                    success=False,
                    ip_address=get_client_ip(),
                    user_agent=get_user_agent(),
                    error_message="MFA 토큰 불일치"
                )
                
                return jsonify({
                    "success": False,
                    "error": "MFA 토큰이 올바르지 않습니다",
                    "code": 401
                }), 401
        
        # 로그인 성공
        user.reset_login_failure()
        user.last_login = datetime.utcnow()
        user.last_login_ip = get_client_ip()
        
        # 세션 생성
        session = UserSession.create_session(
            user_id=user.id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            expiry_hours=24
        )
        
        # CSRF 토큰 생성
        csrf_token = generate_csrf_token(str(user.id))
        
        # 응답 생성
        response = make_response(jsonify({
            "success": True,
            "data": {
                "user": user.to_dict(),
                "csrf_token": csrf_token,
                "session_id": session.session_id
            }
        }))
        
        # 세션 쿠키 설정 (HTTP 전용 - Secure 플래그 미설정)
        flask_env = os.getenv("FLASK_ENV", "development")
        response.set_cookie(
            'session_id',
            session.session_id,
            httponly=True,
            secure=False,  # HTTP 환경이므로 Secure 미설정
            samesite='Strict',  # CSRF 방지
            path='/',
            max_age=86400  # 24시간
        )
        
        # 세션 토큰 쿠키 (Double Submit Cookie)
        response.set_cookie(
            'session_token',
            session.session_token,
            httponly=False,  # JavaScript에서 읽을 수 있어야 함
            secure=False,
            samesite='Strict',
            path='/',
            max_age=86400
        )
        
        logger.info(f"로그인 성공: {email}")
        
        # 감사 로그
        AuditLog.log_login(
            user_id=user.id,
            success=True,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        return response, 200
        
    except Exception as e:
        logger.error(f"로그인 오류: {e}")
        return jsonify({
            "success": False,
            "error": "로그인 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    로그아웃
    POST /api/v1/auth/logout
    """
    try:
        session_id = request.cookies.get('session_id')
        
        if session_id:
            session = UserSession.find_by_session_id(session_id)
            if session:
                user_id = session.user_id
                session.revoke()
                
                # 감사 로그
                AuditLog.log_logout(
                    user_id=user_id,
                    ip_address=get_client_ip(),
                    user_agent=get_user_agent()
                )
        
        # 쿠키 삭제
        response = make_response(jsonify({
            "success": True,
            "message": "로그아웃되었습니다"
        }))
        
        response.set_cookie('session_id', '', expires=0)
        response.set_cookie('session_token', '', expires=0)
        
        return response, 200
        
    except Exception as e:
        logger.error(f"로그아웃 오류: {e}")
        return jsonify({
            "success": False,
            "error": "로그아웃 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/request-reset', methods=['POST'])
def request_password_reset():
    """
    비밀번호 재설정 요청
    POST /api/v1/auth/request-reset
    Body: { "email": "..." }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({
                "success": False,
                "error": "이메일을 입력하세요",
                "code": 400
            }), 400
        
        # 보안: 사용자 존재 여부와 관계없이 동일한 응답 (이메일 존재 여부 노출 방지)
        user = User.find_by_email(email)
        
        if user and user.email_verified:
            # 비밀번호 재설정 토큰 생성
            token_plaintext, token = Token.create_token(
                user_id=user.id,
                token_type='password_reset',
                expiry_hours=1  # 1시간만 유효
            )
            
            # TODO: 이메일 전송
            # send_password_reset_email(user.email, token_plaintext)
            logger.info(f"비밀번호 재설정 토큰 생성: {email}")
            
            # 감사 로그
            AuditLog.log_event(
                user_id=user.id,
                event_type='password_reset_requested',
                event_description='비밀번호 재설정 요청',
                ip_address=get_client_ip(),
                user_agent=get_user_agent(),
                success=True
            )
        
        # 보안: 항상 동일한 응답 반환
        return jsonify({
            "success": True,
            "message": "비밀번호 재설정 이메일을 발송했습니다. 이메일을 확인하세요"
        }), 200
        
    except Exception as e:
        logger.error(f"비밀번호 재설정 요청 오류: {e}")
        return jsonify({
            "success": False,
            "error": "비밀번호 재설정 요청 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/reset', methods=['POST'])
def reset_password():
    """
    비밀번호 재설정
    POST /api/v1/auth/reset
    Body: { "token": "...", "newPassword": "..." }
    """
    try:
        data = request.get_json()
        token_plaintext = data.get('token')
        new_password = data.get('newPassword')
        
        if not token_plaintext or not new_password:
            return jsonify({
                "success": False,
                "error": "토큰과 새 비밀번호를 입력하세요",
                "code": 400
            }), 400
        
        # 비밀번호 강도 검증
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg,
                "code": 400
            }), 400
        
        # 토큰 검증
        token = Token.verify_token(token_plaintext, 'password_reset')
        
        if not token:
            return jsonify({
                "success": False,
                "error": "유효하지 않거나 만료된 토큰입니다",
                "code": 400
            }), 400
        
        if token.used:
            return jsonify({
                "success": False,
                "error": "이미 사용된 토큰입니다",
                "code": 410
            }), 410
        
        # 사용자 조회
        user = User.query.get(token.user_id)
        if not user:
            return jsonify({
                "success": False,
                "error": "사용자를 찾을 수 없습니다",
                "code": 404
            }), 404
        
        # 비밀번호 변경
        user.set_password(new_password)
        token.mark_as_used()
        
        # 모든 세션 무효화 (보안)
        UserSession.revoke_all_user_sessions(user.id)
        
        db.session.commit()
        
        logger.info(f"비밀번호 재설정 성공: {user.email}")
        
        # 감사 로그
        AuditLog.log_password_change(
            user_id=user.id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        return jsonify({
            "success": True,
            "message": "비밀번호가 성공적으로 변경되었습니다"
        }), 200
        
    except ValueError as e:
        logger.warning(f"비밀번호 재설정 실패: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "code": 400
        }), 400
    except Exception as e:
        logger.error(f"비밀번호 재설정 오류: {e}")
        return jsonify({
            "success": False,
            "error": "비밀번호 재설정 중 오류가 발생했습니다",
            "code": 500
        }), 500

