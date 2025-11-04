"""
관리자 전용 라우트 (RBAC)

시큐어코딩 가이드 준수:
- 모든 관리자 경로에서 인가 검사 필수
- 서버 측에서 권한 판단 (쿠키 기반이 아님)
- 감사 로그: 관리자 액션 기록
"""
from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from app.extensions import db, limiter
from app.models import User, Role, UserRole
from app.utils.api_utils import APIResponse
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/v1/admin")

# API 기반이므로 CSRF 예외 처리 (필요시)
# from app.extensions import csrf
# csrf.exempt(admin_bp)


def is_admin(user) -> bool:
    """관리자 여부 확인 (서버 측 판단)"""
    if not user or not user.is_authenticated:
        return False
    return user.is_admin()


def require_admin(f):
    """관리자 권한 데코레이터"""
    from functools import wraps
    
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not is_admin(current_user):
            logger.warning(f"관리자 권한 없이 접근 시도: {current_user.email if current_user.is_authenticated else 'anonymous'}")
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route("/dashboard", methods=["GET"])
@require_admin
@limiter.limit("100 per hour")
def dashboard():
    """관리자 대시보드"""
    try:
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        admin_users = User.query.join(UserRole).join(Role).filter(Role.name == "admin").count()
        
        logger.info(f"관리자 대시보드 접근: {current_user.email}")
        
        return APIResponse.success(
            data={
                "total_users": total_users,
                "active_users": active_users,
                "admin_users": admin_users,
                "inactive_users": total_users - active_users
            }
        )
    except Exception as e:
        logger.error(f"대시보드 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("대시보드 조회 중 오류가 발생했습니다")


@admin_bp.route("/users", methods=["GET"])
@require_admin
@limiter.limit("100 per hour")
def list_users():
    """사용자 목록 조회 (관리자 전용)"""
    try:
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 20, type=int)
        per_page = min(per_page, 100)  # 최대 100개로 제한
        
        users_query = User.query.order_by(User.created_at.desc())
        pagination = users_query.paginate(page=page, per_page=per_page, error_out=False)
        
        users_data = []
        for user in pagination.items:
            users_data.append({
                "id": user.id,
                "email": user.email,
                "is_active": user.is_active,
                "is_admin": user.is_admin(),
                "roles": [ur.role.name for ur in user.roles],
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            })
        
        logger.info(f"사용자 목록 조회: {current_user.email}")
        
        return APIResponse.success(
            data={
                "users": users_data,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": pagination.total,
                    "pages": pagination.pages
                }
            }
        )
    except Exception as e:
        logger.error(f"사용자 목록 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("사용자 목록 조회 중 오류가 발생했습니다")


@admin_bp.route("/users/<int:user_id>/toggle-active", methods=["POST"])
@require_admin
@limiter.limit("50 per hour")
def toggle_user_active(user_id):
    """사용자 활성화/비활성화 (관리자 전용)"""
    try:
        user = User.query.get_or_404(user_id)
        
        # 자기 자신은 비활성화 불가
        if user.id == current_user.id:
            return APIResponse.error("자기 자신은 비활성화할 수 없습니다", code=400)
        
        user.is_active = not user.is_active
        db.session.commit()
        
        action = "비활성화" if not user.is_active else "활성화"
        logger.info(f"사용자 {action}: {user.email} (관리자: {current_user.email})")
        
        return APIResponse.success(
            message=f"사용자가 {action}되었습니다",
            data={"user_id": user.id, "is_active": user.is_active}
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"사용자 상태 변경 오류: {e}", exc_info=True)
        return APIResponse.server_error("사용자 상태 변경 중 오류가 발생했습니다")


@admin_bp.route("/users/<int:user_id>/roles", methods=["POST"])
@require_admin
@limiter.limit("50 per hour")
def assign_role(user_id):
    """사용자에게 역할 부여 (관리자 전용)"""
    try:
        user = User.query.get_or_404(user_id)
        data = request.get_json(silent=True) or {}
        role_name = data.get("role_name", "").strip()
        
        if not role_name:
            return APIResponse.error("역할 이름은 필수입니다", code=400)
        
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            return APIResponse.error(f"역할 '{role_name}'을 찾을 수 없습니다", code=404)
        
        # 이미 부여된 역할인지 확인
        existing = UserRole.query.filter_by(user_id=user.id, role_id=role.id).first()
        if existing:
            return APIResponse.error("이미 부여된 역할입니다", code=409)
        
        user_role = UserRole(user=user, role=role)
        db.session.add(user_role)
        db.session.commit()
        
        logger.info(f"역할 부여: {user.email} -> {role_name} (관리자: {current_user.email})")
        
        return APIResponse.success(
            message="역할이 부여되었습니다",
            data={"user_id": user.id, "role_name": role_name}
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"역할 부여 오류: {e}", exc_info=True)
        return APIResponse.server_error("역할 부여 중 오류가 발생했습니다")


@admin_bp.route("/users/<int:user_id>/roles/<int:role_id>", methods=["DELETE"])
@require_admin
@limiter.limit("50 per hour")
def remove_role(user_id, role_id):
    """사용자에서 역할 제거 (관리자 전용)"""
    try:
        user = User.query.get_or_404(user_id)
        user_role = UserRole.query.filter_by(user_id=user_id, role_id=role_id).first_or_404()
        role_name = user_role.role.name
        
        # 자기 자신의 admin 권한 제거 불가
        if user.id == current_user.id and role_name == "admin":
            return APIResponse.error("자기 자신의 관리자 권한은 제거할 수 없습니다", code=400)
        
        db.session.delete(user_role)
        db.session.commit()
        
        logger.info(f"역할 제거: {user.email} -> {role_name} (관리자: {current_user.email})")
        
        return APIResponse.success(
            message="역할이 제거되었습니다",
            data={"user_id": user.id, "role_name": role_name}
        )
    except Exception as e:
        db.session.rollback()
        logger.error(f"역할 제거 오류: {e}", exc_info=True)
        return APIResponse.server_error("역할 제거 중 오류가 발생했습니다")

