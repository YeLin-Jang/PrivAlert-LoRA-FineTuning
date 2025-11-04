import os
import logging
from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
from flasgger.utils import swag_from
from app.utils.image_sanitize import sanitize_image
from app.utils.security_utils import validate_image_file, mask_sensitive_data_in_log
from config import DOCS_DIR

logger = logging.getLogger(__name__)

image_sanitize_bp = Blueprint("image_sanitize", __name__)

def _boolean(val: str | None, default: bool = True) -> bool:
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "y", "on"}

@image_sanitize_bp.route('/sanitize', methods=['POST'])
@swag_from(os.path.join(DOCS_DIR, "image_sanitize_download.yml"))
def sanitize_download():
    """이미지 sanitize 후 파일 다운로드"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "file is required"}), 400
        
        file = request.files['file']
        
        # 보안: 파일 검증
        is_valid, error_msg = validate_image_file(file)
        if not is_valid:
            logger.warning(f"파일 검증 실패: {mask_sensitive_data_in_log(error_msg or '')}")
            return jsonify({"error": error_msg}), 400

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
    
    except Exception as e:
        logger.error(f"이미지 정제 중 오류: {e}", exc_info=True)
        return jsonify({"error": "서버 오류가 발생했습니다"}), 500

@image_sanitize_bp.route('/sanitize:report', methods=['POST'])
@swag_from(os.path.join(DOCS_DIR, "image_sanitize_report.yml"))
def sanitize_report():
    """이미지 sanitize 리포트 반환"""
    try:
        if 'file' not in request.files:
            return jsonify({"error": "file is required"}), 400
        
        file = request.files['file']
        
        # 보안: 파일 검증
        is_valid, error_msg = validate_image_file(file)
        if not is_valid:
            logger.warning(f"파일 검증 실패: {mask_sensitive_data_in_log(error_msg or '')}")
            return jsonify({"error": error_msg}), 400

        raw = file.read()
        target_format = request.form.get('target_format')
        keep_icc = _boolean(request.form.get('keep_icc'), True)

        _, _, report = sanitize_image(raw, keep_icc=keep_icc, target_format=target_format)
        return jsonify(report)
    
    except Exception as e:
        logger.error(f"이미지 정제 리포트 생성 중 오류: {e}", exc_info=True)
        return jsonify({"error": "서버 오류가 발생했습니다"}), 500
