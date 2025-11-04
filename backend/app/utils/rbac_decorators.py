"""
RBAC 데코레이터
- 역할 기반 접근 제어
- 관리자 전용 데코레이터
"""

import logging
from functools import wraps
from flask import jsonify, request
from flask_login import current_user
from app.models.audit_log import AuditAction
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


def login_required(f):
    """로그인 필요 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user or not current_user.is_authenticated:
            return jsonify({
                'success': False,
                'error': '로그인이 필요합니다',
                'code': 401
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def role_required(*role_names):
    """
    특정 역할 필요 데코레이터
    
    사용 예:
        @role_required('admin', 'moderator')
        def admin_route():
            ...
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if not current_user:
                return jsonify({
                    'success': False,
                    'error': '로그인이 필요합니다',
                    'code': 401
                }), 401
            
            # 역할 확인
            if not current_user.has_any_role(list(role_names)):
                # 감사 로그 기록 (권한 없는 접근 시도)
                audit_service.log_action(
                    user_id=current_user.id,
                    action=AuditAction.SENSITIVE_DATA_ACCESS,
                    ip_address=request.remote_addr,
                    success=False,
                    message=f"권한 없는 접근 시도: {f.__name__} (필요 역할: {role_names})"
                )
                
                logger.warning(
                    f"권한 없는 접근 시도: {current_user.username} -> {f.__name__} "
                    f"(필요 역할: {role_names})"
                )
                
                return jsonify({
                    'success': False,
                    'error': '권한이 없습니다',
                    'code': 403
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    관리자 전용 데코레이터
    - 관리자 행위는 모두 감사 로그에 기록
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user:
            return jsonify({
                'success': False,
                'error': '로그인이 필요합니다',
                'code': 401
            }), 401
        
        if not current_user.is_admin():
            # 감사 로그 기록
            audit_service.log_action(
                user_id=current_user.id,
                action=AuditAction.SENSITIVE_DATA_ACCESS,
                ip_address=request.remote_addr,
                success=False,
                message=f"관리자 권한 없는 접근 시도: {f.__name__}"
            )
            
            logger.warning(
                f"관리자 권한 없는 접근 시도: {current_user.username} -> {f.__name__}"
            )
            
            return jsonify({
                'success': False,
                'error': '관리자 권한이 필요합니다',
                'code': 403
            }), 403
        
        # 관리자 행위 감사 로그 기록
        audit_service.log_action(
            user_id=current_user.id,
            action=AuditAction.ADMIN_ACTION,
            ip_address=request.remote_addr,
            request_method=request.method,
            request_path=request.path,
            success=True,
            message=f"관리자 행위: {f.__name__}"
        )
        
        return f(*args, **kwargs)
    return decorated_function


def active_user_required(f):
    """활성 사용자만 허용 데코레이터"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_active:
            return jsonify({
                'success': False,
                'error': '비활성화된 계정입니다',
                'code': 403
            }), 403
        return f(*args, **kwargs)
    return decorated_function

