from flask import Flask, request, jsonify, send_file
from dotenv import load_dotenv
import os
from io import BytesIO

from utils.image_sanitize import sanitize_image

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


def _boolean(val: str | None, default: bool = True) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}


@app.route('/api/v1/images/sanitize', methods=['POST'])
def api_sanitize_download():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "file is required"}), 400
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "empty file"}), 400

        raw = file.read()
        target_format = request.form.get('target_format')
        keep_icc = _boolean(request.form.get('keep_icc'), True)

        data, ext, report = sanitize_image(raw, keep_icc=keep_icc, target_format=target_format)
        bio = BytesIO(data)
        bio.seek(0)
        # 파일명은 고정 프리픽스 + 확장자만, MIME은 표준으로 매핑
        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "heic": "image/heic",
        }
        mimetype = mime_map.get(ext, f"image/{ext}")
        return send_file(bio, mimetype=mimetype, as_attachment=True, download_name=f'sanitized.{ext}')
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/v1/images/sanitize:report', methods=['POST'])
def api_sanitize_report():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "file is required"}), 400
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({"error": "empty file"}), 400

        raw = file.read()
        target_format = request.form.get('target_format')
        keep_icc = _boolean(request.form.get('keep_icc'), True)

        data, ext, report = sanitize_image(raw, keep_icc=keep_icc, target_format=target_format)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == '__main__':
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
