import os
import logging
from flask import Flask, jsonify
from flasgger import Swagger
from dotenv import load_dotenv
from flask_cors import CORS
from app.utils.file_utils import ensure_dir
from config import BASE_DATA_DIR  

# 환경변수 로드
load_dotenv()

def setup_logging(app):
    """로깅 설정"""
    if not app.config['DEBUG']:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(name)s: %(message)s'
        )

def create_app(config_name=None):
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)
    
    # 환경 설정
    flask_env = os.getenv("FLASK_ENV", "development")
    app.config.update({
        "SECRET_KEY": os.getenv("FLASK_SECRET_KEY", "dev-secret-key"),
        "MAX_CONTENT_LENGTH": 10 * 1024 * 1024,  # 10MB
        "DEBUG": flask_env == "development"
    })
    
    # 로깅 설정
    setup_logging(app)
    
    # CORS 설정
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    CORS(app, resources={
        r"/api/*": {
            "origins": frontend_url,
            "methods": ["GET", "POST"],
            "allow_headers": ["Content-Type"]
        }
    })
    
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
    
    app.register_blueprint(face_bp, url_prefix="/api/v1/face")
    app.register_blueprint(hand_bp, url_prefix="/api/v1/hand")
    app.register_blueprint(ocr_bp, url_prefix="/api/v1/ocr")
    app.register_blueprint(image_sanitize_bp, url_prefix="/api/v1/images")
    app.register_blueprint(integrated_filter_bp, url_prefix="/api/v1/filter")
    app.register_blueprint(integrated_analysis_bp, url_prefix="/api/v1/analyze")  
    
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
    
    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"서버 오류: {error}")
        return jsonify({"success": False, "error": "서버 내부 오류가 발생했습니다", "code": 500}), 500
    
    return app
