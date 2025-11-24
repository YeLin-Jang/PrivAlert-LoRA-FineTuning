"""사용자 필터링 설정 라우트"""
from flask import Blueprint, request
from datetime import datetime
from app.utils.logger import get_logger
from app.models.user import User, UserFilteringSettings
from app.extensions.database import db
from app.utils.decorators import login_required
from app.utils.api_utils import APIResponse
from app.utils.user_route_helpers import (
    validate_csrf_from_session, check_user_active, validate_json_request
)

logger = get_logger(__name__)

user_settings_bp = Blueprint('user_settings', __name__)


@user_settings_bp.route('/filtering-settings', methods=['GET'])
@login_required
def get_filtering_settings():
    """사용자 필터링 설정 조회"""
    try:
        user = request.current_user
        
        # 사용자 활성화 확인
        is_active, error = check_user_active(user)
        if not is_active:
            return error
        
        # 필터링 설정 조회 또는 생성
        try:
            settings = user.filtering_settings
            if not settings:
                # 설정이 없으면 기본값으로 생성
                settings = UserFilteringSettings(user_id=user.id)
                settings.set_detection_options({})
                db.session.add(settings)
                db.session.commit()
                logger.info(f"필터링 설정 생성: user_id={user.id}")
            
            return APIResponse.success(
                data={'settings': settings.to_dict()},
                message="필터링 설정 조회 성공"
            )
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return APIResponse.server_error("필터링 설정 조회 중 오류가 발생했습니다")
    
    except Exception as e:
        logger.error(f"필터링 설정 조회 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("필터링 설정 조회 중 오류가 발생했습니다")


@user_settings_bp.route('/filtering-settings', methods=['PUT'])
@login_required
def update_filtering_settings():
    """사용자 필터링 설정 업데이트"""
    try:
        # CSRF 검증 (세션 기반)
        is_valid, error = validate_csrf_from_session()
        if not is_valid:
            return error
        
        user = request.current_user
        
        # 사용자 활성화 확인
        is_active, error = check_user_active(user)
        if not is_active:
            return error
        
        # JSON 요청 검증
        is_valid, data, error = validate_json_request()
        if not is_valid:
            return error
        
        detection_options = data.get('detection_options', {})
        
        if not isinstance(detection_options, dict):
            return APIResponse.error("detection_options는 객체여야 합니다", code=400)
        
        allowed_keys = {
            'face', 'fingerprint', 'phone', 'rrn', 'passport', 'ip_address',
            'email', 'account', 'school', 'workplace', 'name', 'address'
        }
        
        invalid_keys = [key for key in detection_options.keys() if key not in allowed_keys]
        if invalid_keys:
            logger.warning(f"허용되지 않은 필터링 옵션: {invalid_keys}, user_id={user.id}")
            return APIResponse.error("허용되지 않은 필터링 옵션이 포함되어 있습니다", code=400)
        
        for key, value in detection_options.items():
            if not isinstance(value, bool):
                logger.warning(f"잘못된 필터링 옵션 값 타입: {key}={value}, user_id={user.id}")
                return APIResponse.error(f"필터링 옵션 '{key}'의 값은 boolean이어야 합니다", code=400)
        
        # 필터링 설정 조회 또는 생성
        try:
            settings = user.filtering_settings
            if not settings:
                settings = UserFilteringSettings(user_id=user.id)
                db.session.add(settings)
            
            # 설정 업데이트
            settings.set_detection_options(detection_options)
            settings.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"필터링 설정 업데이트 성공: user_id={user.id}")
            
            return APIResponse.success(
                data={'settings': settings.to_dict()},
                message="필터링 설정이 업데이트되었습니다"
            )
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return APIResponse.server_error("필터링 설정 업데이트 중 오류가 발생했습니다")
    
    except Exception as e:
        logger.error(f"필터링 설정 업데이트 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("필터링 설정 업데이트 중 오류가 발생했습니다")

