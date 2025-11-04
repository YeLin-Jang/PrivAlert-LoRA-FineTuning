import os
from dotenv import load_dotenv
from pathlib import Path
from app import create_app
from werkzeug.serving import WSGIRequestHandler

# 환경변수 로드 (루트 디렉토리의 .env 파일)
root_dir = Path(__file__).parent.parent  # backend/wsgi.py -> 프로젝트 루트
env_path = root_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Werkzeug의 Server 헤더 제거를 위한 커스텀 핸들러
class CustomWSGIRequestHandler(WSGIRequestHandler):
    # Server 헤더를 완전히 제거하기 위한 여러 방법 조합
    
    def send_header(self, keyword, value):
        # Server 헤더는 전송하지 않음
        if keyword.lower() == 'server':
            return
        super().send_header(keyword, value)
    
    def end_headers(self):
        # end_headers 전에 Server 헤더 제거
        if hasattr(self, '_headers_buffer'):
            # _headers_buffer에서 Server 헤더 제거
            self._headers_buffer = [
                header for header in self._headers_buffer 
                if not header.startswith(b'Server:')
            ]
        super().end_headers()
    
    def version_string(self):
        # 버전 문자열을 빈 문자열로 반환하여 Server 헤더에 버전 정보가 포함되지 않도록 함
        return ''
    
    @property
    def server_version(self):
        # server_version property를 빈 문자열로 반환
        return ''

app = create_app()

if __name__ == '__main__':
    # 환경변수에서 포트 가져오기
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    # 커스텀 핸들러를 사용하여 서버 실행
    # app.run()에 request_handler 옵션 전달
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        request_handler=CustomWSGIRequestHandler
    )