import os
import logging
from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("Warning: OpenCV not available. Face detection will be limited.")
from flasgger.utils import swag_from
from app.services.face_detection_service import FaceDetectionService
from app.utils.security_utils import validate_image_file, mask_sensitive_data_in_log
from config import DOCS_DIR

logger = logging.getLogger(__name__)

face_bp = Blueprint("face", __name__)
face_service = FaceDetectionService()

@face_bp.route("/detect", methods=["POST"])
@swag_from(os.path.join(DOCS_DIR, "face.yml"))
def detect_face():
    """얼굴 검출 API (Mediapipe 기반)"""
    try:
        if "image" not in request.files:
            return jsonify({"success": False, "error": "이미지 파일이 필요합니다"}), 400

        image_file = request.files["image"]
        
        # 보안: 파일 검증
        is_valid, error_msg = validate_image_file(image_file)
        if not is_valid:
            logger.warning(f"파일 검증 실패: {mask_sensitive_data_in_log(error_msg or '')}")
            return jsonify({"success": False, "error": error_msg}), 400
        
        return_image = request.form.get('return_image', 'false').lower() in ['true', '1', 'yes']
        
        if return_image:
            result, preview_img = face_service.detect_faces(image_file, return_image=True)
            if result.get("success"):
                # 이미지를 PNG 형식으로 인코딩하여 반환
                _, buffer = cv2.imencode('.png', preview_img)
                bio = BytesIO(buffer)
                bio.seek(0)
                return send_file(bio, mimetype='image/png', as_attachment=True, download_name='face_detection_result.png')
            else:
                return jsonify(result), 500
        else:
            result = face_service.detect_faces(image_file)
            if result.get("result_image_url"):
                result["result_image_url"] = request.host_url.rstrip("/") + result["result_image_url"]
            return jsonify(result), (200 if result.get("success") else 500)
    
    except Exception as e:
        logger.error(f"얼굴 검출 중 오류: {e}", exc_info=True)
        return jsonify({"success": False, "error": "서버 오류가 발생했습니다"}), 500
