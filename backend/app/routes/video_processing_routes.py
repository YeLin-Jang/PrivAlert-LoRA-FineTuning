"""
비디오 처리 API 라우트
"""

import os
import logging
from flask import Blueprint, request, jsonify
from flasgger.utils import swag_from
from app.services.video_processing_service import VideoProcessingService
from app.utils.api_utils import APIResponse
from config import DOCS_DIR

logger = logging.getLogger(__name__)

video_bp = Blueprint("video", __name__)
video_service = VideoProcessingService()


@video_bp.route("/analyze", methods=["POST"])
@swag_from(os.path.join(DOCS_DIR, "video_processing.yml"))
def analyze_video():
    """
    비디오 분석 API
    
    - 비디오에서 프레임 추출 및 분석 (OCR, 얼굴, 손가락 탐지)
    - 오디오 추출 및 음성 인식 (Whisper)
    """
    try:
        # 파일 검증
        if "video" not in request.files:
            return APIResponse.error("비디오 파일이 필요합니다", code=400)
        
        video_file = request.files["video"]
        if not video_file or not video_file.filename:
            return APIResponse.error("비디오 파일이 제공되지 않았습니다", code=400)
        
        # 파라미터 추출
        extract_audio = request.form.get("extract_audio", "true").lower() in ["true", "1", "yes"]
        process_frames = request.form.get("process_frames", "true").lower() in ["true", "1", "yes"]
        
        # 프레임 샘플링 간격 (초)
        try:
            frame_interval = float(request.form.get("frame_interval", "1.0"))
            if frame_interval <= 0:
                frame_interval = 1.0
        except (ValueError, TypeError):
            frame_interval = 1.0
        
        logger.info(
            f"비디오 분석 요청: {video_file.filename}, "
            f"오디오={extract_audio}, 프레임={process_frames}, 간격={frame_interval}초"
        )
        
        # 비디오 처리
        result = video_service.process_video(
            video_file=video_file,
            extract_audio=extract_audio,
            process_frames=process_frames,
            frame_interval=frame_interval
        )
        
        if result.get("success"):
            return jsonify(result), 200
        else:
            return APIResponse.error(
                result.get("error", "비디오 처리 실패"),
                code=500
            )
    
    except Exception as e:
        logger.error(f"비디오 분석 API 오류: {e}", exc_info=True)
        return APIResponse.server_error(f"비디오 분석 중 오류가 발생했습니다: {str(e)}")


@video_bp.route("/health", methods=["GET"])
def video_service_health():
    """비디오 처리 서비스 상태 확인"""
    try:
        # Whisper 모델 로드 시도
        video_service._load_whisper_model()
        whisper_available = True
    except Exception as e:
        logger.warning(f"Whisper 모델 로드 실패: {e}")
        whisper_available = False
    
    return jsonify({
        "service": "video_processing",
        "status": "healthy",
        "whisper_available": whisper_available,
        "supported_formats": list(video_service.ALLOWED_EXTENSIONS),
        "max_file_size_mb": video_service.MAX_FILE_SIZE / (1024 * 1024)
    }), 200

