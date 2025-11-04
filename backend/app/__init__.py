import os
import logging
import mimetypes
from flask import Flask, jsonify, request, Response, send_file
from flasgger import Swagger
from dotenv import load_dotenv
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.file_utils import ensure_dir
from config import BASE_DATA_DIR, BASE_DIR

# 환경변수 로드
load_dotenv()

def setup_logging(app):
    """로깅 설정"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )

def create_app(config_name=None):
    """Flask 애플리케이션 팩토리"""
    static_folder_path = os.path.join(BASE_DIR, 'static')
    app = Flask(__name__, static_folder=static_folder_path, static_url_path='/static')
    
    # 환경 설정
    flask_env = os.getenv("FLASK_ENV", "development")
    secret_key = os.getenv("FLASK_SECRET_KEY")
    
    # 보안 검증
    if not secret_key or secret_key == "dev-secret-key":
        if flask_env == "production":
            raise ValueError("운영 환경에서는 FLASK_SECRET_KEY를 설정해야 합니다")
        secret_key = "dev-secret-key-change-in-production"
    
    app.config.update({
        "SECRET_KEY": secret_key,
        "MAX_CONTENT_LENGTH": int(os.getenv("MAX_CONTENT_LENGTH", "10")) * 1024 * 1024,
        "DEBUG": flask_env == "development",
        # 세션 보안 설정
        "SESSION_COOKIE_SECURE": flask_env == "production",  # HTTPS에서만 쿠키 전송
        "SESSION_COOKIE_HTTPONLY": True,  # JavaScript에서 쿠키 접근 방지
        "SESSION_COOKIE_SAMESITE": "Lax",  # CSRF 공격 방지
        # 기타 보안 설정
        "PREFERRED_URL_SCHEME": "https" if flask_env == "production" else "http",
        "TRAP_HTTP_EXCEPTIONS": True,  # HTTP 예외 처리
        "TRAP_BAD_REQUEST_ERRORS": True,  # 잘못된 요청 처리
    })
    
    # 로깅 설정
    setup_logging(app)
    
    # CORS 설정
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PATCH", "DELETE", "PUT"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        },
        r"/data/*": {
            "origins": cors_origins,
            "methods": ["GET"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False
        }
    })
    
    # JWT 설정
    jwt_secret_key = os.getenv("JWT_SECRET_KEY", secret_key)
    app.config["JWT_SECRET_KEY"] = jwt_secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False  # 데코레이터에서 직접 설정
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = False  # 데코레이터에서 직접 설정
    app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # 개발 환경에서는 비활성화 (프로덕션에서는 True)
    app.config["JWT_COOKIE_SECURE"] = flask_env == "production"
    app.config["JWT_COOKIE_HTTPONLY"] = True
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"
    
    jwt = JWTManager(app)
    
    # Rate Limiter 설정
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://"  # 개발 환경 (프로덕션에서는 Redis 사용 권장)
    )
    
    # 보안 헤더 설정 (OWASP 보안 가이드라인 준수)
    @app.after_request
    def set_security_headers(response):
        """보안 헤더를 설정하고 버전 정보 유출을 방지합니다."""
        # Server 헤더 제거 (버전 정보 유출 방지)
        response.headers.pop('Server', None)
        response.headers.pop('X-Powered-By', None)
        
        # MIME-sniffing 방지
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # 클릭재킹 방지 (X-Frame-Options)
        response.headers['X-Frame-Options'] = 'DENY'
        
        # XSS 공격 방지 (레거시 브라우저 지원)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer 정책 설정
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # 브라우저 기능 정책 설정
        response.headers['Permissions-Policy'] = (
            'geolocation=(), '
            'microphone=(), '
            'camera=(), '
            'payment=(), '
            'usb=(), '
            'magnetometer=(), '
            'gyroscope=(), '
            'speaker=()'
        )
        
        # Content Security Policy (CSP) - 기본 설정
        # API 서버이므로 스크립트 실행 최소화
        csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # 프로덕션 환경에서만 HSTS 설정 (HTTPS 사용 시)
        flask_env = os.getenv("FLASK_ENV", "development")
        if flask_env == "production":
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Content-Type 헤더 적절히 설정
        content_type = response.headers.get('Content-Type', '')
        
        if not content_type:
            # Content-Type이 없는 경우 기본값 설정
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        else:
            # Content-Type이 있지만 charset이 없는 경우 추가
            if 'charset' not in content_type.lower():
                # text/ 또는 application/json 타입에 charset 추가
                if 'text/' in content_type or 'application/json' in content_type:
                    response.headers['Content-Type'] = f'{content_type}; charset=utf-8'
        
        return response
    
    # data 디렉토리도 정적 파일로 서빙 (원본 파일용)
    from flask import send_from_directory
    @app.route('/data/<path:filename>')
    def serve_data(filename):
        return send_from_directory(BASE_DATA_DIR, filename)
    
    # Swagger 설정
    port = os.getenv("PORT", "5000")
    try:
        Swagger(app, config={
            "headers": [],
            "specs": [{
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }],
            "static_url_path": "/flasgger_static",
            "swagger_ui": True,
            "specs_route": "/api-docs/",
            "swagger_ui_args": {
                "displayRequestDuration": True,
                "docExpansion": "list",
                "operationsSorter": "method",
                "tagsSorter": "alpha"
            }
        }, template={
            "swagger": "2.0",
            "info": {
                "title": "PrivAlert API",
                "description": "개인정보 탐지 및 분석 API - 이미지와 텍스트를 통합 분석하여 민감 정보를 탐지합니다",
                "version": "1.0.0",
                "contact": {
                    "name": "PrivAlert Team",
                    "email": "support@privalert.com"
                }
            },
            "host": f"localhost:{port}",
            "basePath": "/api/v1",
            "schemes": ["http"],
            "produces": ["application/json"],
            "consumes": ["application/json", "multipart/form-data"],
            "definitions": {
                "FileUpload": {
                    "type": "object",
                    "properties": {
                        "image": {
                            "type": "file",
                            "description": "분석할 이미지 파일"
                        },
                        "text": {
                            "type": "string",
                            "description": "분석할 텍스트"
                        },
                        "blur_fingers": {
                            "type": "boolean",
                            "description": "손가락 블러 처리 여부",
                            "default": "true"
                        },
                        "show_faces": {
                            "type": "boolean",
                            "description": "얼굴 상세 표시 여부",
                            "default": "false"
                        }
                    }
                }
            }
        })
        app.logger.info("Swagger 설정 완료")
    except Exception as e:
        app.logger.error(f"Swagger 설정 중 오류 발생: {e}")
        # Swagger 설정 실패해도 앱은 계속 실행
    
    # 필요한 디렉토리 생성
    required_dirs = [
        os.path.join(BASE_DATA_DIR, "face"),
        os.path.join(BASE_DATA_DIR, "hand"),
        os.path.join(BASE_DATA_DIR, "ocr"),
        os.path.join(BASE_DATA_DIR, "image"),  
    ]
    for d in required_dirs:
        ensure_dir(d)
    
    # 블루프린트 등록 (OpenCV/MediaPipe 의존성 있는 것들은 임시 비활성화)
    try:
        from app.routes.face_detection_routes import face_bp
        app.register_blueprint(face_bp, url_prefix="/api/v1/face")
    except ImportError as e:
        app.logger.warning(f"Face detection routes not available: {e}")
    
    try:
        from app.routes.hand_detection_routes import hand_bp
        app.register_blueprint(hand_bp, url_prefix="/api/v1/hand")
    except ImportError as e:
        app.logger.warning(f"Hand detection routes not available: {e}")
    
    try:
        from app.routes.ocr_routes import ocr_bp
        app.register_blueprint(ocr_bp, url_prefix="/api/v1/ocr")
    except ImportError as e:
        app.logger.warning(f"OCR routes not available: {e}")
    
    try:
        from app.routes.image_sanitize_routes import image_sanitize_bp
        app.register_blueprint(image_sanitize_bp, url_prefix="/api/v1/images")
    except ImportError as e:
        app.logger.warning(f"Image sanitize routes not available: {e}")
    
    from app.routes.integrated_filter_routes import integrated_filter_bp
    from app.routes.integrated_analysis_routes import integrated_analysis_bp
    from app.routes.education_routes import education_bp
    from app.routes.workplace_detection_routes import workplace_bp
    from app.routes.name_detection_routes import name_detection_bp
    from app.routes.admin_auth_routes import admin_auth_bp
    from app.routes.admin_routes import admin_bp
    
    app.register_blueprint(integrated_filter_bp, url_prefix="/api/v1/filter")
    app.register_blueprint(integrated_analysis_bp, url_prefix="/api/v1")
    app.register_blueprint(education_bp, url_prefix="/api/v1/education")
    app.register_blueprint(workplace_bp, url_prefix="/api/v1/workplace")
    app.register_blueprint(name_detection_bp, url_prefix="/api/v1/name")
    app.register_blueprint(admin_auth_bp, url_prefix="/api/v1/admin/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/v1/admin")  
    
    # 루트 경로
    @app.route("/")
    def index():
        return jsonify({
            "service": "PrivAlert",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "health": "/health",
                "api_docs": "/api-docs/",
                "apispec": "/apispec.json",
                "face_detection": "/api/v1/face",
                "hand_detection": "/api/v1/hand",
                "ocr": "/api/v1/ocr",
                "image_sanitize": "/api/v1/images",
                "integrated_analysis": "/api/v1/analyze",
                "integrated_filter": "/api/v1/filter",
                "education": "/api/v1/education",
                "workplace": "/api/v1/workplace",
                "name_detection": "/api/v1/name",
                "admin_auth": "/api/v1/admin/auth",
                "admin": "/api/v1/admin"
            }
        })
    
    # 헬스체크 엔드포인트
    @app.route("/health")
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "PrivAlert",
            "version": "1.0.0"
        })
    
    # 에러 핸들러
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"success": False, "error": "잘못된 요청입니다", "code": 400}), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "success": False, 
            "error": "요청한 리소스를 찾을 수 없습니다", 
            "code": 404,
            "message": "사용 가능한 엔드포인트 목록은 루트 경로(/)를 참조하세요."
        }), 404
    
    @app.errorhandler(413)
    def payload_too_large(error):
        return jsonify({"success": False, "error": "파일 크기가 너무 큽니다 (최대 10MB)", "code": 413}), 413
    
    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"서버 오류: {error}")
        return jsonify({"success": False, "error": "서버 내부 오류가 발생했습니다", "code": 500}), 500
    
    return app
