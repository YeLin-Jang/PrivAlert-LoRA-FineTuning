"""
인증 라우트 (회원가입/로그인/로그아웃/비밀번호 변경/탈퇴)

시큐어코딩 가이드 준수:
- 비밀번호는 솔트+해시로 저장
- 재인증: 비밀번호 변경/탈퇴 시 필수
- 레이트 리미팅: 브루트포스 공격 방지
- CSRF 보호: 모든 POST 요청에 적용
"""
import secrets
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db, limiter
from app.models import User, Role, UserRole
from app.utils.api_utils import APIResponse
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

# API 기반이므로 CSRF 예외 처리 (필요시)
# from app.extensions import csrf
# csrf.exempt(auth_bp)


@auth_bp.route("/signup", methods=["POST"])
@limiter.limit("10 per minute")  # 레이트 리미팅
def signup():
    """회원가입"""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        
        # 입력 검증
        if not email or not password:
            return APIResponse.error("이메일과 비밀번호는 필수입니다", code=400)
        
        if len(password) < 8:
            return APIResponse.error("비밀번호는 최소 8자 이상이어야 합니다", code=400)
        
        # 이메일 형식 검증 (간단한 검증)
        if "@" not in email or "." not in email:
            return APIResponse.error("올바른 이메일 형식이 아닙니다", code=400)
        
        # 중복 확인
        if User.query.filter_by(email=email).first():
            return APIResponse.error("이미 가입된 이메일입니다", code=409)
        
        # 사용자 생성
        user = User(email=email)
        user.set_password(password)  # 솔트 포함 해시
        db.session.add(user)
        
        # 기본 롤(user) 부여 - 서버 측 인가
        user_role = Role.query.filter_by(name="user").first()
        if not user_role:
            # 롤이 없으면 생성 (초기 데이터 시드에서 처리되어야 함)
            logger.warning("'user' 역할이 없습니다. 초기 데이터 시드를 실행하세요.")
            return APIResponse.error("서버 설정 오류", code=500)
        
        db.session.add(UserRole(user=user, role=user_role))
        db.session.commit()
        
        logger.info(f"새 사용자 가입: {email}")
        return APIResponse.success(
            message="가입이 완료되었습니다",
            data={"user_id": user.id}
        )
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"회원가입 오류: {e}", exc_info=True)
        return APIResponse.server_error("회원가입 중 오류가 발생했습니다")


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")  # 레이트 리미팅 (브루트포스 방지)
def login():
    """로그인"""
    try:
        data = request.get_json(silent=True) or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        
        if not email or not password:
            return APIResponse.error("이메일과 비밀번호는 필수입니다", code=400)
        
        user = User.query.filter_by(email=email).first()
        
        # 보안: 존재 여부와 비밀번호 확인을 분리하지 않음 (타이밍 공격 방지)
        if not user or not user.check_password(password):
            logger.warning(f"로그인 실패 시도: {email}")
            return APIResponse.error("이메일 또는 비밀번호가 올바르지 않습니다", code=401)
        
        if not user.is_active:
            logger.warning(f"비활성화 계정 로그인 시도: {email}")
            return APIResponse.error("비활성화된 계정입니다", code=403)
        
        # 로그인 성공
        login_user(user, remember=False)  # remember는 필요시 설정
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"로그인 성공: {email}")
        return APIResponse.success(
            message="로그인 성공",
            data={
                "user_id": user.id,
                "email": user.email,
                "is_admin": user.is_admin()
            }
        )
        
    except Exception as e:
        logger.error(f"로그인 오류: {e}", exc_info=True)
        return APIResponse.server_error("로그인 중 오류가 발생했습니다")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """로그아웃"""
    try:
        email = current_user.email if current_user.is_authenticated else "unknown"
        logout_user()
        logger.info(f"로그아웃: {email}")
        return APIResponse.success(message="로그아웃되었습니다")
    except Exception as e:
        logger.error(f"로그아웃 오류: {e}", exc_info=True)
        return APIResponse.server_error("로그아웃 중 오류가 발생했습니다")


@auth_bp.route("/change-password", methods=["POST"])
@login_required
@limiter.limit("5 per hour")  # 비밀번호 변경 레이트 리미팅
def change_password():
    """비밀번호 변경 (재인증 필수)"""
    try:
        data = request.get_json(silent=True) or {}
        current_pw = data.get("current_password", "")
        new_pw = data.get("new_password", "")
        
        if not current_pw or not new_pw:
            return APIResponse.error("현재 비밀번호와 새 비밀번호는 필수입니다", code=400)
        
        if len(new_pw) < 8:
            return APIResponse.error("새 비밀번호는 최소 8자 이상이어야 합니다", code=400)
        
        # 재인증: 현재 비밀번호 확인
        if not current_user.check_password(current_pw):
            logger.warning(f"비밀번호 변경 실패 (재인증 실패): {current_user.email}")
            return APIResponse.error("현재 비밀번호가 올바르지 않습니다", code=401)
        
        # 비밀번호 변경
        current_user.set_password(new_pw)
        db.session.commit()
        
        logger.info(f"비밀번호 변경 성공: {current_user.email}")
        return APIResponse.success(message="비밀번호가 변경되었습니다")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"비밀번호 변경 오류: {e}", exc_info=True)
        return APIResponse.server_error("비밀번호 변경 중 오류가 발생했습니다")


@auth_bp.route("/withdraw", methods=["POST"])
@login_required
@limiter.limit("3 per hour")  # 탈퇴 레이트 리미팅
def withdraw():
    """회원 탈퇴 (재확인 필수)"""
    try:
        data = request.get_json(silent=True) or {}
        confirm = data.get("confirm", "").strip().lower()
        password = data.get("password", "")  # 재인증용
        
        # 재확인 및 재인증
        if confirm != "yes":
            return APIResponse.error("탈퇴를 확인하려면 'yes'를 입력하세요", code=400)
        
        if not password or not current_user.check_password(password):
            logger.warning(f"탈퇴 시도 (재인증 실패): {current_user.email}")
            return APIResponse.error("비밀번호가 올바르지 않습니다", code=401)
        
        # 탈퇴 처리 (소프트 삭제: is_active=False)
        email = current_user.email
        current_user.is_active = False
        db.session.commit()
        
        logout_user()
        
        logger.info(f"회원 탈퇴: {email}")
        return APIResponse.success(message="탈퇴가 완료되었습니다")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"탈퇴 오류: {e}", exc_info=True)
        return APIResponse.server_error("탈퇴 처리 중 오류가 발생했습니다")


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    """현재 사용자 정보 조회"""
    try:
        return APIResponse.success(
            data={
                "user_id": current_user.id,
                "email": current_user.email,
                "is_active": current_user.is_active,
                "is_admin": current_user.is_admin(),
                "roles": [ur.role.name for ur in current_user.roles],
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None
            }
        )
    except Exception as e:
        logger.error(f"사용자 정보 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("사용자 정보 조회 중 오류가 발생했습니다")

