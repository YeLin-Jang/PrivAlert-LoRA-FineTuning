"""
더미 사용자 데이터 API 라우트 (인증 없이 접근 가능)
보안: 더미 데이터만 반환, 실제 사용자 데이터 접근 불가
"""
from flask import Blueprint, request
from app.extensions.database import db
from app.models.user import User, UserFilteringSettings, RevisionHistory
from app.utils.logger import get_logger
from app.utils.api_utils import APIResponse
from app.utils.input_sanitizer import validate_no_sql_injection
from datetime import datetime

logger = get_logger(__name__)

dummy_user_bp = Blueprint('dummy_user', __name__)

# 더미 사용자 이메일 (하드코딩, 보안을 위해)
DUMMY_EMAIL = 'demo@privalert.com'


def get_dummy_user():
    """더미 사용자 조회"""
    user = User.find_by_email(DUMMY_EMAIL)
    if not user:
        logger.error(f"더미 사용자를 찾을 수 없습니다: {DUMMY_EMAIL}")
        return None
    return user


@dummy_user_bp.route('/demo/user', methods=['GET'])
def get_demo_user_info():
    """
    더미 사용자 정보 조회
    보안: 더미 사용자만 반환, 실제 사용자 데이터 접근 불가
    """
    try:
        dummy_user = get_dummy_user()
        if not dummy_user:
            return APIResponse.error("더미 사용자 데이터를 찾을 수 없습니다", code=404)
        
        return APIResponse.success(
            data={'user': dummy_user.to_dict()},
            message="더미 사용자 정보 조회 성공"
        )
    
    except Exception as e:
        logger.error(f"더미 사용자 정보 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("더미 사용자 정보 조회 중 오류가 발생했습니다")


@dummy_user_bp.route('/demo/filtering-settings', methods=['GET'])
def get_demo_filtering_settings():
    """
    더미 사용자 필터링 설정 조회
    보안: 더미 사용자만 조회 가능, 입력 검증
    """
    try:
        dummy_user = get_dummy_user()
        if not dummy_user:
            return APIResponse.error("더미 사용자 데이터를 찾을 수 없습니다", code=404)
        
        # 필터링 설정 조회
        try:
            settings = dummy_user.filtering_settings
            if not settings:
                # 설정이 없으면 기본값으로 생성
                settings = UserFilteringSettings(user_id=dummy_user.id)
                settings.set_detection_options({})
                db.session.add(settings)
                db.session.commit()
                logger.info(f"더미 사용자 필터링 설정 생성: user_id={dummy_user.id}")
            
            return APIResponse.success(
                data={'settings': settings.to_dict()},
                message="필터링 설정 조회 성공"
            )
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return APIResponse.server_error("필터링 설정 조회 중 오류가 발생했습니다")
    
    except Exception as e:
        logger.error(f"더미 필터링 설정 조회 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("필터링 설정 조회 중 오류가 발생했습니다")


@dummy_user_bp.route('/demo/filtering-settings', methods=['PUT'])
def update_demo_filtering_settings():
    """
    더미 사용자 필터링 설정 업데이트
    보안: 더미 사용자만 수정 가능, 입력 검증, SQL 인젝션 방지
    """
    try:
        dummy_user = get_dummy_user()
        if not dummy_user:
            return APIResponse.error("더미 사용자 데이터를 찾을 수 없습니다", code=404)
        
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
            logger.warning(f"허용되지 않은 필터링 옵션: {invalid_keys}, user_id={dummy_user.id}")
            return APIResponse.error("허용되지 않은 필터링 옵션이 포함되어 있습니다", code=400)
        
        # 보안: 값 타입 검증 (boolean만 허용)
        for key, value in detection_options.items():
            if not isinstance(value, bool):
                logger.warning(f"잘못된 필터링 옵션 값 타입: {key}={value}, user_id={dummy_user.id}")
                return APIResponse.error(f"필터링 옵션 '{key}'의 값은 boolean이어야 합니다", code=400)
        
        # 필터링 설정 조회 또는 생성
        try:
            settings = dummy_user.filtering_settings
            if not settings:
                settings = UserFilteringSettings(user_id=dummy_user.id)
                db.session.add(settings)
            
            # 설정 업데이트
            settings.set_detection_options(detection_options)
            settings.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"더미 사용자 필터링 설정 업데이트 성공: user_id={dummy_user.id}")
            
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
        logger.error(f"더미 필터링 설정 업데이트 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("필터링 설정 업데이트 중 오류가 발생했습니다")


@dummy_user_bp.route('/demo/revision-history', methods=['GET'])
def get_demo_revision_history():
    """
    더미 사용자 수정 기록 조회
    보안: 더미 사용자만 조회 가능, 페이지네이션 파라미터 검증
    """
    try:
        dummy_user = get_dummy_user()
        if not dummy_user:
            return APIResponse.error("더미 사용자 데이터를 찾을 수 없습니다", code=404)
        
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
        
        # 보안: 더미 사용자의 기록만 조회
        try:
            pagination = RevisionHistory.query.filter_by(user_id=dummy_user.id)\
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
        logger.error(f"더미 수정 기록 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("수정 기록 조회 중 오류가 발생했습니다")


@dummy_user_bp.route('/demo/revision-history', methods=['POST'])
def create_demo_revision_history():
    """
    더미 사용자 수정 기록 생성 (LLM으로 생성된 수정 문장 저장)
    보안: 더미 사용자만 생성 가능, 입력 검증, SQL 인젝션 방지, 민감 정보는 저장하지 않음
    """
    try:
        dummy_user = get_dummy_user()
        if not dummy_user:
            return APIResponse.error("더미 사용자 데이터를 찾을 수 없습니다", code=404)
        
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
        
        # 보안: 빈 문자열 검증
        if not revised_sentence:
            return APIResponse.error("수정된 문장은 공백일 수 없습니다", code=400)
        
        # 보안: SQL 인젝션 패턴 검증
        from app.utils.input_sanitizer import validate_no_sql_injection
        sql_check, sql_error = validate_no_sql_injection(revised_sentence)
        if not sql_check:
            logger.warning(f"SQL 인젝션 시도 감지: user_id={dummy_user.id}")
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
                    logger.warning(f"SQL 인젝션 시도 감지 (카테고리): user_id={dummy_user.id}, category={cat}")
                    return APIResponse.error("잘못된 카테고리 입력입니다", code=400)
        
        # 수정 기록 생성
        try:
            record = RevisionHistory(
                user_id=dummy_user.id,
                revised_sentence=revised_sentence
            )
            
            if categories:
                record.set_categories(categories)
            
            db.session.add(record)
            db.session.commit()
            
            logger.info(f"더미 사용자 수정 기록 생성 성공: user_id={dummy_user.id}, record_id={record.id}")
            
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
        logger.error(f"더미 수정 기록 생성 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("수정 기록 생성 중 오류가 발생했습니다")


@dummy_user_bp.route('/demo/verify-password', methods=['POST'])
def verify_demo_password():
    """
    더미 사용자 기존 비밀번호 확인
    보안: 비밀번호 검증만 수행, Rate Limiting
    """
    try:
        dummy_user = get_dummy_user()
        if not dummy_user:
            return APIResponse.error("더미 사용자 데이터를 찾을 수 없습니다", code=404)
        
        data = request.get_json()
        if not data:
            return APIResponse.error("요청 데이터가 없습니다", code=400)
        
        current_password = data.get('current_password', '')
        
        # 보안: 필수 필드 검증
        if not current_password:
            return APIResponse.error("기존 비밀번호는 필수입니다", code=400)
        
        # 보안: 기존 비밀번호 확인
        if not dummy_user.check_password(current_password):
            logger.warning(f"더미 사용자 비밀번호 확인 실패: 기존 비밀번호 불일치 (user_id={dummy_user.id})")
            return APIResponse.error("기존 비밀번호가 올바르지 않습니다", code=401)
        
        logger.info(f"더미 사용자 비밀번호 확인 성공: user_id={dummy_user.id}")
        
        return APIResponse.success(
            message="기존 비밀번호 확인 성공"
        )
    
    except Exception as e:
        logger.error(f"더미 사용자 비밀번호 확인 오류: {e}", exc_info=True)
        return APIResponse.server_error("비밀번호 확인 중 오류가 발생했습니다")


@dummy_user_bp.route('/demo/change-password', methods=['PUT'])
def change_demo_password():
    """
    더미 사용자 비밀번호 변경
    보안: 기존 비밀번호 확인, 새 비밀번호 검증, 해싱, Rate Limiting, 로깅
    """
    try:
        dummy_user = get_dummy_user()
        if not dummy_user:
            return APIResponse.error("더미 사용자 데이터를 찾을 수 없습니다", code=404)
        
        data = request.get_json()
        if not data:
            return APIResponse.error("요청 데이터가 없습니다", code=400)
        
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')
        
        # 보안: 필수 필드 검증
        if not current_password or not new_password:
            return APIResponse.error("기존 비밀번호와 새 비밀번호는 필수입니다", code=400)
        
        # 보안: 비밀번호 길이 검증
        if len(new_password) < 8:
            return APIResponse.error("새 비밀번호는 최소 8자 이상이어야 합니다", code=400)
        
        if len(new_password) > 128:
            return APIResponse.error("새 비밀번호는 128자 이하여야 합니다", code=400)
        
        # 보안: 비밀번호 복잡도 검증 (영문, 숫자, 특수문자 중 2가지 이상)
        import re
        has_letter = bool(re.search(r'[a-zA-Z]', new_password))
        has_number = bool(re.search(r'[0-9]', new_password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password))
        complexity_count = sum([has_letter, has_number, has_special])
        
        if complexity_count < 2:
            return APIResponse.error("새 비밀번호는 영문, 숫자, 특수문자 중 2가지 이상을 포함해야 합니다", code=400)
        
        # 보안: 기존 비밀번호와 동일한지 확인
        if current_password == new_password:
            return APIResponse.error("새 비밀번호는 기존 비밀번호와 달라야 합니다", code=400)
        
        # 보안: 기존 비밀번호 확인
        if not dummy_user.check_password(current_password):
            logger.warning(f"더미 사용자 비밀번호 변경 실패: 기존 비밀번호 불일치 (user_id={dummy_user.id})")
            return APIResponse.error("기존 비밀번호가 올바르지 않습니다", code=401)
        
        # 보안: SQL 인젝션 패턴 검증 (비밀번호는 일반적으로 SQL 인젝션에 취약하지 않지만 방어)
        sql_check, sql_error = validate_no_sql_injection(new_password)
        if not sql_check:
            logger.warning(f"SQL 인젝션 시도 감지: user_id={dummy_user.id}")
            return APIResponse.error("잘못된 입력입니다", code=400)
        
        # 보안: 비밀번호 변경 (해시화되어 저장)
        dummy_user.set_password(new_password)
        dummy_user.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"더미 사용자 비밀번호 변경 성공: user_id={dummy_user.id}")
        
        return APIResponse.success(
            message="비밀번호가 성공적으로 변경되었습니다"
        )
    
    except ValueError as e:
        # 비밀번호 검증 오류 (예: 길이 부족)
        logger.warning(f"더미 사용자 비밀번호 변경 실패: {e} (user_id={dummy_user.id if 'dummy_user' in locals() else 'unknown'})")
        db.session.rollback()
        return APIResponse.error(str(e), code=400)
    
    except Exception as e:
        logger.error(f"더미 사용자 비밀번호 변경 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("비밀번호 변경 중 오류가 발생했습니다")

