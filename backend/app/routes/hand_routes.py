import os
from flask import Blueprint, request, jsonify
from flasgger.utils import swag_from
from app.services.hand_detection import HandDetectionService
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
    result = hand_service.detect_fingertips(image_file, save_preview=True)

    if result.get("result_image_url"):
        result["result_image_url"] = request.host_url.rstrip("/") + result["result_image_url"]

    return jsonify(result), (200 if result.get("success") else 500)
