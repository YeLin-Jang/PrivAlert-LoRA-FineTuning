import os
from dotenv import load_dotenv
from app import create_app

load_dotenv()

app = create_app()

if __name__ == '__main__':
    # 환경변수에서 포트 가져오기
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    app.run(host='0.0.0.0', port=port, debug=debug)