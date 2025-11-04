"""
비디오 처리 서비스
- 비디오 프레임 추출 및 분석 (OCR, 얼굴, 손가락 탐지)
- 오디오 추출 및 음성 인식 (Whisper)

시큐어 코딩 가이드 준수:
- 파일 업로드 검증 (확장자, 크기)
- 경로 조작 방지 (Path 사용)
- 임시 파일 안전 관리 및 삭제
- 입력 검증 및 에러 처리
- 민감 정보 보호
"""

import os
import cv2  # type: ignore
import numpy as np
import logging
import tempfile
import shutil
from typing import Dict, List, Any, Optional, Tuple
from werkzeug.datastructures import FileStorage
from pathlib import Path

from app.services.ocr_service import OCRService
from app.services.face_detection_service import FaceDetectionService
from app.services.hand_detection_service import HandDetectionService
from app.services.integrated_filter_service import IntegratedFilterService
from app.utils.file_utils import save_json_with_timestamp

logger = logging.getLogger(__name__)


class VideoProcessingService:
    """비디오 처리 서비스"""
    
    # 허용된 비디오 확장자 (보안)
    ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
    
    # 최대 파일 크기 (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    # 프레임 샘플링 간격 (초) - 성능 최적화
    FRAME_SAMPLE_INTERVAL = 1.0
    
    def __init__(self):
        """서비스 초기화"""
        self.ocr_service = OCRService()
        self.face_service = FaceDetectionService()
        self.hand_service = HandDetectionService()
        self.filter_service = IntegratedFilterService()
        
        # Whisper 모델은 지연 로딩 (첫 사용 시 로드)
        self._whisper_model = None
        
        logger.info("비디오 처리 서비스 초기화 완료")
    
    def _validate_video_file(self, file: FileStorage) -> Tuple[bool, Optional[str]]:
        """
        비디오 파일 검증 (보안)
        
        시큐어 코딩 가이드 준수:
        - 파일 확장자 화이트리스트 검증
        - 파일 크기 제한 (DoS 공격 방지)
        - 경로 조작 방지 (Path 사용)
        
        Args:
            file: 업로드된 파일
            
        Returns:
            (유효성, 오류 메시지)
        """
        if not file or not file.filename:
            return False, "파일이 제공되지 않았습니다"
        
        # 파일 확장자 검증 (화이트리스트 방식)
        # Path 사용으로 경로 조작 방지
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in self.ALLOWED_EXTENSIONS:
            return False, f"지원하지 않는 파일 형식입니다. 허용된 형식: {', '.join(self.ALLOWED_EXTENSIONS)}"
        
        # 파일 크기 검증 (DoS 공격 방지)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)  # 파일 포인터 초기화
        
        if file_size > self.MAX_FILE_SIZE:
            return False, f"파일 크기가 너무 큽니다. 최대 크기: {self.MAX_FILE_SIZE / (1024*1024):.0f}MB"
        
        if file_size == 0:
            return False, "빈 파일입니다"
        
        return True, None
    
    def _load_whisper_model(self):
        """Whisper 모델 지연 로딩"""
        if self._whisper_model is None:
            try:
                import whisper
                # base 모델 사용 (정확도와 속도 균형)
                # 더 높은 정확도가 필요하면 "medium" 또는 "large" 사용 가능
                self._whisper_model = whisper.load_model("base")
                logger.info("Whisper 모델 로드 완료 (base)")
            except ImportError:
                logger.error("Whisper 라이브러리가 설치되지 않았습니다. pip install openai-whisper 실행 필요")
                raise ImportError("Whisper 라이브러리가 설치되지 않았습니다")
            except Exception as e:
                logger.error(f"Whisper 모델 로드 실패: {e}")
                raise
        
        return self._whisper_model
    
    def _extract_audio(self, video_path: str, output_path: str) -> bool:
        """
        비디오에서 오디오 추출
        
        Args:
            video_path: 비디오 파일 경로
            output_path: 오디오 출력 경로
            
        Returns:
            성공 여부
        """
        try:
            from moviepy.editor import VideoFileClip
            
            video = VideoFileClip(video_path)
            if video.audio is None:
                logger.warning("비디오에 오디오 트랙이 없습니다")
                return False
            
            video.audio.write_audiofile(
                output_path,
                codec='pcm_s16le',
                verbose=False,
                logger=None
            )
            video.close()
            logger.info(f"오디오 추출 완료: {output_path}")
            return True
            
        except ImportError:
            logger.error("MoviePy 라이브러리가 설치되지 않았습니다")
            return False
        except Exception as e:
            logger.error(f"오디오 추출 실패: {e}")
            return False
    
    def _transcribe_audio(self, audio_path: str, language: str = "ko") -> Dict[str, Any]:
        """
        오디오를 텍스트로 변환 (Whisper)
        
        Args:
            audio_path: 오디오 파일 경로
            language: 언어 코드 (기본값: ko)
            
        Returns:
            음성 인식 결과
        """
        try:
            model = self._load_whisper_model()
            
            # Whisper로 음성 인식
            result = model.transcribe(
                audio_path,
                language=language,
                task="transcribe",
                verbose=False
            )
            
            text = result.get("text", "").strip()
            segments = result.get("segments", [])
            
            logger.info("음성 인식 완료: %d자", len(text))
            
            return {
                "success": True,
                "text": text,
                "language": result.get("language", language),
                "segments": [
                    {
                        "start": seg.get("start", 0),
                        "end": seg.get("end", 0),
                        "text": seg.get("text", "").strip()
                    }
                    for seg in segments
                ]
            }
            
        except Exception as e:
            logger.error(f"음성 인식 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "segments": []
            }
    
    def _extract_frames(self, video_path: str, sample_interval: float = None) -> List[Tuple[float, np.ndarray]]:
        """
        비디오에서 프레임 추출
        
        Args:
            video_path: 비디오 파일 경로
            sample_interval: 프레임 샘플링 간격 (초)
            
        Returns:
            (타임스탬프, 프레임) 리스트
        """
        if sample_interval is None:
            sample_interval = self.FRAME_SAMPLE_INTERVAL
        
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logger.error(f"비디오 파일을 열 수 없습니다: {video_path}")
            return frames
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_interval = int(fps * sample_interval)
        
        if fps <= 0:
            logger.warning("FPS를 읽을 수 없어 기본 간격(30fps) 사용")
            frame_interval = 30
        
        frame_count = 0
        timestamp = 0.0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 샘플링 간격에 맞춰 프레임 추출
                if frame_count % frame_interval == 0:
                    timestamp = frame_count / fps if fps > 0 else frame_count / 30.0
                    frames.append((timestamp, frame.copy()))
                
                frame_count += 1
                
                # 안전장치: 너무 많은 프레임 방지
                if len(frames) > 100:
                    logger.warning("프레임 수가 100개를 초과하여 샘플링 중단")
                    break
            
            logger.info("프레임 추출 완료: %d개 (전체 %d프레임 중)", len(frames), frame_count)
            
        finally:
            cap.release()
        
        return frames
    
    def _process_frame(self, frame: np.ndarray, frame_index: int, timestamp: float) -> Dict[str, Any]:
        """
        단일 프레임 처리 (OCR, 얼굴, 손가락 탐지)
        
        Args:
            frame: 프레임 이미지
            frame_index: 프레임 인덱스
            timestamp: 타임스탬프
            
        Returns:
            프레임 분석 결과
        """
        result = {
            "frame_index": frame_index,
            "timestamp": timestamp,
            "ocr": None,
            "face": None,
            "hand": None,
            "text_analysis": None
        }
        
        # 임시 파일로 프레임 저장 (OCR 서비스가 파일 경로를 요구)
        # 보안: NamedTemporaryFile 사용으로 안전한 임시 파일 생성
        temp_frame_path = None
        try:
            # delete=False로 설정하여 파일이 즉시 삭제되지 않도록 함
            # finally 블록에서 명시적으로 삭제
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False, dir=tempfile.gettempdir()) as temp_file:
                temp_frame_path = temp_file.name
                cv2.imwrite(temp_frame_path, frame)
            
            # OCR 처리
            try:
                ocr_text = self.ocr_service.detect_text(temp_frame_path)
                if ocr_text:
                    result["ocr"] = {
                        "text": ocr_text,
                        "char_count": len(ocr_text)
                    }
                    
                    # OCR 텍스트 분석 (민감 정보 탐지)
                    filter_result = self.filter_service.filter_text(ocr_text)
                    result["text_analysis"] = {
                        "has_sensitive_content": filter_result.get("has_sensitive_content", False),
                        "filtered_text": filter_result.get("filtered_text", ""),
                        "detected_categories": list(filter_result.get("filter_results", {}).keys())
                    }
            except Exception as e:
                logger.warning(f"프레임 {frame_index} OCR 처리 실패: {e}")
            
            # 얼굴 탐지
            try:
                face_result = self.face_service.detect_faces(image_np=frame, save_result=False)
                if face_result.get("success"):
                    result["face"] = {
                        "count": face_result.get("count", 0),
                        "faces": face_result.get("faces", [])
                    }
            except Exception as e:
                logger.warning(f"프레임 {frame_index} 얼굴 탐지 실패: {e}")
            
            # 손가락 탐지
            try:
                hand_result = self.hand_service.detect_fingertips(image_np=frame, save_preview=False)
                if hand_result.get("success"):
                    result["hand"] = {
                        "count": hand_result.get("count", 0),
                        "fingers": hand_result.get("fingers", [])
                    }
            except Exception as e:
                logger.warning(f"프레임 {frame_index} 손가락 탐지 실패: {e}")
        
        finally:
            # 임시 파일 삭제 (보안: 민감 정보 노출 방지)
            if temp_frame_path and os.path.exists(temp_frame_path):
                try:
                    os.unlink(temp_frame_path)
                    logger.debug("임시 프레임 파일 삭제 완료: %s", temp_frame_path)
                except Exception as e:
                    logger.warning("임시 파일 삭제 실패: %s", e)
        
        return result
    
    def process_video(
        self,
        video_file: FileStorage,
        extract_audio: bool = True,
        process_frames: bool = True,
        frame_interval: float = None
    ) -> Dict[str, Any]:
        """
        비디오 처리 메인 함수
        
        Args:
            video_file: 비디오 파일
            extract_audio: 오디오 추출 및 음성 인식 여부
            process_frames: 프레임 분석 여부
            frame_interval: 프레임 샘플링 간격 (초)
            
        Returns:
            비디오 분석 결과
        """
        # 파일 검증
        is_valid, error_msg = self._validate_video_file(video_file)
        if not is_valid:
            return {
                "success": False,
                "error": error_msg
            }
        
        temp_video_path = None
        temp_audio_path = None
        temp_dir = None
        
        try:
            # 임시 디렉토리 생성
            temp_dir = tempfile.mkdtemp(prefix="video_processing_")
            
            # 비디오 파일 저장
            video_ext = Path(video_file.filename).suffix
            temp_video_path = os.path.join(temp_dir, f"video{video_ext}")
            video_file.save(temp_video_path)
            
            result = {
                "success": True,
                "video_info": {},
                "audio_transcription": None,
                "frames": [],
                "summary": {
                    "total_frames_processed": 0,
                    "total_faces_detected": 0,
                    "total_fingers_detected": 0,
                    "total_ocr_text_length": 0,
                    "frames_with_sensitive_content": 0
                }
            }
            
            # 비디오 정보 추출
            cap = cv2.VideoCapture(temp_video_path)
            if cap.isOpened():
                result["video_info"] = {
                    "fps": cap.get(cv2.CAP_PROP_FPS),
                    "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                    "duration": cap.get(cv2.CAP_PROP_FRAME_COUNT) / max(cap.get(cv2.CAP_PROP_FPS), 1),
                    "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                }
                cap.release()
            
            # 오디오 추출 및 음성 인식
            if extract_audio:
                temp_audio_path = os.path.join(temp_dir, "audio.wav")
                if self._extract_audio(temp_video_path, temp_audio_path):
                    transcription = self._transcribe_audio(temp_audio_path)
                    result["audio_transcription"] = transcription
                    
                    # 음성 인식 텍스트 분석
                    if transcription.get("success") and transcription.get("text"):
                        audio_text = transcription["text"]
                        filter_result = self.filter_service.filter_text(audio_text)
                        result["audio_text_analysis"] = {
                            "has_sensitive_content": filter_result.get("has_sensitive_content", False),
                            "filtered_text": filter_result.get("filtered_text", ""),
                            "detected_categories": list(filter_result.get("filter_results", {}).keys())
                        }
            
            # 프레임 분석
            if process_frames:
                frames = self._extract_frames(temp_video_path, frame_interval)
                
                for idx, (timestamp, frame) in enumerate(frames):
                    frame_result = self._process_frame(frame, idx, timestamp)
                    result["frames"].append(frame_result)
                    
                    # 통계 업데이트
                    result["summary"]["total_frames_processed"] += 1
                    
                    if frame_result.get("face"):
                        result["summary"]["total_faces_detected"] += frame_result["face"].get("count", 0)
                    
                    if frame_result.get("hand"):
                        result["summary"]["total_fingers_detected"] += frame_result["hand"].get("count", 0)
                    
                    if frame_result.get("ocr"):
                        result["summary"]["total_ocr_text_length"] += frame_result["ocr"].get("char_count", 0)
                    
                    if frame_result.get("text_analysis", {}).get("has_sensitive_content"):
                        result["summary"]["frames_with_sensitive_content"] += 1
            
            # 결과 저장
            save_dir = os.path.join("data", "results", "video")
            os.makedirs(save_dir, exist_ok=True)
            saved = save_json_with_timestamp(
                save_dir,
                result,
                prefix="video_analysis"
            )
            result["result_file_url"] = saved.get("url")
            
            logger.info("비디오 처리 완료: %s", video_file.filename)
            return result
        
        except Exception as e:
            logger.error(f"비디오 처리 중 오류 발생: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"비디오 처리 중 오류가 발생했습니다: {str(e)}"
            }
        
        finally:
            # 임시 파일 정리 (보안: 민감 정보 노출 방지)
            # 모든 임시 파일과 디렉토리를 안전하게 삭제
            try:
                if temp_video_path and os.path.exists(temp_video_path):
                    os.unlink(temp_video_path)
                    logger.debug("임시 비디오 파일 삭제 완료")
                
                if temp_audio_path and os.path.exists(temp_audio_path):
                    os.unlink(temp_audio_path)
                    logger.debug("임시 오디오 파일 삭제 완료")
                
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    logger.debug("임시 디렉토리 삭제 완료")
            except Exception as e:
                logger.warning("임시 파일 정리 실패: %s", e)

