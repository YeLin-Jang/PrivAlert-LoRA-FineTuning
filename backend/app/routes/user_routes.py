"""
사용자 마이페이지 관련 라우트
보안: 시큐어 코딩 가이드 준수
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions.database import db
from app.models.user import User, UserFilteringSettings, RevisionHistory
from app.utils.logger import get_logger
from app.utils.api_utils import APIResponse
from app.utils.user_decorators import user_required
from app.utils.input_sanitizer import validate_no_sql_injection
from datetime import datetime

logger = get_logger(__name__)

user_bp = Blueprint('user', __name__)


@user_bp.route('/filtering-settings', methods=['GET'])
@jwt_required()
@user_required
def get_filtering_settings():
    """
    사용자 필터링 설정 조회
    보안: JWT 인증 필요, 일반 사용자만 접근 가능, 본인만 조회 가능
    """
    try:
        # 보안: user_id는 정수로 변환 (안전한 변환)
        try:
            user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            logger.warning(f"잘못된 user_id 형식: {get_jwt_identity()}")
            return APIResponse.error("인증 정보가 올바르지 않습니다", code=401)
        
        # 보안: user_id 범위 검증
        if user_id <= 0:
            logger.warning(f"잘못된 user_id 값: {user_id}")
            return APIResponse.error("인증 정보가 올바르지 않습니다", code=401)
        
        user = User.query.get(user_id)
        
        if not user:
            logger.warning(f"사용자를 찾을 수 없음: user_id={user_id}")
            return APIResponse.error("사용자를 찾을 수 없습니다", code=404)
        
        if not user.is_active:
            logger.warning(f"비활성화된 사용자 접근 시도: user_id={user_id}")
            return APIResponse.error("계정이 비활성화되었습니다", code=403)
        
        # 필터링 설정 조회 또는 생성
        try:
            settings = user.filtering_settings
            if not settings:
                # 설정이 없으면 기본값으로 생성
                settings = UserFilteringSettings(user_id=user.id)
                settings.set_detection_options({})
                db.session.add(settings)
                db.session.commit()
                logger.info(f"필터링 설정 생성: user_id={user_id}")
            
            return APIResponse.success(
                data={'settings': settings.to_dict()},
                message="필터링 설정 조회 성공"
            )
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return APIResponse.server_error("필터링 설정 조회 중 오류가 발생했습니다")
    
    except ValueError as e:
        logger.warning(f"입력값 검증 오류: {e}")
        return APIResponse.error("입력값이 올바르지 않습니다", code=400)
    except Exception as e:
        logger.error(f"필터링 설정 조회 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("필터링 설정 조회 중 오류가 발생했습니다")


@user_bp.route('/filtering-settings', methods=['PUT'])
@jwt_required()
@user_required
def update_filtering_settings():
    """
    사용자 필터링 설정 업데이트
    보안: JWT 인증 필요, 일반 사용자만 접근 가능, 본인만 수정 가능, 입력 검증
    """
    try:
        # 보안: user_id는 정수로 변환 (안전한 변환)
        try:
            user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            logger.warning(f"잘못된 user_id 형식: {get_jwt_identity()}")
            return APIResponse.error("인증 정보가 올바르지 않습니다", code=401)
        
        # 보안: user_id 범위 검증
        if user_id <= 0:
            logger.warning(f"잘못된 user_id 값: {user_id}")
            return APIResponse.error("인증 정보가 올바르지 않습니다", code=401)
        
        user = User.query.get(user_id)
        
        if not user:
            logger.warning(f"사용자를 찾을 수 없음: user_id={user_id}")
            return APIResponse.error("사용자를 찾을 수 없습니다", code=404)
        
        if not user.is_active:
            logger.warning(f"비활성화된 사용자 접근 시도: user_id={user_id}")
            return APIResponse.error("계정이 비활성화되었습니다", code=403)
        
        data = request.get_json()
        if not data:
            return APIResponse.error("요청 데이터가 없습니다", code=400)
        
        detection_options = data.get('detection_options', {})
        
        if not isinstance(detection_options, dict):
            return APIResponse.error("detection_options는 객체여야 합니다", code=400)
        
        # 보안: 키 검증 (허용된 키만 허용)
        allowed_keys = {
            'face', 'fingerprint', 'phone', 'rrn', 'passport', 'ip_address',
            'email', 'account', 'school', 'workplace', 'name', 'address',
            'driverLicense', 'postalCode'
        }
        
        # 보안: 모든 키가 허용된 키인지 확인
        invalid_keys = [key for key in detection_options.keys() if key not in allowed_keys]
        if invalid_keys:
            logger.warning(f"허용되지 않은 필터링 옵션: {invalid_keys}, user_id={user_id}")
            return APIResponse.error("허용되지 않은 필터링 옵션이 포함되어 있습니다", code=400)
        
        # 보안: 값 타입 검증 (boolean만 허용)
        for key, value in detection_options.items():
            if not isinstance(value, bool):
                logger.warning(f"잘못된 필터링 옵션 값 타입: {key}={value}, user_id={user_id}")
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
            
            logger.info(f"필터링 설정 업데이트 성공: user_id={user_id}")
            
            return APIResponse.success(
                data={'settings': settings.to_dict()},
                message="필터링 설정이 업데이트되었습니다"
            )
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return APIResponse.server_error("필터링 설정 업데이트 중 오류가 발생했습니다")
    
    except ValueError as e:
        logger.warning(f"입력값 검증 오류: {e}")
        db.session.rollback()
        return APIResponse.error("입력값이 올바르지 않습니다", code=400)
    except Exception as e:
        logger.error(f"필터링 설정 업데이트 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("필터링 설정 업데이트 중 오류가 발생했습니다")


@user_bp.route('/revision-history', methods=['GET'])
@jwt_required()
@user_required
def get_revision_history():
    """
    사용자 수정 기록 조회
    보안: JWT 인증 필요, 일반 사용자만 접근 가능, 본인만 조회 가능, 민감 정보 제외
    """
    try:
        # 보안: user_id는 정수로 변환 (안전한 변환)
        try:
            user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            logger.warning(f"잘못된 user_id 형식: {get_jwt_identity()}")
            return APIResponse.error("인증 정보가 올바르지 않습니다", code=401)
        
        # 보안: user_id 범위 검증
        if user_id <= 0:
            logger.warning(f"잘못된 user_id 값: {user_id}")
            return APIResponse.error("인증 정보가 올바르지 않습니다", code=401)
        
        user = User.query.get(user_id)
        
        if not user:
            logger.warning(f"사용자를 찾을 수 없음: user_id={user_id}")
            return APIResponse.error("사용자를 찾을 수 없습니다", code=404)
        
        if not user.is_active:
            logger.warning(f"비활성화된 사용자 접근 시도: user_id={user_id}")
            return APIResponse.error("계정이 비활성화되었습니다", code=403)
        
        # 페이지네이션 파라미터
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
        except (ValueError, TypeError):
            page = 1
            per_page = 20
        
        # 보안: 페이지네이션 파라미터 검증
        if not isinstance(page, int) or page < 1:
            page = 1
        if not isinstance(per_page, int) or per_page < 1:
            per_page = 20
        # 보안: 페이지 크기 제한
        if per_page > 100:
            per_page = 100
        
        # 보안: 본인의 기록만 조회 (user_id로 명시적 필터링)
        try:
            pagination = RevisionHistory.query.filter_by(user_id=user_id)\
                .order_by(RevisionHistory.created_at.desc())\
                .paginate(page=page, per_page=per_page, error_out=False)
            
            records = [record.to_dict() for record in pagination.items]
            
            return APIResponse.success(
                data={
                    'records': records,
                    'pagination': {
                        'page': pagination.page,
                        'per_page': pagination.per_page,
                        'total': pagination.total,
                        'pages': pagination.pages
                    }
                },
                message="수정 기록 조회 성공"
            )
        except Exception as db_error:
            logger.error(f"데이터베이스 조회 오류: {db_error}", exc_info=True)
            return APIResponse.server_error("수정 기록 조회 중 오류가 발생했습니다")
    
    except ValueError as e:
        logger.warning(f"입력값 검증 오류: {e}")
        return APIResponse.error("입력값이 올바르지 않습니다", code=400)
    except Exception as e:
        logger.error(f"수정 기록 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("수정 기록 조회 중 오류가 발생했습니다")


@user_bp.route('/revision-history', methods=['POST'])
@jwt_required()
@user_required
def create_revision_history():
    """
    수정 기록 생성 (LLM으로 생성된 수정 문장 저장)
    보안: JWT 인증 필요, 일반 사용자만 접근 가능, 본인만 생성 가능, 민감 정보는 저장하지 않음
    """
    try:
        # 보안: user_id는 정수로 변환 (안전한 변환)
        try:
            user_id = int(get_jwt_identity())
        except (ValueError, TypeError):
            logger.warning(f"잘못된 user_id 형식: {get_jwt_identity()}")
            return APIResponse.error("인증 정보가 올바르지 않습니다", code=401)
        
        # 보안: user_id 범위 검증
        if user_id <= 0:
            logger.warning(f"잘못된 user_id 값: {user_id}")
            return APIResponse.error("인증 정보가 올바르지 않습니다", code=401)
        
        user = User.query.get(user_id)
        
        if not user:
            logger.warning(f"사용자를 찾을 수 없음: user_id={user_id}")
            return APIResponse.error("사용자를 찾을 수 없습니다", code=404)
        
        if not user.is_active:
            logger.warning(f"비활성화된 사용자 접근 시도: user_id={user_id}")
            return APIResponse.error("계정이 비활성화되었습니다", code=403)
        
        data = request.get_json()
        if not data:
            return APIResponse.error("요청 데이터가 없습니다", code=400)
        
        revised_sentence = data.get('revised_sentence', '').strip()
        categories = data.get('categories', [])
        
        if not revised_sentence:
            return APIResponse.error("수정된 문장은 필수입니다", code=400)
        
        # 보안: 텍스트 길이 제한
        if len(revised_sentence) > 5000:
            return APIResponse.error("수정된 문장은 5000자 이하여야 합니다", code=400)
        
        # 보안: 빈 문자열 검증 (중복 제거 - 이미 위에서 검증함)
        revised_sentence = revised_sentence.strip()
        if not revised_sentence:
            return APIResponse.error("수정된 문장은 공백일 수 없습니다", code=400)
        
        # 보안: SQL 인젝션 패턴 검증
        sql_check, sql_error = validate_no_sql_injection(revised_sentence)
        if not sql_check:
            logger.warning(f"SQL 인젝션 시도 감지: user_id={user_id}, error={sql_error}")
            return APIResponse.error("잘못된 입력입니다", code=400)
        
        # 보안: 카테고리 검증
        if categories:
            if not isinstance(categories, list):
                return APIResponse.error("카테고리는 배열이어야 합니다", code=400)
            
            # 보안: 배열 크기 제한
            if len(categories) > 50:
                return APIResponse.error("카테고리는 최대 50개까지 가능합니다", code=400)
            
            # 보안: 카테고리 항목 검증 (문자열만 허용, 최대 길이 제한)
            for cat in categories:
                if not isinstance(cat, str):
                    return APIResponse.error("카테고리 항목은 문자열이어야 합니다", code=400)
                if len(cat) > 100:
                    return APIResponse.error("카테고리 항목은 100자 이하여야 합니다", code=400)
                # 보안: SQL 인젝션 패턴 검증
                sql_check, sql_error = validate_no_sql_injection(cat)
                if not sql_check:
                    logger.warning(f"SQL 인젝션 시도 감지 (카테고리): user_id={user_id}, category={cat}")
                    return APIResponse.error("잘못된 카테고리 입력입니다", code=400)
        
        # 수정 기록 생성
        try:
            record = RevisionHistory(
                user_id=user_id,
                revised_sentence=revised_sentence
            )
            
            if categories:
                record.set_categories(categories)
            
            db.session.add(record)
            db.session.commit()
            
            logger.info(f"수정 기록 생성 성공: user_id={user_id}, record_id={record.id}")
            
            return APIResponse.success(
                data={'record': record.to_dict()},
                message="수정 기록이 생성되었습니다",
                status_code=201
            )
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return APIResponse.server_error("수정 기록 생성 중 오류가 발생했습니다")
    
    except ValueError as e:
        logger.warning(f"입력값 검증 오류: {e}")
        db.session.rollback()
        return APIResponse.error("입력값이 올바르지 않습니다", code=400)
    except Exception as e:
        logger.error(f"수정 기록 생성 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("수정 기록 생성 중 오류가 발생했습니다")

