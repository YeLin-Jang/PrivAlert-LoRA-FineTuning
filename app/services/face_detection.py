import cv2
import numpy as np
import os
import mediapipe as mp
from werkzeug.datastructures import FileStorage
from app.utils.file_utils import save_path_with_timestamp, to_public_url

class FaceDetectionService:
    """Mediapipe 기반 얼굴 검출 서비스 (짧은/긴 거리 자동 폴백 + 대비 보정)"""

    def __init__(self):
        self.mp_face = mp.solutions.face_detection
        # 짧은거리(모델 0) 먼저 시도 → 실패 시 긴거리(모델 1) 폴백
        self.det_short = self.mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.6)
        self.det_long  = self.mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.6)
        # 결과 저장 디렉토리
        self.save_dir_fs = os.path.join("app", "static", "results")  # 파일시스템 경로
        self.save_dir_web = "static/results"                         # 웹 경로 (Flask static)

    def _enhance_contrast(self, bgr: np.ndarray) -> np.ndarray:
        """YCrCb의 Y 채널에 CLAHE를 적용해 대비를 살짝 올림 (검출 안정화)"""
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        y_eq = clahe.apply(y)
        ycrcb_eq = cv2.merge([y_eq, cr, cb])
        return cv2.cvtColor(ycrcb_eq, cv2.COLOR_YCrCb2BGR)

    def detect_faces(self, image_file: FileStorage, save_result: bool = True):
        try:
            data = np.frombuffer(image_file.read(), np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if image is None:
                return {"success": False, "error": "이미지 디코딩 실패"}

            # 대비 보정 후 RGB
            image_enh = self._enhance_contrast(image)
            rgb = cv2.cvtColor(image_enh, cv2.COLOR_BGR2RGB)

            # 1) 짧은거리 먼저
            results = self.det_short.process(rgb)
            if not results.detections:
                # 2) 긴거리 폴백
                results = self.det_long.process(rgb)

            faces = []
            if results.detections:
                h, w = image.shape[:2]
                for i, det in enumerate(results.detections, 1):
                    box = det.location_data.relative_bounding_box
                    x, y = int(box.xmin * w), int(box.ymin * h)
                    ww, hh = int(box.width * w), int(box.height * h)
                    # 박스 그리기
                    cv2.rectangle(image, (x, y), (x + ww, y + hh), (0, 255, 0), 2)
                    faces.append({
                        "index": i,
                        "box": {"x": x, "y": y, "w": ww, "h": hh},
                        "score": float(det.score[0])
                    })

            image_url = None
            if save_result:
                save_path = save_path_with_timestamp(self.save_dir_fs, prefix="face", ext=".jpg")
                cv2.imwrite(save_path, image)
                # 웹에서 접근하는 상대 경로로 변환
                rel_path = os.path.join(self.save_dir_web, os.path.basename(save_path))
                image_url = to_public_url(rel_path)

            return {
                "success": True,
                "count": len(faces),
                "faces": faces,
                "message": f"{len(faces)}개의 얼굴이 감지되었습니다" if faces else "얼굴이 감지되지 않았습니다",
                "result_image_url": image_url
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
