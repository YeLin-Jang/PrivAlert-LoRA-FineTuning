"""관리자 인증 및 권한 데코레이터"""
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from app.utils.logger import get_logger
from app.utils.csrf_protection import validate_csrf_token, get_csrf_token

logger = get_logger(__name__)

def admin_required(f):
    """관리자 권한이 필요한 엔드포인트 데코레이터 (CSRF 보호 포함)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role', 'user')
            user_id = str(claims.get('sub', ''))
            
            if user_role not in ['admin', 'super_admin']:
                logger.warning(f"권한 없는 접근 시도: role={user_role}")
                return jsonify({
                    "success": False,
                    "error": "관리자 권한이 필요합니다",
                    "code": 403
                }), 403
            
            # CSRF 토큰 검증 (POST, PUT, PATCH, DELETE 요청에만)
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                csrf_token = request.headers.get('X-CSRF-Token') or request.json.get('csrf_token') if request.is_json else None
                if not csrf_token:
                    logger.warning(f"CSRF 토큰 없음: user_id={user_id}, method={request.method}")
                    return jsonify({
                        "success": False,
                        "error": "CSRF 토큰이 필요합니다",
                        "code": 403
                    }), 403
                
                is_valid, error_msg = validate_csrf_token(user_id, csrf_token)
                if not is_valid:
                    logger.warning(f"CSRF 토큰 검증 실패: user_id={user_id}, error={error_msg}")
                    return jsonify({
                        "success": False,
                        "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                        "code": 403
                    }), 403
            
            # 요청 컨텍스트에 사용자 정보 추가
            request.current_user_id = user_id
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
    """특정 역할만 허용하는 데코레이터 (CSRF 보호 포함)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_role = claims.get('role', 'user')
                user_id = str(claims.get('sub', ''))
                
                if user_role not in allowed_roles:
                    logger.warning(f"권한 없는 접근 시도: role={user_role}, required={allowed_roles}")
                    return jsonify({
                        "success": False,
                        "error": "권한이 없습니다",
                        "code": 403
                    }), 403
                
                # CSRF 토큰 검증 (POST, PUT, PATCH, DELETE 요청에만)
                if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                    csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
                    if not csrf_token:
                        logger.warning(f"CSRF 토큰 없음: user_id={user_id}, method={request.method}")
                        return jsonify({
                            "success": False,
                            "error": "CSRF 토큰이 필요합니다",
                            "code": 403
                        }), 403
                    
                    is_valid, error_msg = validate_csrf_token(user_id, csrf_token)
                    if not is_valid:
                        logger.warning(f"CSRF 토큰 검증 실패: user_id={user_id}, error={error_msg}")
                        return jsonify({
                            "success": False,
                            "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                            "code": 403
                        }), 403
                
                request.current_user_id = user_id
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


