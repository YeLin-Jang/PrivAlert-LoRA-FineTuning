import os
import logging
from flask import Blueprint, request, jsonify
from flasgger.utils import swag_from
from app.services.ocr_service import OCRService
from app.utils.file_utils import save_path_with_timestamp, save_json_with_timestamp
from app.utils.security_utils import validate_image_file, get_safe_file_path, mask_sensitive_data_in_log
from config import DOCS_DIR, BASE_DIR
from app import BASE_DATA_DIR

logger = logging.getLogger(__name__)

ocr_bp = Blueprint("ocr", __name__)
ocr_service = OCRService()

@ocr_bp.route("/text", methods=["POST"])
@swag_from(os.path.join(DOCS_DIR, "ocr.yml"))
def extract_text():
    """이미지에서 텍스트 추출 API"""
    save_path = None
    try:
        if "file" not in request.files:
            return jsonify({"success": False, "error": "파일이 필요합니다"}), 400

        file = request.files["file"]
        
        # 보안: 파일 검증
        is_valid, error_msg = validate_image_file(file)
        if not is_valid:
            logger.warning(f"파일 검증 실패: {mask_sensitive_data_in_log(error_msg or '')}")
            return jsonify({"success": False, "error": error_msg}), 400

        # 보안: 안전한 파일 경로 생성
        temp_dir = os.path.join(BASE_DATA_DIR, "ocr")
        os.makedirs(temp_dir, exist_ok=True)
        save_path = get_safe_file_path(temp_dir, file.filename or "file", prefix="ocr")

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

            logger.info("OCR 결과 저장됨: %s", saved['path'])

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
        logger.error(f"OCR 오류: {e}", exc_info=True)
        return jsonify({"success": False, "error": "서버 오류가 발생했습니다"}), 500

    finally:
        # 보안: 임시 파일 안전 삭제
        if save_path and os.path.exists(save_path):
            try:
                os.remove(save_path)
                logger.debug("임시 OCR 파일 삭제 완료")
            except Exception as e:
                logger.warning(f"임시 파일 삭제 실패: {e}")
