"""
사용자 인증 라우트 (HTTP 전용 환경)
보안: CSRF 보호, Rate limiting, 세션 관리
"""
from flask import Blueprint, request, jsonify, make_response, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, timedelta
from app.utils.logger import get_logger
from app.models.user import User
from app.models.token import Token
from app.models.session import UserSession
from app.models.audit_log import AuditLog
from app.extensions.database import db
from app.utils.auth_utils import (
    validate_email, validate_password_strength, get_client_ip, get_user_agent
)
from app.utils.csrf_protection import generate_csrf_token, validate_csrf_token
import os
import json

logger = get_logger(__name__)

auth_bp = Blueprint('auth', __name__)

# Rate Limiter는 Flask 앱에서 초기화됨
def get_limiter():
    """Rate Limiter 인스턴스 가져오기"""
    return Limiter(
        app=current_app._get_current_object(),
        key_func=get_remote_address,
        default_limits=["1000 per hour"]
    )


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    회원가입
    POST /api/v1/auth/signup
    Body: { "email": "...", "password": "..." }
    보안: Rate limiting (app/__init__.py에서 적용), 입력 검증, XSS 방지
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "요청 데이터가 필요합니다",
                "code": 400
            }), 400
        
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        nickname = data.get('nickname', '').strip()
        
        # 입력 검증
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "이메일과 비밀번호를 입력하세요",
                "code": 400
            }), 400
        
        # 별명 검증
        if not nickname or len(nickname.strip()) < 2:
            return jsonify({
                "success": False,
                "error": "별명은 최소 2자 이상이어야 합니다",
                "code": 400
            }), 400
        
        if len(nickname.strip()) > 20:
            return jsonify({
                "success": False,
                "error": "별명은 최대 20자까지 가능합니다",
                "code": 400
            }), 400
        
        # 이메일 형식 검증
        if not validate_email(email):
            return jsonify({
                "success": False,
                "error": "올바른 이메일 형식이 아닙니다",
                "code": 400
            }), 400
        
        # 비밀번호 강도 검증
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg,
                "code": 400
            }), 400
        
        # 중복 이메일 확인 (인증 완료된 사용자만 확인)
        existing_user = User.find_by_email(email)
        if existing_user and existing_user.email_verified:
            return jsonify({
                "success": False,
                "error": "이미 등록된 이메일입니다",
                "code": 409
            }), 409
        
        # 비밀번호 해시 생성 (나중에 사용자 생성 시 사용)
        user = User.create_user(email, password)
        password_hash = user.password_hash  # 해시된 비밀번호 저장
        
        # 사용자는 아직 DB에 저장하지 않음 (이메일 인증 완료 후 저장)
        # 대신 토큰에 정보를 저장
        token_metadata = {
            'email': email,
            'password_hash': password_hash,
            'nickname': nickname.strip()  # 별명 저장
        }
        
        # 이메일 검증 토큰 생성 (user_id 없이, metadata에 정보 저장)
        token_plaintext, token = Token.create_token(
            user_id=None,  # 이메일 인증 완료 전까지는 user_id 없음
            token_type='email_verification',
            expiry_hours=24,
            metadata=token_metadata
        )
        
        # 인증 코드 생성 및 저장
        from app.services.verification_service import VerificationService
        verification_code = VerificationService.generate_code(email, token.id)
        
        # SMTP 이메일 전송 (실무: 실제 이메일로만 전송, 코드는 절대 응답에 포함하지 않음)
        try:
            from app.services.email_service import EmailService
            email_sent = EmailService.send_verification_code(email, verification_code)
            
            if not email_sent:
                # SMTP 전송 실패 시 오류 반환
                logger.error(f"이메일 전송 실패: {email}")
                return jsonify({
                    "success": False,
                    "error": "이메일 전송에 실패했습니다. SMTP 설정을 확인하세요.",
                    "code": 500
                }), 500
            else:
                logger.info(f"이메일 인증 코드 전송 성공: {email}")
        except Exception as e:
            logger.error(f"이메일 전송 중 오류: {e}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "이메일 전송 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                "code": 500
            }), 500
        
        ip = get_client_ip()
        # 보안: 회원가입 요청 로그 기록 (아직 계정 생성 안됨)
        logger.info(f"회원가입 요청: email={email[:3]}..., ip={ip}, 인증 코드 생성 및 이메일 전송 완료")
        
        # 실무: 인증 코드는 절대 응답에 포함하지 않음 (보안)
        return jsonify({
            "success": True,
            "message": "회원가입 요청이 접수되었습니다. 이메일을 확인하여 인증 코드를 입력해주세요.",
            "data": {
                "email": email
            }
        }), 201
        
    except ValueError as e:
        logger.warning(f"회원가입 실패: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "code": 400
        }), 400
    except Exception as e:
        # 보안: 에러 메시지 최소화 (상세 정보는 로그에만 기록)
        logger.error(f"회원가입 오류: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "회원가입 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/verify', methods=['POST'])
def verify_email():
    """
    이메일 검증 (인증 코드 입력)
    POST /api/v1/auth/verify
    Body: { "email": "...", "code": "..." }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "success": False,
                "error": "요청 데이터가 필요합니다",
                "code": 400
            }), 400
        
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()
        
        if not email or not code:
            return jsonify({
                "success": False,
                "error": "이메일과 인증 코드를 입력하세요",
                "code": 400
            }), 400
        
        # 인증 코드 검증
        from app.services.verification_service import VerificationService
        token_id = VerificationService.verify_code(email, code)
        
        if not token_id:
            return jsonify({
                "success": False,
                "error": "인증 코드가 올바르지 않거나 만료되었습니다",
                "code": 400
            }), 400
        
        # 토큰 조회
        token = Token.query.get(token_id)
        
        if not token:
            return jsonify({
                "success": False,
                "error": "유효하지 않은 토큰입니다",
                "code": 400
            }), 400
        
        if token.used:
            return jsonify({
                "success": False,
                "error": "이미 사용된 인증 코드입니다",
                "code": 410
            }), 410
        
        # 이메일 인증 토큰에서 회원가입 정보 추출
        if token.token_type == 'email_verification':
            # token_metadata에서 이메일과 비밀번호 해시 추출
            if not token.token_metadata:
                return jsonify({
                    "success": False,
                    "error": "토큰 정보가 유효하지 않습니다",
                    "code": 400
                }), 400
            
            try:
                # 토큰 metadata 복호화 (보안)
                # Token은 이미 파일 상단에서 import됨
                metadata = Token._decrypt_metadata(token.token_metadata)
                if not metadata:
                    raise ValueError("metadata 복호화 실패")
                email = metadata.get('email')
                password_hash = metadata.get('password_hash')
                nickname = metadata.get('nickname', '').strip()
                
                if not email or not password_hash:
                    return jsonify({
                        "success": False,
                        "error": "토큰 정보가 유효하지 않습니다",
                        "code": 400
                    }), 400
                
                # 별명이 없으면 이메일의 @ 앞 부분을 기본값으로 사용
                if not nickname:
                    nickname = email.split('@')[0]
                
                # 중복 확인 (이메일 인증 완료된 사용자)
                existing_user = User.find_by_email(email)
                if existing_user and existing_user.email_verified:
                    token.mark_as_used()  # 토큰은 사용 처리
                    return jsonify({
                        "success": False,
                        "error": "이미 등록된 이메일입니다",
                        "code": 409
                    }), 409
                
                # 기존 미인증 계정이 있으면 삭제
                if existing_user:
                    db.session.delete(existing_user)
                
                # 사용자 생성 (이메일 인증 완료 후)
                user = User(
                    email=email.lower().strip(),
                    password_hash=password_hash,  # 이미 해시된 비밀번호 사용
                    nickname=nickname,  # 별명 설정
                    email_verified=True,
                    email_verified_at=datetime.utcnow(),
                    is_active=True,  # 이메일 인증 완료 시 즉시 활성화
                    is_deleted=False,
                    mfa_enabled=False
                )
                db.session.add(user)
                db.session.flush()  # ID 생성
                
                # 토큰에 user_id 연결 및 사용 처리
                token.user_id = user.id
                token.mark_as_used()
                db.session.commit()
                
                ip = get_client_ip()
                logger.info(f"이메일 검증 완료 및 계정 생성: user_id={user.id}, email={user.email[:3]}..., ip={ip}")
                
                # 감사 로그
                AuditLog.log_event(
                    user_id=user.id,
                    event_type='signup',
                    event_description='회원가입 완료 (이메일 인증)',
                    ip_address=ip,
                    user_agent=get_user_agent(),
                    success=True
                )
                AuditLog.log_event(
                    user_id=user.id,
                    event_type='email_verified',
                    event_description='이메일 검증 완료',
                    ip_address=ip,
                    user_agent=get_user_agent(),
                    success=True
                )
                
                return jsonify({
                    "success": True,
                    "message": "이메일 검증이 완료되었습니다. 계정이 생성되었습니다."
                }), 200
                
            except json.JSONDecodeError:
                return jsonify({
                    "success": False,
                    "error": "토큰 정보가 유효하지 않습니다",
                    "code": 400
                }), 400
        else:
            # 비밀번호 재설정 토큰 등 (기존 로직)
            user = User.query.get(token.user_id)
            if not user:
                return jsonify({
                    "success": False,
                    "error": "사용자를 찾을 수 없습니다",
                    "code": 404
                }), 404
            
            user.email_verified = True
            user.email_verified_at = datetime.utcnow()
            user.is_active = True
            token.mark_as_used()
            db.session.commit()
            
            ip = get_client_ip()
            logger.info(f"이메일 검증 성공: user_id={user.id}, email={user.email[:3] if user.email else 'unknown'}..., ip={ip}")
            
            # 감사 로그
            AuditLog.log_event(
                user_id=user.id,
                event_type='email_verified',
                event_description='이메일 검증 완료',
                ip_address=ip,
                user_agent=get_user_agent(),
                success=True
            )
            
            return jsonify({
                "success": True,
                "message": "이메일 검증이 완료되었습니다"
            }), 200
        
    except Exception as e:
        # 보안: 에러 메시지 최소화
        logger.error(f"이메일 검증 오류: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "이메일 검증 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    로그인
    POST /api/v1/auth/login
    Body: { "email": "...", "password": "...", "totp": "..." (선택) }
    보안: Rate limiting (app/__init__.py에서 적용, 브루트포스 공격 방지), 입력 검증
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        totp_code = data.get('totp', '')  # MFA 토큰 (선택)
        
        if not email or not password:
            return jsonify({
                "success": False,
                "error": "이메일과 비밀번호를 입력하세요",
                "code": 401
            }), 401
        
        # 사용자 조회
        user = User.find_by_email(email)
        
        # 사용자 존재 및 삭제 여부 확인
        if not user or user.is_deleted:
            # 감사 로그 (실패)
            ip = get_client_ip()
            AuditLog.log_login(
                user_id=None,
                success=False,
                ip_address=ip,
                user_agent=get_user_agent(),
                error_message="사용자 없음 또는 삭제된 계정"
            )
            # 보안: 로그인 실패 로그 기록
            logger.warning(f"로그인 실패 (사용자 없음 또는 삭제된 계정): email={email[:3]}..., ip={ip}")
            return jsonify({
                "success": False,
                "error": "로그인에 실패했습니다",
                "code": 401
            }), 401
        
        # 이메일 인증 확인 (is_active 체크 전에 확인)
        if not user.email_verified:
            ip = get_client_ip()
            AuditLog.log_login(
                user_id=user.id,
                success=False,
                ip_address=ip,
                user_agent=get_user_agent(),
                error_message="이메일 미인증"
            )
            logger.warning(f"로그인 실패 (이메일 미인증): user_id={user.id}, email={email[:3]}..., ip={ip}")
            # 이메일 인증이 필요하다는 것을 사용자에게 알림
            return jsonify({
                "success": False,
                "error": "이메일 인증이 필요합니다. 이메일을 확인해주세요.",
                "code": 403,
                "requires_verification": True
            }), 403
        
        # 계정 활성화 상태 확인 (이메일 인증 완료 후)
        if not user.is_active:
            ip = get_client_ip()
            AuditLog.log_login(
                user_id=user.id,
                success=False,
                ip_address=ip,
                user_agent=get_user_agent(),
                error_message="비활성 계정"
            )
            logger.warning(f"로그인 실패 (비활성 계정): user_id={user.id}, email={email[:3]}..., ip={ip}")
            return jsonify({
                "success": False,
                "error": "로그인에 실패했습니다",
                "code": 401
            }), 401
        
        # 계정 잠금 확인
        if user.is_locked():
            ip = get_client_ip()
            # 보안: 계정 잠금 로그 기록
            logger.warning(f"로그인 시도 (계정 잠금): user_id={user.id}, email={email[:3]}..., ip={ip}")
            AuditLog.log_login(
                user_id=user.id,
                success=False,
                ip_address=ip,
                user_agent=get_user_agent(),
                error_message="계정 잠금"
            )
            return jsonify({
                "success": False,
                "error": "계정이 일시적으로 잠겨있습니다. 30분 후 다시 시도하세요",
                "code": 423
            }), 423
        
        # 비밀번호 확인
        if not user.check_password(password):
            user.increment_login_failure()
            ip = get_client_ip()
            
            # 감사 로그 (실패)
            AuditLog.log_login(
                user_id=user.id,
                success=False,
                ip_address=ip,
                user_agent=get_user_agent(),
                error_message="비밀번호 불일치"
            )
            # 보안: 로그인 실패 로그 기록
            logger.warning(f"로그인 실패 (비밀번호 불일치): user_id={user.id}, email={email[:3]}..., ip={ip}, 실패 횟수={user.login_failure_count}")
            
            return jsonify({
                "success": False,
                "error": "로그인에 실패했습니다",
                "code": 401
            }), 401
        
        # 이메일 검증 확인
        if not user.email_verified:
            return jsonify({
                "success": False,
                "error": "이메일 검증이 필요합니다",
                "code": 403
            }), 403
        
        # MFA 검증 (활성화된 경우)
        if user.mfa_enabled:
            if not totp_code:
                return jsonify({
                    "success": False,
                    "error": "MFA 토큰이 필요합니다",
                    "code": 401,
                    "requires_mfa": True
                }), 401
            
            # TOTP 또는 복구 코드 확인
            if not user.verify_totp(totp_code) and not user.verify_backup_code(totp_code):
                user.increment_login_failure()
                ip = get_client_ip()
                
                AuditLog.log_login(
                    user_id=user.id,
                    success=False,
                    ip_address=ip,
                    user_agent=get_user_agent(),
                    error_message="MFA 토큰 불일치"
                )
                # 보안: MFA 토큰 불일치 로그 기록
                logger.warning(f"로그인 실패 (MFA 토큰 불일치): user_id={user.id}, email={email[:3]}..., ip={ip}")
                
                return jsonify({
                    "success": False,
                    "error": "MFA 토큰이 올바르지 않습니다",
                    "code": 401
                }), 401
        
        # 로그인 성공
        user.reset_login_failure()
        user.last_login = datetime.utcnow()
        user.last_login_ip = get_client_ip()
        
        # 보안: 기존 세션 무효화 (세션 고정 공격 방지)
        existing_session_id = request.cookies.get('session_id')
        if existing_session_id:
            existing_session = UserSession.find_by_session_id(existing_session_id)
            if existing_session and existing_session.user_id == user.id:
                existing_session.revoke()
                logger.info(f"기존 세션 무효화: user_id={user.id}, session_id={existing_session_id[:8]}...")
        
        # 새 세션 생성 (세션 회전)
        session = UserSession.create_session(
            user_id=user.id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent(),
            expiry_hours=24
        )
        
        # CSRF 토큰 생성
        csrf_token = generate_csrf_token(str(user.id))
        
        # 응답 생성
        response = make_response(jsonify({
            "success": True,
            "data": {
                "user": user.to_dict(),
                "csrf_token": csrf_token,
                "session_id": session.session_id
            }
        }))
        
        # 세션 쿠키 설정 (HTTP 전용 - Secure 플래그 미설정)
        flask_env = os.getenv("FLASK_ENV", "development")
        response.set_cookie(
            'session_id',
            session.session_id,
            httponly=True,
            secure=False,  # HTTP 환경이므로 Secure 미설정
            samesite='Strict',  # CSRF 방지
            path='/',
            max_age=86400  # 24시간
        )
        
        # 세션 토큰 쿠키 (Double Submit Cookie)
        response.set_cookie(
            'session_token',
            session.session_token,
            httponly=False,  # JavaScript에서 읽을 수 있어야 함
            secure=False,
            samesite='Strict',
            path='/',
            max_age=86400
        )
        
        ip = get_client_ip()
        # 보안: 로그인 성공 로그 기록
        logger.info(f"로그인 성공: user_id={user.id}, email={email[:3]}..., ip={ip}")
        
        # 감사 로그
        AuditLog.log_login(
            user_id=user.id,
            success=True,
            ip_address=ip,
            user_agent=get_user_agent()
        )
        
        return response, 200
        
    except Exception as e:
        # 보안: 에러 메시지 최소화 (상세 정보는 로그에만 기록)
        logger.error(f"로그인 오류: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "로그인 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    로그아웃
    POST /api/v1/auth/logout
    """
    try:
        session_id = request.cookies.get('session_id')
        
        if session_id:
            session = UserSession.find_by_session_id(session_id)
            if session:
                user_id = session.user_id
                session.revoke()
                ip = get_client_ip()
                
                # 감사 로그
                AuditLog.log_logout(
                    user_id=user_id,
                    ip_address=ip,
                    user_agent=get_user_agent()
                )
                # 보안: 로그아웃 로그 기록
                logger.info(f"로그아웃: user_id={user_id}, ip={ip}")
        
        # 쿠키 삭제
        response = make_response(jsonify({
            "success": True,
            "message": "로그아웃되었습니다"
        }))
        
        response.set_cookie('session_id', '', expires=0)
        response.set_cookie('session_token', '', expires=0)
        
        return response, 200
        
    except Exception as e:
        logger.error(f"로그아웃 오류: {e}")
        return jsonify({
            "success": False,
            "error": "로그아웃 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/request-reset', methods=['POST'])
def request_password_reset():
    """
    비밀번호 재설정 요청
    POST /api/v1/auth/request-reset
    Body: { "email": "..." }
    """
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({
                "success": False,
                "error": "이메일을 입력하세요",
                "code": 400
            }), 400
        
        # 보안: 사용자 존재 여부와 관계없이 동일한 응답 (이메일 존재 여부 노출 방지)
        user = User.find_by_email(email)
        
        if user and user.email_verified:
            # 비밀번호 재설정 토큰 생성
            token_plaintext, token = Token.create_token(
                user_id=user.id,
                token_type='password_reset',
                expiry_hours=1  # 1시간만 유효
            )
            
            # TODO: 이메일 전송
            # 비밀번호 재설정 이메일 전송
            reset_url = f"{request.host_url.rstrip('/')}/api/v1/auth/reset-password?token={token_plaintext}"
            try:
                from app.services.email_service import EmailService
                email_sent = EmailService.send_password_reset_email(user.email, token_plaintext, reset_url)
                if email_sent:
                    logger.info(f"비밀번호 재설정 메일 전송 성공: {email}")
                else:
                    logger.warning(f"비밀번호 재설정 메일 전송 실패: {email}")
            except Exception as e:
                logger.error(f"비밀번호 재설정 메일 전송 중 오류: {e}", exc_info=True)
            
            logger.info(f"비밀번호 재설정 토큰 생성: {email}")
            
            # 감사 로그
            AuditLog.log_event(
                user_id=user.id,
                event_type='password_reset_requested',
                event_description='비밀번호 재설정 요청',
                ip_address=get_client_ip(),
                user_agent=get_user_agent(),
                success=True
            )
        
        # 보안: 항상 동일한 응답 반환
        return jsonify({
            "success": True,
            "message": "비밀번호 재설정 이메일을 발송했습니다. 이메일을 확인하세요"
        }), 200
        
    except Exception as e:
        logger.error(f"비밀번호 재설정 요청 오류: {e}")
        return jsonify({
            "success": False,
            "error": "비밀번호 재설정 요청 중 오류가 발생했습니다",
            "code": 500
        }), 500


@auth_bp.route('/reset', methods=['POST'])
def reset_password():
    """
    비밀번호 재설정
    POST /api/v1/auth/reset
    Body: { "token": "...", "newPassword": "..." }
    """
    try:
        data = request.get_json()
        token_plaintext = data.get('token')
        new_password = data.get('newPassword')
        
        if not token_plaintext or not new_password:
            return jsonify({
                "success": False,
                "error": "토큰과 새 비밀번호를 입력하세요",
                "code": 400
            }), 400
        
        # 비밀번호 강도 검증
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            return jsonify({
                "success": False,
                "error": error_msg,
                "code": 400
            }), 400
        
        # 토큰 검증
        token = Token.verify_token(token_plaintext, 'password_reset')
        
        if not token:
            return jsonify({
                "success": False,
                "error": "유효하지 않거나 만료된 토큰입니다",
                "code": 400
            }), 400
        
        if token.used:
            return jsonify({
                "success": False,
                "error": "이미 사용된 토큰입니다",
                "code": 410
            }), 410
        
        # 사용자 조회
        user = User.query.get(token.user_id)
        if not user:
            return jsonify({
                "success": False,
                "error": "사용자를 찾을 수 없습니다",
                "code": 404
            }), 404
        
        # 비밀번호 변경
        user.set_password(new_password)
        token.mark_as_used()
        
        # 모든 세션 무효화 (보안)
        UserSession.revoke_all_user_sessions(user.id)
        
        db.session.commit()
        
        logger.info(f"비밀번호 재설정 성공: {user.email}")
        
        # 감사 로그
        AuditLog.log_password_change(
            user_id=user.id,
            ip_address=get_client_ip(),
            user_agent=get_user_agent()
        )
        
        return jsonify({
            "success": True,
            "message": "비밀번호가 성공적으로 변경되었습니다"
        }), 200
        
    except ValueError as e:
        logger.warning(f"비밀번호 재설정 실패: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "code": 400
        }), 400
    except Exception as e:
        logger.error(f"비밀번호 재설정 오류: {e}")
        return jsonify({
            "success": False,
            "error": "비밀번호 재설정 중 오류가 발생했습니다",
            "code": 500
        }), 500

