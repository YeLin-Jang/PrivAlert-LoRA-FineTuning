"""
사용자 마이페이지 관련 라우트
보안: CSRF 보호, 인증 필요, 시큐어 코딩 가이드 준수
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from app.utils.logger import get_logger
from app.models.user import User, UserFilteringSettings, RevisionHistory
from app.models.session import UserSession
from app.models.audit_log import AuditLog
from app.models.token import Token
from app.extensions.database import db
from app.utils.auth_utils import (
    validate_email, validate_password_strength, get_client_ip, get_user_agent
)
from app.utils.csrf_protection import validate_csrf_token
from app.utils.decorators import login_required
from app.utils.input_sanitizer import validate_no_sql_injection
import os

logger = get_logger(__name__)

user_bp = Blueprint('user', __name__)


@user_bp.route('/filtering-settings', methods=['GET'])
@login_required
def get_filtering_settings():
    """
    사용자 필터링 설정 조회
    보안: JWT 인증 필요, 일반 사용자만 접근 가능, 본인만 조회 가능
    """
    try:
        user = request.current_user
        
        if not user.is_active:
            logger.warning(f"비활성화된 사용자 접근 시도: user_id={user.id}")
            return jsonify({
                "success": False,
                "error": "계정이 비활성화되었습니다",
                "code": 403
            }), 403
        
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
            
            return jsonify({
                "success": True,
                "data": {'settings': settings.to_dict()},
                "message": "필터링 설정 조회 성공"
            }), 200
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return jsonify({
                "success": False,
                "error": "필터링 설정 조회 중 오류가 발생했습니다",
                "code": 500
            }), 500
    
    except Exception as e:
        logger.error(f"필터링 설정 조회 오류: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "필터링 설정 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/filtering-settings', methods=['PUT'])
@login_required
def update_filtering_settings():
    """
    사용자 필터링 설정 업데이트
    보안: JWT 인증 필요, 일반 사용자만 접근 가능, 본인만 수정 가능, 입력 검증
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        if not user.is_active:
            logger.warning(f"비활성화된 사용자 접근 시도: user_id={user.id}")
            return jsonify({
                "success": False,
                "error": "계정이 비활성화되었습니다",
                "code": 403
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "요청 데이터가 없습니다",
                "code": 400
            }), 400
        
        detection_options = data.get('detection_options', {})
        
        if not isinstance(detection_options, dict):
            return jsonify({
                "success": False,
                "error": "detection_options는 객체여야 합니다",
                "code": 400
            }), 400
        
        # 보안: 키 검증 (허용된 키만 허용)
        allowed_keys = {
            'face', 'fingerprint', 'phone', 'rrn', 'passport', 'ip_address',
            'email', 'account', 'school', 'workplace', 'name', 'address'
        }
        
        # 보안: 모든 키가 허용된 키인지 확인
        invalid_keys = [key for key in detection_options.keys() if key not in allowed_keys]
        if invalid_keys:
            logger.warning(f"허용되지 않은 필터링 옵션: {invalid_keys}, user_id={user.id}")
            return jsonify({
                "success": False,
                "error": "허용되지 않은 필터링 옵션이 포함되어 있습니다",
                "code": 400
            }), 400
        
        # 보안: 값 타입 검증 (boolean만 허용)
        for key, value in detection_options.items():
            if not isinstance(value, bool):
                logger.warning(f"잘못된 필터링 옵션 값 타입: {key}={value}, user_id={user.id}")
                return jsonify({
                    "success": False,
                    "error": f"필터링 옵션 '{key}'의 값은 boolean이어야 합니다",
                    "code": 400
                }), 400
        
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
            
            return jsonify({
                "success": True,
                "data": {'settings': settings.to_dict()},
                "message": "필터링 설정이 업데이트되었습니다"
            }), 200
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return jsonify({
                "success": False,
                "error": "필터링 설정 업데이트 중 오류가 발생했습니다",
                "code": 500
            }), 500
    
    except Exception as e:
        logger.error(f"필터링 설정 업데이트 오류: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "필터링 설정 업데이트 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/revision-history', methods=['GET'])
@login_required
def get_revision_history():
    """
    사용자 수정 기록 조회
    보안: JWT 인증 필요, 일반 사용자만 접근 가능, 본인만 조회 가능, 민감 정보 제외
    """
    try:
        user = request.current_user
        
        if not user.is_active:
            logger.warning(f"비활성화된 사용자 접근 시도: user_id={user.id}")
            return jsonify({
                "success": False,
                "error": "계정이 비활성화되었습니다",
                "code": 403
            }), 403
        
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
            pagination = RevisionHistory.query.filter_by(user_id=user.id)\
                .order_by(RevisionHistory.created_at.desc())\
                .paginate(page=page, per_page=per_page, error_out=False)
            
            records = [record.to_dict() for record in pagination.items]
            
            return jsonify({
                "success": True,
                "data": {
                    'records': records,
                    'pagination': {
                        'page': pagination.page,
                        'per_page': pagination.per_page,
                        'total': pagination.total,
                        'pages': pagination.pages
                    }
                },
                "message": "수정 기록 조회 성공"
            }), 200
        except Exception as db_error:
            logger.error(f"데이터베이스 조회 오류: {db_error}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "수정 기록 조회 중 오류가 발생했습니다",
                "code": 500
            }), 500
    
    except Exception as e:
        logger.error(f"수정 기록 조회 오류: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "수정 기록 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/revision-history', methods=['POST'])
@login_required
def create_revision_history():
    """
    수정 기록 생성 (LLM으로 생성된 수정 문장 저장)
    보안: JWT 인증 필요, 일반 사용자만 접근 가능, 본인만 생성 가능, 민감 정보는 저장하지 않음
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        if not user.is_active:
            logger.warning(f"비활성화된 사용자 접근 시도: user_id={user.id}")
            return jsonify({
                "success": False,
                "error": "계정이 비활성화되었습니다",
                "code": 403
            }), 403
        
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "요청 데이터가 없습니다",
                "code": 400
            }), 400
        
        revised_sentence = data.get('revised_sentence', '').strip()
        categories = data.get('categories', [])
        
        if not revised_sentence:
            return jsonify({
                "success": False,
                "error": "수정된 문장은 필수입니다",
                "code": 400
            }), 400
        
        # 보안: 텍스트 길이 제한
        if len(revised_sentence) > 5000:
            return jsonify({
                "success": False,
                "error": "수정된 문장은 5000자 이하여야 합니다",
                "code": 400
            }), 400
        
        # 보안: 빈 문자열 검증
        revised_sentence = revised_sentence.strip()
        if not revised_sentence:
            return jsonify({
                "success": False,
                "error": "수정된 문장은 공백일 수 없습니다",
                "code": 400
            }), 400
        
        # 보안: SQL 인젝션 패턴 검증
        sql_check, sql_error = validate_no_sql_injection(revised_sentence)
        if not sql_check:
            logger.warning(f"SQL 인젝션 시도 감지: user_id={user.id}, error={sql_error}")
            return jsonify({
                "success": False,
                "error": "잘못된 입력입니다",
                "code": 400
            }), 400
        
        # 보안: 카테고리 검증
        if categories:
            if not isinstance(categories, list):
                return jsonify({
                    "success": False,
                    "error": "카테고리는 배열이어야 합니다",
                    "code": 400
                }), 400
            
            # 보안: 배열 크기 제한
            if len(categories) > 50:
                return jsonify({
                    "success": False,
                    "error": "카테고리는 최대 50개까지 가능합니다",
                    "code": 400
                }), 400
            
            # 보안: 카테고리 항목 검증 (문자열만 허용, 최대 길이 제한)
            for cat in categories:
                if not isinstance(cat, str):
                    return jsonify({
                        "success": False,
                        "error": "카테고리 항목은 문자열이어야 합니다",
                        "code": 400
                    }), 400
                if len(cat) > 100:
                    return jsonify({
                        "success": False,
                        "error": "카테고리 항목은 100자 이하여야 합니다",
                        "code": 400
                    }), 400
                # 보안: SQL 인젝션 패턴 검증
                sql_check, sql_error = validate_no_sql_injection(cat)
                if not sql_check:
                    logger.warning(f"SQL 인젝션 시도 감지 (카테고리): user_id={user.id}, category={cat}")
                    return jsonify({
                        "success": False,
                        "error": "잘못된 카테고리 입력입니다",
                        "code": 400
                    }), 400
        
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
            
            return jsonify({
                "success": True,
                "data": {'record': record.to_dict()},
                "message": "수정 기록이 생성되었습니다"
            }), 201
        except Exception as db_error:
            logger.error(f"데이터베이스 오류: {db_error}", exc_info=True)
            db.session.rollback()
            return jsonify({
                "success": False,
                "error": "수정 기록 생성 중 오류가 발생했습니다",
                "code": 500
            }), 500
    
    except Exception as e:
        logger.error(f"수정 기록 생성 오류: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({
            "success": False,
            "error": "수정 기록 생성 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/me', methods=['GET'])
@login_required
def get_profile():
    """
    현재 사용자 정보 조회
    GET /api/v1/user/me
    보안: CSRF 토큰도 함께 반환하여 프론트엔드에서 토큰 갱신 가능
    """
    try:
        user = request.current_user
        user_id_str = str(user.id)
        
        # CSRF 토큰 생성 (프론트엔드에서 토큰 갱신 가능하도록)
        from app.utils.csrf_protection import generate_csrf_token
        csrf_token = generate_csrf_token(user_id_str)
        
        return jsonify({
            "success": True,
            "data": {
                **user.to_dict(),
                "csrf_token": csrf_token
            }
        }), 200
        
    except Exception as e:
        logger.error(f"프로필 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "프로필 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/me', methods=['PATCH'])
@login_required
def update_profile():
    """
    프로필 수정
    PATCH /api/v1/user/me
    Body: { "email": "..." (선택) }
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        data = request.get_json()
        new_email = data.get('email', '').strip().lower() if data else None
        
        # 이메일 변경 시
        if new_email and new_email != user.email:
            # 이메일 형식 검증
            if not validate_email(new_email):
                return jsonify({
                    "success": False,
                    "error": "올바른 이메일 형식이 아닙니다",
                    "code": 400
                }), 400
            
            # 중복 확인
            if User.find_by_email(new_email):
                return jsonify({
                    "success": False,
                    "error": "이미 사용 중인 이메일입니다",
                    "code": 409
                }), 409
            
            # 이메일 변경 및 재검증 필요
            user.email = new_email
            user.email_verified = False
            user.email_verified_at = None
            
            # 새 이메일 검증 토큰 생성
            token_plaintext, token = Token.create_token(
                user_id=user.id,
                token_type='email_verification',
                expiry_hours=24
            )
            
            # 이메일 변경 인증 메일 전송
            verification_url = f"{request.host_url.rstrip('/')}/api/v1/auth/verify?token={token_plaintext}"
            try:
                from app.services.email_service import EmailService
                email_sent = EmailService.send_verification_email(new_email, token_plaintext, verification_url)
                if email_sent:
                    logger.info(f"이메일 변경 인증 메일 전송 성공: {new_email}")
                else:
                    logger.warning(f"이메일 변경 인증 메일 전송 실패: {new_email}")
            except Exception as e:
                logger.error(f"이메일 변경 인증 메일 전송 중 오류: {e}", exc_info=True)
            
            db.session.commit()
            
            logger.info(f"이메일 변경: {user.email}")
            
            # 감사 로그
            AuditLog.log_event(
                user_id=user.id,
                event_type='email_changed',
                event_description='이메일 주소 변경',
                ip_address=get_client_ip(),
                user_agent=get_user_agent(),
                success=True
            )
            
            return jsonify({
                "success": True,
                "message": "이메일이 변경되었습니다. 새 이메일을 확인하여 계정을 활성화하세요",
                "data": {
                    "user": user.to_dict(),
                    "verification_token": token_plaintext if os.getenv("FLASK_ENV") == "development" else None
                }
            }), 200
        
        # 프로필 업데이트 없음
        return jsonify({
            "success": True,
            "message": "변경사항이 없습니다",
            "data": user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"프로필 수정 오류: {e}")
        return jsonify({
            "success": False,
            "error": "프로필 수정 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/password-change', methods=['POST'])
@login_required
def change_password():
    """
    비밀번호 변경 (현재 비밀번호 확인 필요)
    POST /api/v1/user/password-change
    Body: { "currentPassword": "...", "newPassword": "...", "csrf_token": "..." }
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        data = request.get_json()
        current_password = data.get('currentPassword', '')
        new_password = data.get('newPassword', '')
        
        if not current_password or not new_password:
            return jsonify({
                "success": False,
                "error": "현재 비밀번호와 새 비밀번호를 입력하세요",
                "code": 400
            }), 400
        
        # 현재 비밀번호 확인
        if not user.check_password(current_password):
            ip = get_client_ip()
            # 보안: 비밀번호 변경 실패 로그 기록
            logger.warning(f"비밀번호 변경 실패 (현재 비밀번호 불일치): user_id={user.id}, ip={ip}")
            return jsonify({
                "success": False,
                "error": "현재 비밀번호가 올바르지 않습니다",
                "code": 401
            }), 401
        
        # 새 비밀번호 강도 검증
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg,
                "code": 400
            }), 400
        
        # 새 비밀번호가 현재 비밀번호와 같은지 확인
        if current_password == new_password:
            return jsonify({
                "success": False,
                "error": "새 비밀번호는 현재 비밀번호와 달라야 합니다",
                "code": 400
            }), 400
        
        # 비밀번호 변경
        user.set_password(new_password)
        
        # 모든 세션 무효화 (보안)
        session_id = request.cookies.get('session_id')
        UserSession.revoke_all_user_sessions(user.id, except_session_id=session_id)
        
        db.session.commit()
        
        ip = get_client_ip()
        # 보안: 비밀번호 변경 성공 로그 기록
        logger.warning(f"비밀번호 변경 성공: user_id={user.id}, email={user.email[:3] if user.email else 'unknown'}..., ip={ip}")
        
        # 감사 로그
        AuditLog.log_password_change(
            user_id=user.id,
            ip_address=ip,
            user_agent=get_user_agent()
        )
        
        return jsonify({
            "success": True,
            "message": "비밀번호가 성공적으로 변경되었습니다"
        }), 200
        
    except ValueError as e:
        logger.warning(f"비밀번호 변경 실패: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "code": 400
        }), 400
    except Exception as e:
        logger.error(f"비밀번호 변경 오류: {e}")
        return jsonify({
            "success": False,
            "error": "비밀번호 변경 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/sessions', methods=['GET'])
@login_required
def get_sessions():
    """
    세션 목록 조회
    GET /api/v1/user/sessions
    """
    try:
        user = request.current_user
        current_session_id = request.cookies.get('session_id')
        
        # 활성 세션 조회
        sessions = UserSession.query.filter_by(
            user_id=user.id,
            is_active=True
        ).order_by(UserSession.last_activity.desc()).all()
        
        # 만료된 세션 제거
        active_sessions = []
        for session in sessions:
            if session.is_expired():
                session.revoke()
            else:
                active_sessions.append(session)
        
        db.session.commit()
        
        return jsonify({
            "success": True,
            "data": {
                "sessions": [s.to_dict() for s in active_sessions],
                "current_session_id": current_session_id
            }
        }), 200
        
    except Exception as e:
        logger.error(f"세션 목록 조회 오류: {e}")
        return jsonify({
            "success": False,
            "error": "세션 목록 조회 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/sessions/<session_id>', methods=['DELETE'])
@login_required
def revoke_session(session_id):
    """
    특정 세션 무효화
    DELETE /api/v1/user/sessions/<session_id>
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        # 세션 조회 및 소유권 확인
        session = UserSession.find_by_session_id(session_id)
        
        if not session or session.user_id != user.id:
            return jsonify({
                "success": False,
                "error": "세션을 찾을 수 없습니다",
                "code": 404
            }), 404
        
        session.revoke()
        
        logger.info(f"세션 무효화: {session_id}")
        
        # 감사 로그
        AuditLog.log_event(
            user_id=user.id,
            event_type='session_revoked',
            event_description='세션 무효화',
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            success=True,
            extra_data={"session_id": session_id}
        )
        
        return jsonify({
            "success": True,
            "message": "세션이 무효화되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"세션 무효화 오류: {e}")
        return jsonify({
            "success": False,
            "error": "세션 무효화 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/sessions/revoke-all', methods=['POST'])
@login_required
def revoke_all_sessions():
    """
    모든 세션 무효화 (현재 세션 제외)
    POST /api/v1/user/sessions/revoke-all
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        current_session_id = request.cookies.get('session_id')
        
        # 모든 세션 무효화 (현재 세션 제외)
        UserSession.revoke_all_user_sessions(user.id, except_session_id=current_session_id)
        
        logger.info(f"모든 세션 무효화: {user.email}")
        
        # 감사 로그
        AuditLog.log_event(
            user_id=user.id,
            event_type='all_sessions_revoked',
            event_description='모든 세션 무효화',
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            success=True
        )
        
        return jsonify({
            "success": True,
            "message": "모든 세션이 무효화되었습니다"
        }), 200
        
    except Exception as e:
        logger.error(f"세션 전체 무효화 오류: {e}")
        return jsonify({
            "success": False,
            "error": "세션 무효화 중 오류가 발생했습니다",
            "code": 500
        }), 500


@user_bp.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """
    계정 삭제 요청 (7일 유예)
    POST /api/v1/user/delete-account
    Body: { "password": "...", "csrf_token": "..." }
    """
    try:
        # CSRF 검증
        csrf_token = request.headers.get('X-CSRF-Token') or (request.json.get('csrf_token') if request.is_json else None)
        if not csrf_token:
            return jsonify({
                "success": False,
                "error": "CSRF 토큰이 필요합니다",
                "code": 403
            }), 403
        
        user = request.current_user
        user_id_str = str(user.id)
        
        is_valid, error_msg = validate_csrf_token(user_id_str, csrf_token)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg or "CSRF 토큰이 유효하지 않습니다",
                "code": 403
            }), 403
        
        data = request.get_json()
        password = data.get('password', '')
        
        # 비밀번호 확인
        if not user.check_password(password):
            return jsonify({
                "success": False,
                "error": "비밀번호가 올바르지 않습니다",
                "code": 401
            }), 401
        
        # 계정 삭제 요청
        user.request_deletion()
        
        # 감사 로그
        ip = get_client_ip()
        AuditLog.log_account_deletion(
            user_id=user.id,
            ip_address=ip,
            user_agent=get_user_agent()
        )
        # 보안: 계정 삭제 요청 로그 기록
        logger.warning(f"계정 삭제 요청: user_id={user.id}, email={user.email[:3] if user.email else 'unknown'}..., ip={ip}")
        
        return jsonify({
            "success": True,
            "message": "계정 삭제가 요청되었습니다. 7일 후 계정이 영구적으로 삭제됩니다"
        }), 200
        
    except Exception as e:
        logger.error(f"계정 삭제 요청 오류: {e}")
        return jsonify({
            "success": False,
            "error": "계정 삭제 요청 중 오류가 발생했습니다",
            "code": 500
        }), 500

