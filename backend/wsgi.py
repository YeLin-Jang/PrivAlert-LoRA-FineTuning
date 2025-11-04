import os
from dotenv import load_dotenv
from app import create_app

# 프로젝트 루트 경로 찾기 (PrivAlert/)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(ROOT_DIR, '.env')

# 프로젝트 루트의 .env 파일 우선 로드
if os.path.exists(ENV_FILE):
    load_dotenv(ENV_FILE)
else:
    # Fallback: 현재 디렉토리의 .env 파일
    load_dotenv()

app = create_app()

if __name__ == '__main__':
    # 환경변수에서 포트 가져오기
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)