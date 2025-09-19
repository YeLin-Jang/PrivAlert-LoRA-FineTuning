import os
import logging
from flask import Blueprint, request, jsonify
from flasgger.utils import swag_from
from app.services.ocr_service import OCRService
from app.utils.file_utils import save_path_with_timestamp, save_json_with_timestamp
from config import DOCS_DIR, BASE_DIR
from app import BASE_DATA_DIR

logger = logging.getLogger(__name__)

ocr_bp = Blueprint("ocr", __name__, url_prefix="/ocr")
ocr_service = OCRService()

@ocr_bp.route("/text", methods=["POST"])
@swag_from(os.path.join(DOCS_DIR, "ocr.yml"))
def extract_text():
    """이미지에서 텍스트 추출 API"""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "파일이 필요합니다"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"success": False, "error": "파일명이 필요합니다"}), 400

    temp_dir = os.path.join(BASE_DATA_DIR, "ocr")
    os.makedirs(temp_dir, exist_ok=True)
    save_path = save_path_with_timestamp(temp_dir, prefix="ocr", ext=".jpg")

    try:
        file.save(save_path)
        text = ocr_service.detect_text(save_path)

        if text:
            result = {
                "success": True,
                "count": 1,
                "text": text,
                "char_count": len(text),
                "line_count": len(text.split('\n')),
                "message": f"텍스트가 감지되었습니다 ({len(text)}자)"
            }

            # OCR 결과를 static/temp에 JSON 파일로 저장 (경로 + URL 반환)
            saved = save_json_with_timestamp(
                os.path.join(BASE_DATA_DIR, "ocr"),
                result,
                prefix="ocr_result"
            )

            logger.info(f"OCR 결과 저장됨: {saved['path']} (url={saved['url']})")

            # 응답에 file_url 포함
            return jsonify({**result, "file_url": saved["url"]})

        else:
            # 텍스트가 감지되지 않아도 200 OK 반환
            result = {
                "success": True,
                "count": 0,
                "text": "",
                "char_count": 0,
                "line_count": 0,
                "message": "텍스트가 발견되지 않았습니다"
            }
            return jsonify(result)

    except Exception as e:
        logger.error(f"OCR 오류: {e}")
        return jsonify({"success": False, "error": "서버 오류가 발생했습니다"}), 500

    finally:
        if os.path.exists(save_path):
            try:
                os.remove(save_path)
            except Exception as e:
                logger.warning(f"임시 파일 삭제 실패: {e}")
