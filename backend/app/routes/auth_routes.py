"""
인증 라우트
- 회원가입, 로그인, 로그아웃
- 세션 관리
"""

import logging
from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import auth_service
from app.services.audit_service import audit_service
from app.models.audit_log import AuditAction
from app.utils.api_utils import APIResponse
from app.utils.csrf_protection import csrf_protect_manual
from app.utils.rbac_decorators import login_required as rbac_login_required

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
@csrf_protect_manual
def register():
    """
    회원가입 API
    
    ---
    tags:
      - 인증
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - username
            - email
            - password
          properties:
            username:
              type: string
              description: 사용자명
            email:
              type: string
              description: 이메일
            password:
              type: string
              description: 비밀번호
            full_name:
              type: string
              description: 전체 이름 (선택)
    responses:
      200:
        description: 회원가입 성공
      400:
        description: 잘못된 요청
    """
    try:
        data = request.get_json()
        
        if not data:
            return APIResponse.error("요청 데이터가 없습니다", code=400)
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip() or None
        
        # IP 주소 추출
        ip_address = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            ip_address = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        
        # 회원가입 처리
        result = auth_service.register_user(
            username=username,
            email=email,
            password=password,
            full_name=full_name,
            ip_address=ip_address
        )
        
        if result.get('success'):
            return APIResponse.success(
                {'user': result.get('user')},
                message=result.get('message', '회원가입이 완료되었습니다')
            )
        else:
            return APIResponse.error(result.get('error', '회원가입 실패'), code=400)
    
    except Exception as e:
        logger.error(f"회원가입 API 오류: {e}")
        return APIResponse.server_error("회원가입 중 오류가 발생했습니다")


@auth_bp.route('/login', methods=['POST'])
@csrf_protect_manual
def login():
    """
    로그인 API
    
    ---
    tags:
      - 인증
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        schema:
          type: object
          required:
            - username
            - password
          properties:
            username:
              type: string
              description: 사용자명 또는 이메일
            password:
              type: string
              description: 비밀번호
    responses:
      200:
        description: 로그인 성공
      400:
        description: 로그인 실패
    """
    try:
        data = request.get_json()
        
        if not data:
            return APIResponse.error("요청 데이터가 없습니다", code=400)
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return APIResponse.error("사용자명과 비밀번호를 입력하세요", code=400)
        
        # IP 주소 및 User-Agent 추출
        ip_address = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            ip_address = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        user_agent = request.headers.get('User-Agent', '')
        
        # 인증 처리
        result = auth_service.authenticate_user(
            username=username,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if result.get('success'):
            user = result.get('user')
            
            # Flask-Login 세션 생성
            from app.extensions.database import get_db
            from app.models.user import User
            db = get_db()
            user_obj = db.query(User).filter_by(id=user['id']).first()
            
            if user_obj:
                login_user(user_obj, remember=True)  # 세션 생성
                
                return APIResponse.success(
                    {
                        'user': user,
                        'session_id': session.get('_id', '')
                    },
                    message=result.get('message', '로그인 성공')
                )
            else:
                return APIResponse.error("사용자를 찾을 수 없습니다", code=500)
        else:
            return APIResponse.error(result.get('error', '로그인 실패'), code=401)
    
    except Exception as e:
        logger.error(f"로그인 API 오류: {e}")
        return APIResponse.server_error("로그인 중 오류가 발생했습니다")


@auth_bp.route('/logout', methods=['POST'])
@rbac_login_required
@csrf_protect_manual
def logout():
    """
    로그아웃 API
    
    ---
    tags:
      - 인증
    responses:
      200:
        description: 로그아웃 성공
    """
    try:
        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else None
        
        # IP 주소 추출
        ip_address = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            ip_address = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        
        # 로그아웃 처리
        logout_user()
        session.clear()
        
        # 감사 로그 기록
        audit_service.log_action(
            user_id=user_id,
            action=AuditAction.LOGOUT,
            ip_address=ip_address,
            success=True,
            message=f"로그아웃: {username}"
        )
        
        return APIResponse.success(message="로그아웃되었습니다")
    
    except Exception as e:
        logger.error(f"로그아웃 API 오류: {e}")
        return APIResponse.server_error("로그아웃 중 오류가 발생했습니다")


@auth_bp.route('/me', methods=['GET'])
@rbac_login_required
def get_current_user():
    """
    현재 사용자 정보 조회 API
    
    ---
    tags:
      - 인증
    responses:
      200:
        description: 사용자 정보
    """
    try:
        if current_user:
            return APIResponse.success({
                'user': current_user.to_dict()
            })
        else:
            return APIResponse.error("로그인이 필요합니다", code=401)
    
    except Exception as e:
        logger.error(f"사용자 정보 조회 API 오류: {e}")
        return APIResponse.server_error("사용자 정보 조회 중 오류가 발생했습니다")


@auth_bp.route('/session', methods=['GET'])
def check_session():
    """
    세션 확인 API
    
    ---
    tags:
      - 인증
    responses:
      200:
        description: 세션 상태
    """
    try:
        if current_user and current_user.is_authenticated:
            return APIResponse.success({
                'authenticated': True,
                'user': current_user.to_dict()
            })
        else:
            return APIResponse.success({
                'authenticated': False
            })
    
    except Exception as e:
        logger.error(f"세션 확인 API 오류: {e}")
        return APIResponse.success({'authenticated': False})

