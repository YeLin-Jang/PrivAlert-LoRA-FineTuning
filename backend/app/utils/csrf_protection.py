"""
CSRF 보호 유틸리티
- Flask-WTF 기반 CSRF 토큰 검증
"""

import logging
from functools import wraps
from flask import request, jsonify, session
from flask_wtf.csrf import CSRFProtect, generate_csrf, validate_csrf
from wtforms import ValidationError

logger = logging.getLogger(__name__)

csrf = CSRFProtect()


def init_csrf(app):
    """CSRF 보호 초기화"""
    csrf.init_app(app)
    
    # CSRF 설정
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1시간
    app.config['WTF_CSRF_CHECK_DEFAULT'] = True
    
    # CSRF 토큰 엔드포인트 (프론트엔드에서 토큰 가져오기)
    @app.route('/api/v1/auth/csrf-token', methods=['GET'])
    def get_csrf_token():
        """CSRF 토큰 발급"""
        token = generate_csrf()
        return jsonify({
            'success': True,
            'csrf_token': token
        })
    
    logger.info("CSRF 보호 초기화 완료")


def csrf_exempt(f):
    """CSRF 검증 제외 데코레이터 (필요한 경우만 사용)"""
    f.__csrf_exempt__ = True
    return f


def csrf_protect_manual(f):
    """
    수동 CSRF 검증 데코레이터
    - API 엔드포인트에서 사용
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # CSRF 토큰 검증
            csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if csrf_token:
                validate_csrf(csrf_token)
            else:
                # 토큰이 없으면 자동 검증 (쿠키 기반)
                validate_csrf()
        except ValidationError as e:
            logger.warning(f"CSRF 검증 실패: {e}")
            return jsonify({
                'success': False,
                'error': 'CSRF 토큰이 유효하지 않습니다',
                'code': 403
            }), 403
        except Exception as e:
            logger.error(f"CSRF 검증 중 오류: {e}")
            return jsonify({
                'success': False,
                'error': 'CSRF 검증 중 오류가 발생했습니다',
                'code': 500
            }), 500
        
        return f(*args, **kwargs)
    
    return decorated_function

