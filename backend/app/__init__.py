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

# 보안: 환경 변수 검증
def validate_environment():
    """환경 변수 검증"""
    flask_env = os.getenv("FLASK_ENV", "development")
    
    if flask_env == "production":
        required_vars = ["FLASK_SECRET_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"운영 환경에서 필수 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
    
    # SECRET_KEY 검증
    secret_key = os.getenv("FLASK_SECRET_KEY")
    if flask_env == "production" and (not secret_key or secret_key == "dev-secret-key"):
        raise ValueError("운영 환경에서는 강력한 FLASK_SECRET_KEY를 설정해야 합니다")
    
    return True

def setup_logging(app):
    """로깅 설정"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s'
    )

def create_app(config_name=None):
    """Flask 애플리케이션 팩토리"""
    # 환경 변수 검증
    validate_environment()
    
    static_folder_path = os.path.join(BASE_DIR, 'static')
    app = Flask(__name__, static_folder=static_folder_path, static_url_path='/static')
    
    # 환경 설정
    flask_env = os.getenv("FLASK_ENV", "development")
    secret_key = os.getenv("FLASK_SECRET_KEY")
    
    # 보안: SECRET_KEY 검증 및 설정
    if not secret_key or secret_key == "dev-secret-key":
        if flask_env == "production":
            raise ValueError("운영 환경에서는 FLASK_SECRET_KEY를 설정해야 합니다")
        secret_key = "dev-secret-key-change-in-production"
    
    # 최소 32자 이상의 강력한 키 검증 (운영 환경)
    if flask_env == "production" and len(secret_key) < 32:
        raise ValueError("운영 환경에서는 최소 32자 이상의 강력한 SECRET_KEY를 사용해야 합니다")
    
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
    
    # CORS 설정 (보안 강화)
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    # 운영 환경에서는 명시적 origin만 허용
    if flask_env == "production" and "*" in cors_origins:
        raise ValueError("운영 환경에서는 와일드카드(*) CORS origin을 사용할 수 없습니다")
    
    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PATCH", "DELETE", "PUT"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": flask_env == "development",  # 운영 환경에서는 False 권장
            "max_age": 3600  # preflight 요청 캐싱
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
    # 모든 응답(에러 포함)에 보안 헤더 적용
    @app.after_request
    def set_security_headers(response):
        """보안 헤더를 설정하고 버전 정보 유출을 방지합니다.
        모든 응답(정상 응답, 에러 응답, 정적 파일 포함)에 적용됩니다.
        """
        # Server 헤더 제거 후 브랜드명으로 교체
        response.headers.pop('Server', None)
        response.headers['Server'] = 'PrivAlert'
        response.headers.pop('X-Powered-By', None)
        
        # MIME-sniffing 방지
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # 클릭재킹 방지
        response.headers['X-Frame-Options'] = 'DENY'
        
        # XSS 방지
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer 정책
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # 브라우저 기능 제한
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=(), payment=(), usb=(), '
            'magnetometer=(), gyroscope=(), speaker=()'
        )
        
        # 요청 경로 확인
        request_path = request.path if request else ''
        is_admin_path = request_path.startswith('/admin') or request_path.startswith('/api/v1/admin')
        
        # Content Security Policy
        # 관리자 페이지에 대해 더 엄격한 CSP 적용
        if is_admin_path:
            # 관리자 페이지용 엄격한 CSP 정책
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "object-src 'none'; "
                "media-src 'none'; "
                "worker-src 'none'; "
                "manifest-src 'self'; "
                "upgrade-insecure-requests"
            )
        else:
            # 일반 페이지용 CSP 정책
            # 보안: 와일드카드 제거, 'self'와 data:만 허용 (외부 이미지가 필요하면 특정 도메인 명시)
            csp = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        
        response.headers['Content-Security-Policy'] = csp
        
        # 프로덕션 환경에서만 HSTS 활성화
        if flask_env == "production":
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        # Content-Type 설정 보정
        content_type = response.headers.get('Content-Type', '')
        if not content_type:
            response.headers['Content-Type'] = 'application/json; charset=utf-8'
        elif 'charset' not in content_type.lower():
            if 'text/' in content_type or 'application/json' in content_type:
                response.headers['Content-Type'] = f'{content_type}; charset=utf-8'
        
        return response
    
    # data 디렉토리도 정적 파일로 서빙 (원본 파일용)
    # 보안: 경로 조작 방지
    from flask import send_from_directory, abort
    from app.utils.security_utils import validate_path
    
    @app.route('/data/<path:filename>')
    def serve_data(filename):
        """보안이 적용된 정적 파일 서빙"""
        # 경로 조작 방지
        is_valid, error = validate_path(BASE_DATA_DIR, filename)
        if not is_valid:
            app.logger.warning(f"경로 조작 시도 감지: {filename}")
            abort(403)
        
        try:
            response = send_from_directory(BASE_DATA_DIR, filename)
            # 보안: 정적 파일에도 X-Content-Type-Options 헤더 명시적 설정 (이중 보장)
            response.headers['X-Content-Type-Options'] = 'nosniff'
            return response
        except FileNotFoundError:
            abort(404)
    
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
        os.path.join(BASE_DATA_DIR, "video"),
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
    from app.routes.video_processing_routes import video_bp

    
    app.register_blueprint(integrated_filter_bp, url_prefix="/api/v1/filter")
    app.register_blueprint(integrated_analysis_bp, url_prefix="/api/v1")
    app.register_blueprint(education_bp, url_prefix="/api/v1/education")
    app.register_blueprint(workplace_bp, url_prefix="/api/v1/workplace")
    app.register_blueprint(name_detection_bp, url_prefix="/api/v1/name")
    app.register_blueprint(admin_auth_bp, url_prefix="/api/v1/admin/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/v1/admin")  
    app.register_blueprint(video_bp, url_prefix="/api/v1/video")  
    
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
    
    # 에러 핸들러 (모든 에러 응답에도 보안 헤더가 적용됨 - @app.after_request를 통해)
    @app.errorhandler(400)
    def bad_request(error):
        response = jsonify({"success": False, "error": "잘못된 요청입니다", "code": 400})
        # 보안: X-Content-Type-Options 헤더 명시적 설정 (이중 보장)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response, 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        """인증 필요 핸들러"""
        response = jsonify({
            "success": False,
            "error": "인증이 필요합니다",
            "code": 401
        })
        # 보안: X-Content-Type-Options 헤더 명시적 설정 (이중 보장)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response, 401
    
    @app.errorhandler(403)
    def forbidden(error):
        """접근 거부 핸들러"""
        response = jsonify({"success": False, "error": "접근이 거부되었습니다", "code": 403})
        # 보안: X-Content-Type-Options 헤더 명시적 설정 (이중 보장)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response, 403
    
    @app.errorhandler(404)
    def not_found(error):
        response = jsonify({
            "success": False, 
            "error": "요청한 리소스를 찾을 수 없습니다", 
            "code": 404,
            "message": "사용 가능한 엔드포인트 목록은 루트 경로(/)를 참조하세요."
        })
        # 보안: X-Content-Type-Options 헤더 명시적 설정 (이중 보장)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response, 404
    
    @app.errorhandler(413)
    def payload_too_large(error):
        """페이로드 크기 초과 핸들러"""
        response = jsonify({"success": False, "error": "파일 크기가 너무 큽니다 (최대 10MB)", "code": 413})
        # 보안: X-Content-Type-Options 헤더 명시적 설정 (이중 보장)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response, 413
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """서버 오류 핸들러 (보안: 상세 정보 노출 방지)"""
        # 상세한 에러 정보는 로그에만 기록
        app.logger.error(f"서버 오류: {error}", exc_info=True)
        # 클라이언트에는 일반적인 메시지만 반환
        response = jsonify({"success": False, "error": "서버 내부 오류가 발생했습니다", "code": 500})
        # 보안: X-Content-Type-Options 헤더 명시적 설정 (이중 보장)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response, 500
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """모든 예외 처리 (보안: 상세 정보 노출 방지)"""
        app.logger.error(f"예외 발생: {error}", exc_info=True)
        response = jsonify({"success": False, "error": "서버 오류가 발생했습니다", "code": 500})
        # 보안: X-Content-Type-Options 헤더 명시적 설정 (이중 보장)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response, 500
    
    return app
