import os
from flask import Blueprint, request, jsonify
from flasgger.utils import swag_from
from app.services.face_detection import FaceDetectionService
from config import DOCS_DIR

face_bp = Blueprint("face", __name__)
face_service = FaceDetectionService()

@face_bp.route("/detect", methods=["POST"])
@swag_from(os.path.join(DOCS_DIR, "face.yml"))
def detect_face():
    """얼굴 검출 API (Mediapipe 기반)"""
    if "image" not in request.files:
        return jsonify({"success": False, "error": "이미지 파일이 필요합니다"}), 400

    image_file = request.files["image"]
    result = face_service.detect_faces(image_file)

    if result.get("result_image_url"):
        result["result_image_url"] = request.host_url.rstrip("/") + result["result_image_url"]

    return jsonify(result), (200 if result.get("success") else 500)
