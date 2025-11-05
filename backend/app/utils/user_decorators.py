"""
일반 사용자 인증 및 권한 데코레이터
보안: 관리자와 일반 사용자 구분, 접근 제어
"""
from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from app.utils.logger import get_logger

logger = get_logger(__name__)

def user_required(f):
    """
    일반 사용자 권한이 필요한 엔드포인트 데코레이터
    보안: 관리자 역할로 접근 시도 방지
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            user_role = claims.get('role', 'user')
            user_id = claims.get('sub')
            
            # 보안: 관리자 역할로 일반 사용자 라우트 접근 방지
            if user_role in ['admin', 'super_admin']:
                logger.warning(f"관리자가 일반 사용자 라우트 접근 시도: role={user_role}, user_id={user_id}")
                return jsonify({
                    "success": False,
                    "error": "일반 사용자 전용 기능입니다",
                    "code": 403
                }), 403
            
            # 보안: user_id가 정수인지 확인
            try:
                user_id = int(user_id)
            except (ValueError, TypeError):
                logger.warning(f"잘못된 user_id 형식: {user_id}")
                return jsonify({
                    "success": False,
                    "error": "인증 정보가 올바르지 않습니다",
                    "code": 401
                }), 401
            
            # 보안: user_id 범위 검증
            if user_id <= 0:
                logger.warning(f"잘못된 user_id 값: {user_id}")
                return jsonify({
                    "success": False,
                    "error": "인증 정보가 올바르지 않습니다",
                    "code": 401
                }), 401
            
            # 요청 컨텍스트에 사용자 정보 추가
            request.current_user_id = user_id
            request.current_user_role = user_role
            
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"인증 오류: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "인증이 필요합니다",
                "code": 401
            }), 401
    
    return decorated_function

