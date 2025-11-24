"""사용자 수정 기록 라우트"""
from flask import Blueprint, request
from app.utils.logger import get_logger
from app.models.user import User, RevisionHistory
from app.extensions.database import db
from app.utils.decorators import login_required
from app.utils.input_sanitizer import validate_no_sql_injection
from app.utils.api_utils import APIResponse
from app.utils.user_route_helpers import (
    validate_csrf_from_session, check_user_active, validate_json_request
)

logger = get_logger(__name__)

user_history_bp = Blueprint('user_history', __name__)


@user_history_bp.route('/revision-history', methods=['GET'])
@login_required
def get_revision_history():
    """사용자 수정 기록 조회"""
    try:
        user = request.current_user
        
        # 사용자 활성화 확인
        is_active, error = check_user_active(user)
        if not is_active:
            return error
        
        # 페이지네이션 파라미터
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
        except (ValueError, TypeError):
            page = 1
            per_page = 20
        
        if not isinstance(page, int) or page < 1:
            page = 1
        if not isinstance(per_page, int) or per_page < 1:
            per_page = 20
        if per_page > 100:
            per_page = 100
        try:
            pagination = RevisionHistory.query.filter_by(user_id=user.id)\
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
    
    except Exception as e:
        logger.error(f"수정 기록 조회 오류: {e}", exc_info=True)
        return APIResponse.server_error("수정 기록 조회 중 오류가 발생했습니다")


@user_history_bp.route('/revision-history', methods=['POST'])
@login_required
def create_revision_history():
    """수정 기록 생성 (LLM으로 생성된 수정 문장 저장)"""
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
        
        revised_sentence = data.get('revised_sentence', '').strip()
        categories = data.get('categories', [])
        
        if not revised_sentence:
            return APIResponse.error("수정된 문장은 필수입니다", code=400)
        
        if len(revised_sentence) > 5000:
            return APIResponse.error("수정된 문장은 5000자 이하여야 합니다", code=400)
        
        revised_sentence = revised_sentence.strip()
        if not revised_sentence:
            return APIResponse.error("수정된 문장은 공백일 수 없습니다", code=400)
        
        sql_check, sql_error = validate_no_sql_injection(revised_sentence)
        if not sql_check:
            logger.warning(f"SQL 인젝션 시도 감지: user_id={user.id}, error={sql_error}")
            return APIResponse.error("잘못된 입력입니다", code=400)
        
        if categories:
            if not isinstance(categories, list):
                return APIResponse.error("카테고리는 배열이어야 합니다", code=400)
            
            if len(categories) > 50:
                return APIResponse.error("카테고리는 최대 50개까지 가능합니다", code=400)
            
            for cat in categories:
                if not isinstance(cat, str):
                    return APIResponse.error("카테고리 항목은 문자열이어야 합니다", code=400)
                if len(cat) > 100:
                    return APIResponse.error("카테고리 항목은 100자 이하여야 합니다", code=400)
                sql_check, sql_error = validate_no_sql_injection(cat)
                if not sql_check:
                    logger.warning(f"SQL 인젝션 시도 감지 (카테고리): user_id={user.id}, category={cat}")
                    return APIResponse.error("잘못된 카테고리 입력입니다", code=400)
        
        # 수정 기록 생성
        try:
            record = RevisionHistory(
                user_id=user.id,
                revised_sentence=revised_sentence
            )
            
            if categories:
                record.set_categories(categories)
            
            db.session.add(record)
            db.session.commit()
            
            logger.info(f"수정 기록 생성 성공: user_id={user.id}, record_id={record.id}")
            
            return APIResponse.success(
                data={'record': record.to_dict()},
                message="수정 기록이 생성되었습니다",
                status_code=201
            )
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return APIResponse.server_error("수정 기록 생성 중 오류가 발생했습니다")
    
    except Exception as e:
        logger.error(f"수정 기록 생성 오류: {e}", exc_info=True)
        db.session.rollback()
        return APIResponse.server_error("수정 기록 생성 중 오류가 발생했습니다")

