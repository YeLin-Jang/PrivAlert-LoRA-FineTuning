"""
사용자 인증 라우트
보안: 시큐어 코딩 가이드 준수
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions.database import db
from app.models.user import User
from app.utils.logger import get_logger
from app.utils.api_utils import APIResponse
from app.utils.security_utils import validate_text_input
from app.utils.input_sanitizer import sanitize_username, sanitize_email, validate_no_sql_injection
from datetime import datetime
import re

logger = get_logger(__name__)

user_auth_bp = Blueprint('user_auth', __name__)

# 보안: 이메일 형식 검증
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

# 보안: 사용자명 형식 검증 (영문, 숫자, 언더스코어, 하이픈만 허용, 3-20자)
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,20}$')


def validate_email(email: str) -> tuple[bool, str]:
    """
    이메일 검증
    보안: 형식 검증 및 길이 제한
    """
    if not email or not isinstance(email, str):
        return False, "이메일은 필수입니다"
    
    email = email.strip()
    if len(email) > 120:
        return False, "이메일은 120자 이하여야 합니다"
    
    if not EMAIL_PATTERN.match(email):
        return False, "올바른 이메일 형식이 아닙니다"
    
    return True, ""


def validate_username(username: str) -> tuple[bool, str]:
    """
    사용자명 검증
    보안: 형식 검증 및 길이 제한
    """
    if not username or not isinstance(username, str):
        return False, "사용자명은 필수입니다"
    
    username = username.strip()
    if not USERNAME_PATTERN.match(username):
        return False, "사용자명은 3-20자의 영문, 숫자, 언더스코어(_), 하이픈(-)만 사용할 수 있습니다"
    
    return True, ""


@user_auth_bp.route('/register', methods=['POST'])
def register():
    """
    사용자 회원가입
    보안: 입력 검증, 비밀번호 해시화, SQL 인젝션 방지
    """
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("요청 데이터가 없습니다", code=400)
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        detection_options = data.get('detection_options', {})
        
        # 보안: SQL 인젝션 패턴 검증
        sql_check, sql_error = validate_no_sql_injection(username)
        if not sql_check:
            logger.warning(f"SQL 인젝션 시도 감지: username={username}")
            return APIResponse.error("잘못된 입력입니다", code=400)
        
        sql_check, sql_error = validate_no_sql_injection(email)
        if not sql_check:
            logger.warning(f"SQL 인젝션 시도 감지: email={email}")
            return APIResponse.error("잘못된 입력입니다", code=400)
        
        # 보안: 입력값 정제
        username = sanitize_username(username)
        email = sanitize_email(email)
        
        # 입력 검증
        username_valid, username_error = validate_username(username)
        if not username_valid:
            return APIResponse.error(username_error, code=400)
        
        email_valid, email_error = validate_email(email)
        if not email_valid:
            return APIResponse.error(email_error, code=400)
        
        if not password or len(password) < 8:
            return APIResponse.error("비밀번호는 최소 8자 이상이어야 합니다", code=400)
        
        if len(password) > 128:
            return APIResponse.error("비밀번호는 128자 이하여야 합니다", code=400)
        
        # 보안: 중복 사용자명 확인
        if User.find_by_username(username):
            return APIResponse.error("이미 사용 중인 사용자명입니다", code=409)
        
        # 보안: 중복 이메일 확인
        if User.find_by_email(email):
            return APIResponse.error("이미 사용 중인 이메일입니다", code=409)
        
        # 사용자 생성
        user = User(
            username=username,
            email=email,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.flush()  # ID 생성
        
        # 필터링 설정 생성 (회원가입 시 입력받은 옵션 저장)
        if detection_options:
            from app.models.user import UserFilteringSettings
            settings = UserFilteringSettings(user_id=user.id)
            settings.set_detection_options(detection_options)
            db.session.add(settings)
        
        db.session.commit()
        
        # 보안: 민감 정보는 로깅하지 않음 (username만 로깅)
        logger.info(f"사용자 회원가입 성공: username={username}")
        
        return APIResponse.success(
            data={
                'user': user.to_dict(),
                'token': user.generate_token()
            },
            message="회원가입이 완료되었습니다",
            status_code=201
        )
    
    except ValueError as e:
        logger.warning(f"회원가입 입력 검증 실패: {e}")
        return APIResponse.error(str(e), code=400)
    except Exception as e:
        logger.error(f"회원가입 오류: {e}", exc_info=True)
        return APIResponse.server_error("회원가입 중 오류가 발생했습니다")


@user_auth_bp.route('/login', methods=['POST'])
def login():
    """
    사용자 로그인
    보안: 비밀번호 검증, JWT 토큰 발급
    """
    try:
        data = request.get_json()
        if not data:
            return APIResponse.error("요청 데이터가 없습니다", code=400)
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return APIResponse.error("사용자명과 비밀번호는 필수입니다", code=400)
        
        # 보안: SQL 인젝션 패턴 검증
        sql_check, sql_error = validate_no_sql_injection(username)
        if not sql_check:
            logger.warning(f"SQL 인젝션 시도 감지: username={username}")
            return APIResponse.error("잘못된 입력입니다", code=400)
        
        # 보안: 입력값 정제
        username = sanitize_username(username)
        
        # 보안: 사용자 조회 (SQL 인젝션 방지)
        user = User.find_by_username(username)
        if not user:
            logger.warning(f"로그인 실패: username={username} (사용자 없음)")
            return APIResponse.error("잘못된 사용자명 또는 비밀번호입니다", code=401)
        
        if not user.is_active:
            logger.warning(f"로그인 실패: username={username} (계정 비활성)")
            return APIResponse.error("계정이 비활성화되었습니다", code=403)
        
        # 보안: 비밀번호 검증
        if not user.check_password(password):
            logger.warning(f"로그인 실패: username={username} (비밀번호 불일치)")
            return APIResponse.error("잘못된 사용자명 또는 비밀번호입니다", code=401)
        
        # 로그인 시간 업데이트
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # 보안: 민감 정보는 로깅하지 않음 (username만 로깅)
        logger.info(f"사용자 로그인 성공: username={username}")
        
        return APIResponse.success(
            data={
                'user': user.to_dict(),
                'token': user.generate_token()
            },
            message="로그인 성공"
        )
    
    except Exception as e:
        logger.error(f"로그인 오류: {e}", exc_info=True)
        return APIResponse.server_error("로그인 중 오류가 발생했습니다")


@user_auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    현재 로그인한 사용자 정보 조회
    보안: JWT 인증 필요, 일반 사용자만 접근 가능
    """
    try:
        from flask_jwt_extended import get_jwt
        
        # 보안: JWT에서 role 확인 (일반 사용자만 허용)
        claims = get_jwt()
        user_role = claims.get('role', 'user')
        
        if user_role in ['admin', 'super_admin']:
            logger.warning(f"관리자가 일반 사용자 라우트 접근 시도: role={user_role}")
            return APIResponse.error("일반 사용자 전용 기능입니다", code=403)
        
        user_id = get_jwt_identity()
        # 보안: user_id 타입 확인
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            return APIResponse.error("인증 정보가 올바르지 않습니다", code=401)
        
        user = User.query.get(user_id)
        
        if not user:
            return APIResponse.error("사용자를 찾을 수 없습니다", code=404)
        
        if not user.is_active:
            return APIResponse.error("계정이 비활성화되었습니다", code=403)
        
        return APIResponse.success(
            data={'user': user.to_dict()},
            message="사용자 정보 조회 성공"
        )
    
    except Exception as e:
        logger.error(f"사용자 정보 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("사용자 정보 조회 중 오류가 발생했습니다")

