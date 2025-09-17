import os
from flask import Flask
from flasgger import Swagger
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()


def create_app(config_name=None):
    """Flask 애플리케이션 팩토리"""
    app = Flask(__name__)

    # 기본 설정
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "privalert-dev-key")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB

    # 환경 설정
    flask_env = os.getenv("FLASK_ENV", "development")
    app.config["DEBUG"] = flask_env != "production"

    # CORS 설정
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    CORS(app, resources={r"/api/*": {"origins": frontend_url}})

    # Swagger 설정
    port = os.getenv("PORT", "5000")
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api-docs/",
    }
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "PrivAlert API",
            "description": "도전~!!!! 보안벨!!!!!",
            "version": "1.0.0",
        },
        "host": f"localhost:{port}",
        "basePath": "/",
        "schemes": ["http"],
        "produces": ["application/json"],
    }
    Swagger(app, config=swagger_config, template=swagger_template)

    # --- 블루프린트 등록 ---
    from app.routes.face_routes import face_bp
    from app.routes.hand_routes import hand_bp

    app.register_blueprint(face_bp, url_prefix="/api/face")
    app.register_blueprint(hand_bp, url_prefix="/api/hand")

    # 기본 라우트 (상태 확인용)
    @app.route("/health")
    def health():
        return {"status": "ok", "service": "PrivAlert"}

    # 에러 핸들러
    @app.errorhandler(404)
    def not_found(error):
        return {"success": False, "error": "페이지를 찾을 수 없습니다", "code": 404}, 404

    @app.errorhandler(413)
    def too_large(error):
        return {"success": False, "error": "파일이 너무 큽니다 (최대 10MB)", "code": 413}, 413

    @app.errorhandler(500)
    def server_error(error):
        return {"success": False, "error": "서버 오류가 발생했습니다", "code": 500}, 500

    return app
