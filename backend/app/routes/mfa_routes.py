"""
MFA (Multi-Factor Authentication) 라우트
보안: TOTP (RFC 6238) 기반 2단계 인증
"""
from flask import Blueprint, request, jsonify
from app.utils.logger import get_logger
from app.models.user import User
from app.models.audit_log import AuditLog
from app.extensions.database import db
from app.utils.auth_utils import get_client_ip, get_user_agent
from app.utils.csrf_protection import validate_csrf_token
from app.utils.decorators import login_required
import os

logger = get_logger(__name__)

mfa_bp = Blueprint('mfa', __name__)


@mfa_bp.route('/enable', methods=['POST'])
@login_required
def enable_mfa():
    """
    MFA 활성화 (TOTP 시크릿 및 QR 코드 생성)
    POST /api/v1/user/mfa/enable
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        if user.mfa_enabled:
            return jsonify({
                "success": False,
                "error": "MFA가 이미 활성화되어 있습니다",
                "code": 400
            }), 400
        
        # TOTP 시크릿 생성
        secret_plaintext = user.generate_mfa_secret()
        
        # 복구 코드 생성
        backup_codes = user.generate_backup_codes(count=10)
        
        # QR 코드 생성
        qr_code_base64 = user.generate_mfa_qr_code(secret_plaintext)
        
        db.session.commit()
        
        logger.info(f"MFA 활성화 시작: {user.email}")
        
        return jsonify({
            "success": True,
            "data": {
                "secret": secret_plaintext,  # 개발 환경에서만 반환 (프로덕션에서는 제거 권장)
                "qr_code": qr_code_base64,
                "backup_codes": backup_codes,  # 이번 한 번만 반환 (나중에 재생성 불가)
                "message": "QR 코드를 스캔하고 TOTP 토큰을 입력하여 MFA를 활성화하세요"
            }
        }), 200
        
    except Exception as e:
        logger.error(f"MFA 활성화 오류: {e}")
        return jsonify({
            "success": False,
            "error": "MFA 활성화 중 오류가 발생했습니다",
            "code": 500
        }), 500


@mfa_bp.route('/confirm', methods=['POST'])
@login_required
def confirm_mfa():
    """
    MFA 활성화 확인 (TOTP 토큰 검증)
    POST /api/v1/user/mfa/confirm
    Body: { "totp": "...", "csrf_token": "..." }
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        if user.mfa_enabled:
            return jsonify({
                "success": False,
                "error": "MFA가 이미 활성화되어 있습니다",
                "code": 400
            }), 400
        
        if not user.mfa_secret:
            return jsonify({
                "success": False,
                "error": "먼저 MFA를 활성화하세요",
                "code": 400
            }), 400
        
        data = request.get_json()
        totp_code = data.get('totp', '')
        
        if not totp_code:
            return jsonify({
                "success": False,
                "error": "TOTP 토큰을 입력하세요",
                "code": 400
            }), 400
        
        # TOTP 검증
        if not user.verify_totp(totp_code):
            logger.warning(f"MFA 활성화 실패 (TOTP 불일치): {user.email}")
            return jsonify({
                "success": False,
                "error": "TOTP 토큰이 올바르지 않습니다",
                "code": 401
            }), 401
        
        # MFA 활성화
        user.mfa_enabled = True
        db.session.commit()
        
        logger.info(f"MFA 활성화 완료: {user.email}")
        
        # 감사 로그
        AuditLog.log_mfa_enabled(
            user_id=user.id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        return jsonify({
            "success": True,
            "message": "MFA가 성공적으로 활성화되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"MFA 활성화 확인 오류: {e}")
        return jsonify({
            "success": False,
            "error": "MFA 활성화 확인 중 오류가 발생했습니다",
            "code": 500
        }), 500


@mfa_bp.route('/disable', methods=['POST'])
@login_required
def disable_mfa():
    """
    MFA 비활성화
    POST /api/v1/user/mfa/disable
    Body: { "password": "...", "csrf_token": "..." }
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        if not user.mfa_enabled:
            return jsonify({
                "success": False,
                "error": "MFA가 활성화되어 있지 않습니다",
                "code": 400
            }), 400
        
        data = request.get_json()
        password = data.get('password', '')
        
        # 비밀번호 확인
        if not user.check_password(password):
            return jsonify({
                "success": False,
                "error": "비밀번호가 올바르지 않습니다",
                "code": 401
            }), 401
        
        # MFA 비활성화
        user.mfa_enabled = False
        user.mfa_secret = None
        user.mfa_backup_codes_hash = None
        
        db.session.commit()
        
        logger.info(f"MFA 비활성화: {user.email}")
        
        # 감사 로그
        AuditLog.log_mfa_disabled(
            user_id=user.id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        return jsonify({
            "success": True,
            "message": "MFA가 비활성화되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"MFA 비활성화 오류: {e}")
        return jsonify({
            "success": False,
            "error": "MFA 비활성화 중 오류가 발생했습니다",
            "code": 500
        }), 500

