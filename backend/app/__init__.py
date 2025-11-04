import os
import secrets
import logging
from flask import Flask, jsonify
from flasgger import Swagger
from dotenv import load_dotenv
from flask_cors import CORS
from app.utils.file_utils import ensure_dir
from app.extensions import db, login_manager, migrate, limiter
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
    
    # DB 설정
    database_url = os.getenv("DATABASE_URL", "sqlite:///privalert.db")
    
    app.config.update({
        "SECRET_KEY": secret_key,
        "MAX_CONTENT_LENGTH": int(os.getenv("MAX_CONTENT_LENGTH", "10")) * 1024 * 1024,
        "DEBUG": flask_env == "development",
        # DB 설정
        "SQLALCHEMY_DATABASE_URI": database_url,
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        # 세션/쿠키 강화 (시큐어코딩 가이드 준수)
        "SESSION_COOKIE_HTTPONLY": True,  # JS 접근 차단
        "SESSION_COOKIE_SECURE": flask_env == "production",  # HTTPS 전용 (프로덕션)
        "SESSION_COOKIE_SAMESITE": "Lax",  # CSRF 추가 방어
        "REMEMBER_COOKIE_HTTPONLY": True,
        "REMEMBER_COOKIE_SECURE": flask_env == "production",
        "REMEMBER_COOKIE_DURATION": 3600,  # 1시간 (최소 보존 시간 권장)
    })
    
    # 로깅 설정
    setup_logging(app)
    
    # 확장 초기화
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    
    # CSRF 보호 (API 기반이므로 선택적 적용)
    # 웹 폼이 있는 경우에만 활성화
    # csrf.init_app(app)
    
    # Flask-Login 설정
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.session_protection = "strong"  # 세션 보호 강화
    
    @login_manager.user_loader
    def load_user(user_id):
        """사용자 로드 함수"""
        from app.models import User
        return User.query.get(int(user_id))
    
    # CORS 설정
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": True
        },
        r"/data/*": {
            "origins": cors_origins,
            "methods": ["GET"],
            "allow_headers": ["Content-Type"],
            "supports_credentials": False
        }
    })
    
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
    from app.routes.auth_routes import auth_bp
    from app.routes.admin_routes import admin_bp
    
    app.register_blueprint(face_bp, url_prefix="/api/v1/face")
    app.register_blueprint(hand_bp, url_prefix="/api/v1/hand")
    app.register_blueprint(ocr_bp, url_prefix="/api/v1/ocr")
    app.register_blueprint(image_sanitize_bp, url_prefix="/api/v1/images")
    app.register_blueprint(integrated_filter_bp, url_prefix="/api/v1/filter")
    app.register_blueprint(integrated_analysis_bp, url_prefix="/api/v1")
    app.register_blueprint(education_bp, url_prefix="/api/v1/education")
    app.register_blueprint(workplace_bp, url_prefix="/api/v1/workplace")
    app.register_blueprint(name_detection_bp, url_prefix="/api/v1/name")
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)  
    
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
        return jsonify({"success": False, "error": "파일 크기가 너무 큽니다 (최대 10MB)", "code": 413}), 413
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"success": False, "error": "접근 권한이 없습니다", "code": 403}), 403
    
    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"서버 오류: {error}")
        return jsonify({"success": False, "error": "서버 내부 오류가 발생했습니다", "code": 500}), 500
    
    # DB 테이블 생성 (개발 환경에서만)
    if flask_env == "development":
        with app.app_context():
            try:
                db.create_all()
                app.logger.info("DB 테이블 생성 완료")
            except Exception as e:
                app.logger.warning(f"DB 테이블 생성 중 오류 (이미 생성되었을 수 있음): {e}")
    
    return app
