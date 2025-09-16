from flask import Blueprint, request, jsonify
from flasgger.utils import swag_from
from app.services.face_detection import FaceDetectionService

face_bp = Blueprint("face", __name__)
face_service = FaceDetectionService()

@face_bp.route("/detect", methods=["POST"])
@swag_from({
    "tags": ["Face Detection"],
    "summary": "얼굴 검출 (Mediapipe)",
    "consumes": ["multipart/form-data"],
    "parameters": [
        {
            "name": "image",
            "in": "formData",
            "type": "file",
            "required": True,
            "description": "얼굴이 포함된 이미지 파일 (jpg, png 등)"
        }
    ],
    "responses": {
        200: {
            "description": "얼굴 검출 성공",
            "examples": {
                "application/json": {
                    "success": True,
                    "count": 1,
                    "faces": [
                        {
                            "index": 1,
                            "box": {"x": 123, "y": 45, "w": 220, "h": 220},
                            "score": 0.985
                        }
                    ],
                    "message": "1개의 얼굴이 감지되었습니다",
                    "result_image_url": "http://localhost:5000/static/results/face_abc123.jpg"
                }
            }
        },
        400: {"description": "잘못된 요청"},
        500: {"description": "서버 오류"}
    }
})
def detect_face():
    """얼굴 검출 API"""
    if "image" not in request.files:
        return jsonify({"success": False, "error": "이미지 파일이 필요합니다"}), 400

    image_file = request.files["image"]
    result = face_service.detect_faces(image_file)

    # URL 절대 경로 보정
    if result.get("result_image_url"):
        result["result_image_url"] = request.host_url.rstrip("/") + result["result_image_url"]

    return jsonify(result), (200 if result.get("success") else 500)
