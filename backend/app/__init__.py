import os
import logging
from flask import Flask, jsonify
from flasgger import Swagger
from dotenv import load_dotenv
from flask_cors import CORS
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
        "SESSION_COOKIE_SECURE": flask_env == "production",  # HTTPS만 허용 (운영 환경)
        "SESSION_COOKIE_HTTPONLY": True,  # XSS 방지
        "SESSION_COOKIE_SAMESITE": "Lax",  # CSRF 방지
        "PREFERRED_URL_SCHEME": "https" if flask_env == "production" else "http"
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
            "methods": ["GET", "POST"],
            "allow_headers": ["Content-Type"],
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
    
    # 보안 헤더 추가
    @app.after_request
    def set_security_headers(response):
        """보안 헤더 설정"""
        # XSS 방지
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy (기본 설정)
        if flask_env == "production":
            response.headers['Content-Security-Policy'] = "default-src 'self'"
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # 서버 정보 숨김
        response.headers['Server'] = 'PrivAlert'
        
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
            return send_from_directory(BASE_DATA_DIR, filename)
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
    
    # 블루프린트 등록
    from app.routes.face_detection_routes import face_bp
    from app.routes.hand_detection_routes import hand_bp
    from app.routes.ocr_routes import ocr_bp
    from app.routes.image_sanitize_routes import image_sanitize_bp
    from app.routes.integrated_filter_routes import integrated_filter_bp
    from app.routes.integrated_analysis_routes import integrated_analysis_bp
    from app.routes.education_routes import education_bp
    from app.routes.workplace_detection_routes import workplace_bp
    from app.routes.name_detection_routes import name_detection_bp
    from app.routes.video_processing_routes import video_bp
    
    app.register_blueprint(face_bp, url_prefix="/api/v1/face")
    app.register_blueprint(hand_bp, url_prefix="/api/v1/hand")
    app.register_blueprint(ocr_bp, url_prefix="/api/v1/ocr")
    app.register_blueprint(image_sanitize_bp, url_prefix="/api/v1/images")
    app.register_blueprint(integrated_filter_bp, url_prefix="/api/v1/filter")
    app.register_blueprint(integrated_analysis_bp, url_prefix="/api/v1")
    app.register_blueprint(education_bp, url_prefix="/api/v1/education")
    app.register_blueprint(workplace_bp, url_prefix="/api/v1/workplace")
    app.register_blueprint(name_detection_bp, url_prefix="/api/v1/name")
    app.register_blueprint(video_bp, url_prefix="/api/v1/video")  
    
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
        return jsonify({"success": False, "error": "요청한 리소스를 찾을 수 없습니다", "code": 404}), 404
    
    @app.errorhandler(413)
    def payload_too_large(error):
        """페이로드 크기 초과 핸들러"""
        return jsonify({"success": False, "error": "파일 크기가 너무 큽니다 (최대 10MB)", "code": 413}), 413
    
    @app.errorhandler(500)
    def internal_server_error(error):
        """서버 오류 핸들러 (보안: 상세 정보 노출 방지)"""
        # 상세한 에러 정보는 로그에만 기록
        app.logger.error(f"서버 오류: {error}", exc_info=True)
        # 클라이언트에는 일반적인 메시지만 반환
        return jsonify({"success": False, "error": "서버 내부 오류가 발생했습니다", "code": 500}), 500
    
    @app.errorhandler(403)
    def forbidden(error):
        """접근 거부 핸들러"""
        return jsonify({"success": False, "error": "접근이 거부되었습니다", "code": 403}), 403
    
    return app
