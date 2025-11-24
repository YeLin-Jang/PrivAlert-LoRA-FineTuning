"""사용자 세션 관리 라우트"""
from flask import Blueprint, request
from app.utils.logger import get_logger
from app.models.session import UserSession
from app.models.audit_log import AuditLog
from app.extensions.database import db
from app.utils.auth_utils import get_client_ip, get_user_agent
from app.utils.decorators import login_required
from app.utils.api_utils import APIResponse
from app.utils.user_route_helpers import validate_csrf_from_request

logger = get_logger(__name__)

user_session_bp = Blueprint('user_session', __name__)


@user_session_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """세션 목록 조회"""
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
        
        return APIResponse.success(
            data={
                "sessions": [s.to_dict() for s in active_sessions],
                "current_session_id": current_session_id
            }
        )
        
    except Exception as e:
        logger.error(f"세션 목록 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("세션 목록 조회 중 오류가 발생했습니다")


@user_session_bp.route('/sessions/<session_id>', methods=['DELETE'])
@login_required
def revoke_session(session_id):
    """특정 세션 무효화"""
    try:
        # CSRF 검증
        is_valid, error = validate_csrf_from_request()
        if not is_valid:
            return error
        
        user = request.current_user
        
        # 세션 조회 및 소유권 확인
        session = UserSession.find_by_session_id(session_id)
        
        if not session or session.user_id != user.id:
            return APIResponse.not_found("세션을 찾을 수 없습니다")
        
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
        
        return APIResponse.success(message="세션이 무효화되었습니다")
        
    except Exception as e:
        logger.error(f"세션 무효화 오류: {e}", exc_info=True)
        return APIResponse.server_error("세션 무효화 중 오류가 발생했습니다")


@user_session_bp.route('/sessions/revoke-all', methods=['POST'])
@login_required
def revoke_all_sessions():
    """모든 세션 무효화 (현재 세션 제외)"""
    try:
        # CSRF 검증
        is_valid, error = validate_csrf_from_request()
        if not is_valid:
            return error
        
        user = request.current_user
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
        
        return APIResponse.success(message="모든 세션이 무효화되었습니다")
        
    except Exception as e:
        logger.error(f"세션 전체 무효화 오류: {e}", exc_info=True)
        return APIResponse.server_error("세션 무효화 중 오류가 발생했습니다")

