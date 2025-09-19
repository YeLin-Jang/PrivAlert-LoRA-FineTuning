import os
from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
from flasgger.utils import swag_from
from app.utils.image_sanitize import sanitize_image
from config import DOCS_DIR

image_sanitize_bp = Blueprint("image_sanitize", __name__, url_prefix="/images")

def _boolean(val: str | None, default: bool = True) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}

@image_sanitize_bp.route('/sanitize', methods=['POST'])
@swag_from(os.path.join(DOCS_DIR, "image_sanitize_download.yml"))
def sanitize_download():
    """이미지 sanitize 후 파일 다운로드"""
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

    mime_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "heic": "image/heic",
    }
    mimetype = mime_map.get(ext, f"image/{ext}")

    return send_file(bio, mimetype=mimetype, as_attachment=True, download_name=f'sanitized.{ext}')

@image_sanitize_bp.route('/sanitize:report', methods=['POST'])
@swag_from(os.path.join(DOCS_DIR, "image_sanitize_report.yml"))
def sanitize_report():
    """이미지 sanitize 리포트 반환"""
    if 'file' not in request.files:
        return jsonify({"error": "file is required"}), 400
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({"error": "empty file"}), 400

    raw = file.read()
    target_format = request.form.get('target_format')
    keep_icc = _boolean(request.form.get('keep_icc'), True)

    _, _, report = sanitize_image(raw, keep_icc=keep_icc, target_format=target_format)
    return jsonify(report)
