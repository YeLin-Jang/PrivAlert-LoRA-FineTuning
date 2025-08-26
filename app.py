from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)

@app.route('/')
def index():
    """메인 페이지"""
    return jsonify({
        "message": "PrivAlert API 서버가 실행 중입니다!",
        "status": "running",
        "version": "1.0.0"
    })


if __name__ == '__main__':
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
