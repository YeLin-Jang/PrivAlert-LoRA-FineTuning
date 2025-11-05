"""
사용자 프로필 라우트 (마이페이지)
보안: CSRF 보호, 인증 필요
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from app.utils.logger import get_logger
from app.models.user import User
from app.models.session import UserSession
from app.models.audit_log import AuditLog
from app.models.token import Token
from app.extensions.database import db
from app.utils.auth_utils import (
    validate_email, validate_password_strength, get_client_ip, get_user_agent
)
from app.utils.csrf_protection import validate_csrf_token
from app.utils.decorators import login_required
import os

logger = get_logger(__name__)

user_bp = Blueprint('user', __name__)


@user_bp.route('/me', methods=['GET'])
@login_required
def get_profile():
    """
    현재 사용자 정보 조회
    GET /api/v1/user/me
    """
    try:
        user = request.current_user
        
        return jsonify({
            "success": True,
            "data": user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"프로필 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "프로필 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/me', methods=['PATCH'])
@login_required
def update_profile():
    """
    프로필 수정
    PATCH /api/v1/user/me
    Body: { "email": "..." (선택) }
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
        
        data = request.get_json()
        new_email = data.get('email', '').strip().lower() if data else None
        
        # 이메일 변경 시
        if new_email and new_email != user.email:
            # 이메일 형식 검증
            if not validate_email(new_email):
                return jsonify({
                    "success": False,
                    "error": "올바른 이메일 형식이 아닙니다",
                    "code": 400
                }), 400
            
            # 중복 확인
            if User.find_by_email(new_email):
                return jsonify({
                    "success": False,
                    "error": "이미 사용 중인 이메일입니다",
                    "code": 409
                }), 409
            
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
            
            # TODO: 이메일 전송
            # send_verification_email(user.email, token_plaintext)
            
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
            
            return jsonify({
                "success": True,
                "message": "이메일이 변경되었습니다. 새 이메일을 확인하여 계정을 활성화하세요",
                "data": {
                    "user": user.to_dict(),
                    "verification_token": token_plaintext if os.getenv("FLASK_ENV") == "development" else None
                }
            }), 200
        
        # 프로필 업데이트 없음
        return jsonify({
            "success": True,
            "message": "변경사항이 없습니다",
            "data": user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"프로필 수정 오류: {e}")
        return jsonify({
            "success": False,
            "error": "프로필 수정 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/password-change', methods=['POST'])
@login_required
def change_password():
    """
    비밀번호 변경 (현재 비밀번호 확인 필요)
    POST /api/v1/user/password-change
    Body: { "currentPassword": "...", "newPassword": "...", "csrf_token": "..." }
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
        
        data = request.get_json()
        current_password = data.get('currentPassword', '')
        new_password = data.get('newPassword', '')
        
        if not current_password or not new_password:
            return jsonify({
                "success": False,
                "error": "현재 비밀번호와 새 비밀번호를 입력하세요",
                "code": 400
            }), 400
        
        # 현재 비밀번호 확인
        if not user.check_password(current_password):
            return jsonify({
                "success": False,
                "error": "현재 비밀번호가 올바르지 않습니다",
                "code": 401
            }), 401
        
        # 새 비밀번호 강도 검증
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg,
                "code": 400
            }), 400
        
        # 새 비밀번호가 현재 비밀번호와 같은지 확인
        if current_password == new_password:
            return jsonify({
                "success": False,
                "error": "새 비밀번호는 현재 비밀번호와 달라야 합니다",
                "code": 400
            }), 400
        
        # 비밀번호 변경
        user.set_password(new_password)
        
        # 모든 세션 무효화 (보안)
        session_id = request.cookies.get('session_id')
        UserSession.revoke_all_user_sessions(user.id, except_session_id=session_id)
        
        db.session.commit()
        
        logger.info(f"비밀번호 변경 성공: {user.email}")
        
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
        logger.warning(f"비밀번호 변경 실패: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "code": 400
        }), 400
    except Exception as e:
        logger.error(f"비밀번호 변경 오류: {e}")
        return jsonify({
            "success": False,
            "error": "비밀번호 변경 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """
    세션 목록 조회
    GET /api/v1/user/sessions
    """
    try:
        user = request.current_user
        current_session_id = request.cookies.get('session_id')
        
        # 활성 세션 조회
        sessions = UserSession.query.filter_by(
            user_id=user.id,
            is_active=True
        ).order_by(UserSession.last_activity.desc()).all()
        
        # 만료된 세션 제거
        active_sessions = []
        for session in sessions:
            if session.is_expired():
                session.revoke()
            else:
                active_sessions.append(session)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "data": {
                "sessions": [s.to_dict() for s in active_sessions],
                "current_session_id": current_session_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"세션 목록 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "세션 목록 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/sessions/<session_id>', methods=['DELETE'])
@login_required
def revoke_session(session_id):
    """
    특정 세션 무효화
    DELETE /api/v1/user/sessions/<session_id>
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
        
        # 세션 조회 및 소유권 확인
        session = UserSession.find_by_session_id(session_id)
        
        if not session or session.user_id != user.id:
            return jsonify({
                "success": False,
                "error": "세션을 찾을 수 없습니다",
                "code": 404
            }), 404
        
        session.revoke()
        
        logger.info(f"세션 무효화: {session_id}")
        
        # 감사 로그
        AuditLog.log_event(
            user_id=user.id,
            event_type='session_revoked',
            event_description='세션 무효화',
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            success=True,
            extra_data={"session_id": session_id}
        )
        
        return jsonify({
            "success": True,
            "message": "세션이 무효화되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"세션 무효화 오류: {e}")
        return jsonify({
            "success": False,
            "error": "세션 무효화 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/sessions/revoke-all', methods=['POST'])
@login_required
def revoke_all_sessions():
    """
    모든 세션 무효화 (현재 세션 제외)
    POST /api/v1/user/sessions/revoke-all
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
        
        current_session_id = request.cookies.get('session_id')
        
        # 모든 세션 무효화 (현재 세션 제외)
        UserSession.revoke_all_user_sessions(user.id, except_session_id=current_session_id)
        
        logger.info(f"모든 세션 무효화: {user.email}")
        
        # 감사 로그
        AuditLog.log_event(
            user_id=user.id,
            event_type='all_sessions_revoked',
            event_description='모든 세션 무효화',
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            success=True
        )
        
        return jsonify({
            "success": True,
            "message": "모든 세션이 무효화되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"세션 전체 무효화 오류: {e}")
        return jsonify({
            "success": False,
            "error": "세션 무효화 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """
    계정 삭제 요청 (7일 유예)
    POST /api/v1/user/delete-account
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
        
        data = request.get_json()
        password = data.get('password', '')
        
        # 비밀번호 확인
        if not user.check_password(password):
            return jsonify({
                "success": False,
                "error": "비밀번호가 올바르지 않습니다",
                "code": 401
            }), 401
        
        # 계정 삭제 요청
        user.request_deletion()
        
        logger.info(f"계정 삭제 요청: {user.email}")
        
        # 감사 로그
        AuditLog.log_account_deletion(
            user_id=user.id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        return jsonify({
            "success": True,
            "message": "계정 삭제가 요청되었습니다. 7일 후 계정이 영구적으로 삭제됩니다"
        }), 200
        
    except Exception as e:
        logger.error(f"계정 삭제 요청 오류: {e}")
        return jsonify({
            "success": False,
            "error": "계정 삭제 요청 중 오류가 발생했습니다",
            "code": 500
        }), 500

