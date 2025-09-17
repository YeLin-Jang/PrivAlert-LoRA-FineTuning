from flask import Blueprint, request, jsonify
from flasgger.utils import swag_from
from app.services.hand_detection import HandDetectionService

hand_bp = Blueprint("hand", __name__)
hand_service = HandDetectionService()

@hand_bp.route("/detect", methods=["POST"])
@swag_from({
    "tags": ["Hand/Fingerprint"],
    "summary": "손가락 끝(지문 노출 가능 영역) 탐지",
    "consumes": ["multipart/form-data"],
    "parameters": [
        {"name": "image", "in": "formData", "type": "file", "required": True, "description": "이미지 파일"}
    ],
    "responses": {
        200: {"description": "탐지 성공"},
        400: {"description": "잘못된 요청"},
        500: {"description": "서버 오류"}
    }
})
def detect_fingertips():
    if "image" not in request.files:
        return jsonify({"success": False, "error": "이미지 파일 필요"}), 400

    image_file = request.files["image"]
    result = hand_service.detect_fingertips(image_file, save_preview=True)

    if result.get("result_image_url"):
        result["result_image_url"] = request.host_url.rstrip("/") + result["result_image_url"]

    return jsonify(result), (200 if result.get("success") else 500)
