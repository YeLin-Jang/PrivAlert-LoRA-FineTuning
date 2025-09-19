import os

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
