"""관리자 인증 및 권한 데코레이터"""
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from app.utils.logger import get_logger

logger = get_logger(__name__)

def admin_required(f):
    """관리자 권한이 필요한 엔드포인트 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role', 'user')
            
            if user_role not in ['admin', 'super_admin']:
                logger.warning(f"권한 없는 접근 시도: role={user_role}")
                return jsonify({
                    "success": False,
                    "error": "관리자 권한이 필요합니다",
                    "code": 403
                }), 403
            
            # 요청 컨텍스트에 사용자 정보 추가
            request.current_user_id = claims.get('sub')
            request.current_user_role = user_role
            
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"인증 오류: {e}")
            return jsonify({
                "success": False,
                "error": "인증이 필요합니다",
                "code": 401
            }), 401
    
    return decorated_function

def role_required(*allowed_roles):
    """특정 역할만 허용하는 데코레이터"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_role = claims.get('role', 'user')
                
                if user_role not in allowed_roles:
                    logger.warning(f"권한 없는 접근 시도: role={user_role}, required={allowed_roles}")
                    return jsonify({
                        "success": False,
                        "error": "권한이 없습니다",
                        "code": 403
                    }), 403
                
                request.current_user_id = claims.get('sub')
                request.current_user_role = user_role
                
                return f(*args, **kwargs)
            except Exception as e:
                logger.error(f"인증 오류: {e}")
                return jsonify({
                    "success": False,
                    "error": "인증이 필요합니다",
                    "code": 401
                }), 401
        
        return decorated_function
    return decorator


