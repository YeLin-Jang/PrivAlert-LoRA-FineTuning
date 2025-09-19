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
    }, template={
        "swagger": "2.0",
        "info": {
            "title": "PrivAlert API",
            "description": "개인정보 탐지 및 분석 API",
            "version": "1.0.0",
        },
        "host": f"localhost:{port}",
        "basePath": "/",
        "schemes": ["http"],
        "produces": ["application/json"],
    })
    
    # 필요한 디렉토리 생성 (face, hand, ocr)
    required_dirs = [
        os.path.join(BASE_DATA_DIR, "face"),
        os.path.join(BASE_DATA_DIR, "hand"),
        os.path.join(BASE_DATA_DIR, "ocr"),
    ]
    for d in required_dirs:
        ensure_dir(d)
    
    # 블루프린트 등록
    from app.routes.face_routes import face_bp
    from app.routes.hand_routes import hand_bp
    from app.routes.ocr_routes import ocr_bp
    
    app.register_blueprint(face_bp, url_prefix="/api/face")
    app.register_blueprint(hand_bp, url_prefix="/api/hand")
    app.register_blueprint(ocr_bp, url_prefix="/api")
    
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
