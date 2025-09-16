import os
from flask import Flask
from flasgger import Swagger
from flasgger.utils import swag_from
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

def create_app(config_name=None):
    """Flask 앱 생성"""
    app = Flask(__name__)
    
    # 기본 설정 (환경변수 사용)
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'privalert-dev-key')
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
    
    # 환경 설정 (FLASK_ENV 사용)
    flask_env = os.getenv('FLASK_ENV', 'development')
    if flask_env == 'production':
        app.config['DEBUG'] = False
    else:
        app.config['DEBUG'] = True
    
    # CORS 설정
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    CORS(app, resources={r"/api/*": {"origins": frontend_url}})
    
    # Swagger 설정 (PORT 환경변수 사용)
    port = os.getenv('PORT', '5000')
    swagger_config = {
        "headers": [],
        "specs": [{
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/api-docs/"
    }
    
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "PrivAlert API",
            "description": "개인정보 보호 및 AI 서비스",
            "version": "1.0.0"
        },
        "host": f"localhost:{port}",
        "basePath": "/",
        "schemes": ["http"],
        "produces": ["application/json"]
    }
    
    Swagger(app, config=swagger_config, template=swagger_template)
    
    # Blueprint 등록
    from app.routes.face_routes import face_bp
    app.register_blueprint(face_bp, url_prefix='/api/face')
    
    # main.py가 있다면 등록 (선택사항)
    try:
        from app.routes.main import main_bp
        app.register_blueprint(main_bp)
    except ImportError:
        pass  # main.py가 없어도 괜찮음
    
    # 기본 라우트들
    @app.route('/')
    def index():
        return {
            'service': 'PrivAlert',
            'description': '개인정보 보호 및 AI 서비스',
            'version': '1.0.0',
            'docs': '/api-docs/',
            'status': 'running'
        }
    
    @app.route('/health')
    @swag_from({
        "tags": ["System"],
        "summary": "전체 시스템 상태",
        "responses": {200: {"description": "정상"}}
    })
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
