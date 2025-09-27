import os
from flask import Blueprint, request, jsonify, send_file
from io import BytesIO
import cv2
from flasgger.utils import swag_from
from app.services.hand_detection_service import HandDetectionService
from config import DOCS_DIR

hand_bp = Blueprint("hand", __name__)
hand_service = HandDetectionService()

@hand_bp.route("/detect", methods=["POST"])
@swag_from(os.path.join(DOCS_DIR, "hand.yml"))
def detect_fingertips():
    """손가락 끝 검출 API"""
    if "image" not in request.files:
        return jsonify({"success": False, "error": "이미지 파일 필요"}), 400

    image_file = request.files["image"]
    return_image = request.form.get('return_image', 'false').lower() in ['true', '1', 'yes']
    
    if return_image:
        result, preview_img = hand_service.detect_fingertips(image_file, save_preview=True, return_image=True)
        if result.get("success"):
            # 이미지를 PNG 형식으로 인코딩하여 반환
            _, buffer = cv2.imencode('.png', preview_img)
            bio = BytesIO(buffer)
            bio.seek(0)
            return send_file(bio, mimetype='image/png', as_attachment=True, download_name='hand_detection_result.png')
        else:
            return jsonify(result), 500
    else:
        result = hand_service.detect_fingertips(image_file, save_preview=True)
        if result.get("result_image_url"):
            result["result_image_url"] = request.host_url.rstrip("/") + result["result_image_url"]
        return jsonify(result), (200 if result.get("success") else 500)
