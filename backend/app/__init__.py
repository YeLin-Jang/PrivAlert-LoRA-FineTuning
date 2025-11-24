import os
import logging
import warnings
from datetime import timedelta
from flask import Flask, jsonify

# TensorFlow/MediaPipe 경고 억제
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # ERROR만 출력
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', message='.*TensorFlow.*')
warnings.filterwarnings('ignore', message='.*MediaPipe.*')

# APScheduler 로그 억제
logging.getLogger('apscheduler').setLevel(logging.WARNING)
from flasgger import Swagger
from dotenv import load_dotenv
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.utils.file_utils import ensure_dir
from app.extensions.database import init_db, db
from config import BASE_DATA_DIR

# 환경변수 로드 (루트 디렉토리의 .env 파일)
# 프로젝트 루트로 이동하여 .env 파일 찾기
from pathlib import Path
root_dir = Path(__file__).parent.parent.parent  # backend/app/__init__.py -> 프로젝트 루트
env_path = root_dir / '.env'
load_dotenv(dotenv_path=env_path)

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

    app = Flask(__name__)
    
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

        # 세션 보안 설정 (HTTP 전용 환경)
        # 중요: HTTP 환경이므로 Secure 플래그는 False로 설정
        # 보안: HttpOnly, SameSite=Strict로 최대한 보호
        "SESSION_COOKIE_SECURE": False,  # HTTP 환경이므로 Secure 미설정
        "SESSION_COOKIE_HTTPONLY": True,  # JavaScript에서 쿠키 접근 방지
        "SESSION_COOKIE_SAMESITE": "Strict",  # CSRF 공격 방지 (HTTP 환경에서는 Strict 권장)
        # 세션 만료 시간 설정 (보안: 최소화, 환경 변수로 제어 가능)
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=int(os.getenv("SESSION_LIFETIME_HOURS", "24"))),  # 기본 24시간
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
            "allow_headers": ["Content-Type", "Authorization", "X-CSRF-Token"],
            "supports_credentials": True,  # 세션 쿠키 전송을 위해 항상 True (개발/운영 환경 모두)
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
    # CSRF 보호: 프로덕션에서는 활성화, 개발 환경에서는 선택적
    app.config["JWT_COOKIE_CSRF_PROTECT"] = flask_env == "production"
    app.config["JWT_COOKIE_SECURE"] = False  # HTTP 환경이므로 Secure 미설정
    app.config["JWT_COOKIE_HTTPONLY"] = True
    app.config["JWT_COOKIE_SAMESITE"] = "Strict"  # CSRF 공격 방지 (HTTP 환경에서는 Strict 권장)
    
    JWTManager(app)  # JWT 초기화 (변수 할당 불필요)
    
    # 데이터베이스 초기화
    # 보안: Docker 환경 감지 및 MySQL 호스트 설정
    # Docker 컨테이너 내부에서는 'mysql' 호스트 사용 (Docker 네트워크)
    # 로컬 실행 시에는 환경 변수에 따라 설정 (기본값: localhost)
    is_docker_container = os.path.exists('/.dockerenv') or os.getenv('DOCKER_ENV') == 'true'
    
    if is_docker_container:
        # Docker 컨테이너 내부: 'mysql' 호스트 사용 (보안: 내부 네트워크만)
        if os.getenv('MYSQL_HOST') != 'mysql':
            app.logger.warning(f"Docker 환경에서 MYSQL_HOST가 'mysql'이 아닙니다: {os.getenv('MYSQL_HOST')}")
        app.logger.info("Docker 컨테이너 환경 감지: MySQL 호스트 'mysql' 사용 (내부 네트워크)")
    else:
        # 로컬 실행 환경: 'mysql' 호스트를 'localhost'로 자동 변경
        mysql_host = os.getenv('MYSQL_HOST', 'localhost')
        if mysql_host == 'mysql':
            app.logger.warning(
                "로컬 실행 환경에서 MYSQL_HOST='mysql'로 설정되어 있습니다. "
                "자동으로 'localhost'로 변경합니다."
            )
            os.environ['MYSQL_HOST'] = 'localhost'
            mysql_host = 'localhost'
        app.logger.info(f"로컬 실행 환경: MySQL 호스트 '{mysql_host}' 사용")
    
    # 보안: 데이터베이스 연결 시도
    try:
        init_db(app)
        app.logger.info("데이터베이스 연결 성공")
    except Exception as e:
        error_msg = str(e)
        app.logger.error(
            f"데이터베이스 연결 실패: {error_msg} | "
            f"호스트: {os.getenv('MYSQL_HOST', 'localhost')}:{os.getenv('MYSQL_PORT', '3306')} | "
            f"DB: {os.getenv('MYSQL_DATABASE', 'privalert')} | "
            f"사용자: {os.getenv('MYSQL_USER', 'privalert_user')} | "
            f"해결: MySQL 서버 실행 확인 및 .env 파일 확인"
        )
        # 보안: 프로덕션 환경에서는 데이터베이스 연결 실패 시 중단
        if flask_env == "production":
            raise
        else:
            # 개발 환경에서는 경고만 출력하고 계속 진행
            app.logger.warning("개발 환경: 데이터베이스 연결 실패했지만 계속 진행합니다")
    
    # Rate Limiter 설정
    # Redis 사용 여부는 환경 변수로 제어 (REDIS_URL이 설정되어 있으면 Redis 사용)
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        storage_uri = redis_url
        app.logger.info(f"Rate Limiter: Redis 사용 ({redis_url})")
    else:
        storage_uri = "memory://"
        app.logger.warning("Rate Limiter: 메모리 기반 사용 (프로덕션에서는 REDIS_URL 설정 권장)")
    
    # Rate Limiter 제한값 설정 (환경 변수로 제어 가능)
    rate_limit_per_hour = os.getenv("RATE_LIMIT_PER_HOUR", "1000")
    rate_limit_per_minute = os.getenv("RATE_LIMIT_PER_MINUTE", "100")
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[f"{rate_limit_per_hour} per hour", f"{rate_limit_per_minute} per minute"],
        storage_uri=storage_uri
    )
    
    # 보안 헤더 설정
    from app.utils.security_headers import setup_security_headers
    setup_security_headers(app)
    
    # 헬스체크 엔드포인트 (Docker healthcheck용)
    @app.route('/health', methods=['GET'])
    def health_check():
        """
        헬스체크 엔드포인트
        보안: 민감 정보 노출 방지
        """
        from app.utils.api_utils import APIResponse
        try:
            # 데이터베이스 연결 확인
            db_status = "healthy"
            try:
                from sqlalchemy import text
                db.session.execute(text("SELECT 1"))
            except Exception as e:
                app.logger.warning(f"데이터베이스 연결 확인 실패: {e}")
                db_status = "unhealthy"
            
            status_code = 200 if db_status == "healthy" else 503
            return APIResponse.success(
                data={
                    "status": "healthy" if db_status == "healthy" else "degraded",
                    "database": db_status,
                    "service": "PrivAlert Backend"
                },
                status_code=status_code
            )
        except Exception as e:
            app.logger.error(f"헬스체크 오류: {e}")
            return APIResponse.error("Internal error", code=503)
    
    # data 디렉토리도 정적 파일로 서빙 (원본 파일용)
    # 보안: 경로 조작 방지
    from flask import send_from_directory, abort
    from app.utils.security_utils import validate_path
    
    @app.route('/data/results/<path:filename>')
    def serve_data(filename):
        """보안이 적용된 정적 파일 서빙"""
        from flask import request
        from app.utils.file_cleanup import cleanup_file
        
        # 경로 조작 방지
        # filename은 results/ 하위의 상대 경로 (예: image/sanitized_xxx.png)
        is_valid, error = validate_path(BASE_DATA_DIR, filename)
        if not is_valid:
            app.logger.warning(f"경로 조작 시도 감지: {filename}")
            abort(403)
        
        try:
            # 다운로드 모드 확인 (download 파라미터가 있으면 다운로드 후 삭제)
            is_download = request.args.get('download', '').lower() == 'true'
            
            response = send_from_directory(
                BASE_DATA_DIR, 
                filename,
                as_attachment=is_download  # 다운로드 모드면 attachment로 설정
            )
            # 보안 헤더는 @app.after_request에서 자동 적용됨
            
            # 다운로드 모드이고 삭제 플래그가 있으면 다운로드 후 삭제
            if is_download and request.args.get('delete', '').lower() == 'true':
                file_path = os.path.join(BASE_DATA_DIR, filename)
                abs_path = os.path.abspath(file_path)
                
                # 보안: 경로 재검증
                base_abs = os.path.abspath(BASE_DATA_DIR)
                if abs_path.startswith(base_abs) and os.path.exists(abs_path):
                    # 다운로드 완료 후 파일 삭제 (백그라운드에서)
                    import threading
                    def delayed_delete():
                        import time
                        time.sleep(2)  # 다운로드 완료 대기
                        cleanup_file(abs_path, BASE_DATA_DIR)
                    
                    thread = threading.Thread(target=delayed_delete, daemon=True)
                    thread.start()
            
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
    from app.routes.secure_upload_routes import secure_upload_bp
    from app.routes.auth_routes import auth_bp
    # 사용자 관련 라우트 (기능별로 분리)
    from app.routes.user_profile_routes import user_profile_bp
    from app.routes.user_session_routes import user_session_bp
    from app.routes.user_settings_routes import user_settings_bp
    from app.routes.user_history_routes import user_history_bp
    
    # NER 라우트 등록 (선택적 - 모델이 없는 경우에도 앱이 실행되도록)
    try:
        from app.routes.ner_routes import ner_bp
        app.register_blueprint(ner_bp, url_prefix="/api/ner")
        app.logger.info("NER routes registered successfully")
    except ImportError as e:
        app.logger.warning(f"NER routes not available (ImportError): {e}")
    except Exception as e:
        app.logger.warning(f"NER routes not available (Error): {e}")

    # 비디오 처리 라우트 등록 (선택적 - easyocr 등 의존성이 없는 경우에도 앱이 실행되도록)
    try:
        from app.routes.video_processing_routes import video_bp
        app.register_blueprint(video_bp, url_prefix="/api/v1/video")
        app.logger.info("Video processing routes registered successfully")
    except ImportError as e:
        app.logger.warning(f"Video processing routes not available (ImportError): {e}")
    except Exception as e:
        app.logger.warning(f"Video processing routes not available (Error): {e}")

    
    app.register_blueprint(integrated_filter_bp, url_prefix="/api/v1/filter")
    app.register_blueprint(integrated_analysis_bp, url_prefix="/api/v1")
    app.register_blueprint(education_bp, url_prefix="/api/v1/education")
    app.register_blueprint(workplace_bp, url_prefix="/api/v1/workplace")
    app.register_blueprint(name_detection_bp, url_prefix="/api/v1/name")
    app.register_blueprint(secure_upload_bp, url_prefix="/api/v1")  
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    # 사용자 관련 라우트 등록
    app.register_blueprint(user_profile_bp, url_prefix="/api/v1/user")
    app.register_blueprint(user_session_bp, url_prefix="/api/v1/user")
    app.register_blueprint(user_settings_bp, url_prefix="/api/v1/user")
    app.register_blueprint(user_history_bp, url_prefix="/api/v1/user")
    
    # 보안: 인증 관련 엔드포인트에 더 엄격한 Rate Limiting 적용 (라우트 등록 후)
    try:
        # 회원가입: 분당 5회 제한
        limiter.limit("5 per minute")(auth_bp.view_functions['signup'])
        # 로그인: 분당 10회 제한 (브루트포스 공격 방지)
        limiter.limit("10 per minute")(auth_bp.view_functions['login'])
    except (KeyError, AttributeError):
        # 라우트가 아직 등록되지 않은 경우 조용히 무시
        pass
    
    # 보안: 인증된 사용자 API 엔드포인트에 대해 더 관대한 Rate Limiting 적용
    # 인증된 사용자는 브루트포스 공격 위험이 낮고, 정상적인 사용 활동을 방해하지 않도록 설정
    try:
        # 사용자 필터링 설정 조회/수정: 분당 30회 제한
        if 'get_filtering_settings' in user_settings_bp.view_functions:
            limiter.limit("30 per minute")(user_settings_bp.view_functions['get_filtering_settings'])
        if 'update_filtering_settings' in user_settings_bp.view_functions:
            limiter.limit("30 per minute")(user_settings_bp.view_functions['update_filtering_settings'])
        # 사용자 정보 조회: 분당 60회 제한
        if 'get_profile' in user_profile_bp.view_functions:
            limiter.limit("60 per minute")(user_profile_bp.view_functions['get_profile'])
        # 수정 기록 조회: 분당 30회 제한
        if 'get_revision_history' in user_history_bp.view_functions:
            limiter.limit("30 per minute")(user_history_bp.view_functions['get_revision_history'])
    except (KeyError, AttributeError):
        # 라우트가 아직 등록되지 않은 경우 조용히 무시
        pass
    
    # 데이터베이스 및 백그라운드 작업 초기화
    from app.utils.app_initialization import initialize_database, initialize_background_tasks
    initialize_database(app)
    initialize_background_tasks(app)  
    
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
                "name_detection": "/api/v1/name"
            }
        })
    
    # 에러 핸들러 등록
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    return app
