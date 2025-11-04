"""관리자 인증 라우트"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    unset_jwt_cookies
)
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta
from app.utils.logger import get_logger
import os

logger = get_logger(__name__)

admin_auth_bp = Blueprint('admin_auth', __name__)

# 임시 관리자 계정 (실제로는 데이터베이스에서 조회해야 함)
# 프로덕션에서는 반드시 데이터베이스 사용
ADMIN_USERS = {
    "admin": {
        "password_hash": generate_password_hash("admin123!"),  # 기본 비밀번호 (변경 필요)
        "role": "admin",
        "id": 1,
        "username": "admin"
    },
    "super_admin": {
        "password_hash": generate_password_hash("super123!"),  # 기본 비밀번호 (변경 필요)
        "role": "super_admin",
        "id": 2,
        "username": "super_admin"
    }
}

@admin_auth_bp.route('/login', methods=['POST'])
def admin_login():
    """관리자 로그인"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                "success": False,
                "error": "사용자명과 비밀번호를 입력해주세요",
                "code": 400
            }), 400
        
        # 임시 관리자 계정 확인 (실제로는 DB에서 조회)
        user = ADMIN_USERS.get(username)
        if not user or not check_password_hash(user['password_hash'], password):
            logger.warning(f"관리자 로그인 실패: username={username}")
            return jsonify({
                "success": False,
                "error": "잘못된 사용자명 또는 비밀번호입니다",
                "code": 401
            }), 401
        
        # JWT 토큰 생성
        additional_claims = {
            "role": user['role'],
            "username": user['username']
        }
        
        access_token = create_access_token(
            identity=str(user['id']),
            additional_claims=additional_claims,
            expires_delta=timedelta(minutes=15)
        )
        refresh_token = create_refresh_token(
            identity=str(user['id']),
            additional_claims=additional_claims,
            expires_delta=timedelta(days=7)
        )
        
        logger.info(f"관리자 로그인 성공: username={username}, role={user['role']}")
        
        response = jsonify({
            "success": True,
            "data": {
                "access_token": access_token,
                "user": {
                    "id": user['id'],
                    "username": user['username'],
                    "role": user['role']
                }
            }
        })
        
        # Refresh Token을 HttpOnly 쿠키에 저장
        flask_env = os.getenv("FLASK_ENV", "development")
        response.set_cookie(
            'refresh_token',
            refresh_token,
            httponly=True,
            secure=(flask_env == "production"),
            samesite='Lax',
            max_age=604800  # 7일
        )
        
        return response, 200
        
    except Exception as e:
        logger.error(f"로그인 오류: {e}")
        return jsonify({
            "success": False,
            "error": "로그인 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def admin_logout():
    """관리자 로그아웃"""
    try:
        # JWT 블랙리스트에 추가 (실제 구현 시 Redis 등 사용)
        # 현재는 쿠키만 제거
        response = jsonify({
            "success": True,
            "message": "로그아웃되었습니다"
        })
        unset_jwt_cookies(response)
        return response, 200
    except Exception as e:
        logger.error(f"로그아웃 오류: {e}")
        return jsonify({
            "success": False,
            "error": "로그아웃 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    """토큰 갱신"""
    try:
        current_user_id = get_jwt_identity()
        claims = get_jwt()
        
        new_access_token = create_access_token(
            identity=current_user_id,
            additional_claims={
                "role": claims.get('role'),
                "username": claims.get('username')
            },
            expires_delta=timedelta(minutes=15)
        )
        
        return jsonify({
            "success": True,
            "data": {
                "access_token": new_access_token
            }
        }), 200
    except Exception as e:
        logger.error(f"토큰 갱신 오류: {e}")
        return jsonify({
            "success": False,
            "error": "토큰 갱신 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_admin():
    """현재 로그인한 관리자 정보"""
    try:
        claims = get_jwt()
        user_id = get_jwt_identity()
        
        # 실제로는 DB에서 조회
        user = ADMIN_USERS.get(claims.get('username', ''))
        if not user:
            return jsonify({
                "success": False,
                "error": "사용자를 찾을 수 없습니다",
                "code": 404
            }), 404
        
        return jsonify({
            "success": True,
            "data": {
                "id": user['id'],
                "username": user['username'],
                "role": user['role']
            }
        }), 200
    except Exception as e:
        logger.error(f"사용자 정보 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "사용자 정보 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500

@admin_auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """비밀번호 변경"""
    try:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({
                "success": False,
                "error": "현재 비밀번호와 새 비밀번호를 입력해주세요",
                "code": 400
            }), 400
        
        if len(new_password) < 8:
            return jsonify({
                "success": False,
                "error": "비밀번호는 최소 8자 이상이어야 합니다",
                "code": 400
            }), 400
        
        claims = get_jwt()
        username = claims.get('username')
        
        user = ADMIN_USERS.get(username)
        if not user or not check_password_hash(user['password_hash'], current_password):
            return jsonify({
                "success": False,
                "error": "현재 비밀번호가 올바르지 않습니다",
                "code": 401
            }), 401
        
        # 비밀번호 업데이트 (실제로는 DB에 저장)
        ADMIN_USERS[username]['password_hash'] = generate_password_hash(new_password)
        
        logger.info(f"비밀번호 변경 성공: username={username}")
        return jsonify({
            "success": True,
            "message": "비밀번호가 변경되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"비밀번호 변경 오류: {e}")
        return jsonify({
            "success": False,
            "error": "비밀번호 변경 중 오류가 발생했습니다",
            "code": 500
        }), 500

