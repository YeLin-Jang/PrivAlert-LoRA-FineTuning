import os
from dotenv import load_dotenv

# 프로젝트 루트 경로 찾기 (PrivAlert/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT_DIR, '.env')

# 프로젝트 루트의 .env 파일 우선 로드
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)
else:
    # Fallback: 현재 디렉토리의 .env 파일
    load_dotenv()

# 프로젝트 루트 디렉토리
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Swagger 문서 경로
DOCS_DIR = os.path.join(BASE_DIR, "docs")

# 민감 데이터 저장 루트
BASE_DATA_DIR = os.path.join(BASE_DIR, "data", "results")

# 하위 디렉토리 (face / hand / ocr)
FACE_DIR = os.path.join(BASE_DATA_DIR, "face")
HAND_DIR = os.path.join(BASE_DATA_DIR, "hand")
OCR_DIR  = os.path.join(BASE_DATA_DIR, "ocr")

# 필요한 디렉토리 자동 생성
for d in [FACE_DIR, HAND_DIR, OCR_DIR]:
    os.makedirs(d, exist_ok=True)

# 데이터베이스 설정
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or \
    f"mysql+pymysql://{os.getenv('DB_USER', 'app_user')}:{os.getenv('DB_PASSWORD', '')}@" \
    f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'privalert')}"

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = os.getenv('FLASK_ENV') == 'development'
