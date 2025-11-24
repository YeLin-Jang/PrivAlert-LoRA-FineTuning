import cv2
import numpy as np
import os
import logging
import mediapipe as mp
from werkzeug.datastructures import FileStorage
from app.utils.file_utils import save_path_with_timestamp, to_public_url
from config import BASE_DATA_DIR

logger = logging.getLogger(__name__)

# 디버그 모드 (환경 변수로 제어)
DEBUG_FACE_DETECTION = os.getenv("DEBUG_FACE_DETECTION", "false").lower() == "true"


class FaceDetectionService:
    def __init__(self):
        self.mp_face = mp.solutions.face_detection
        self.det_short = self.mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.3)
        self.det_long = self.mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.3)

        # 민감 데이터 저장소 (data 디렉토리로 통일)
        self.save_dir = os.path.join(BASE_DATA_DIR, "face")

    def _enhance_contrast(self, bgr: np.ndarray) -> np.ndarray:
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        y_eq = clahe.apply(y)
        ycrcb_eq = cv2.merge([y_eq, cr, cb])
        return cv2.cvtColor(ycrcb_eq, cv2.COLOR_YCrCb2BGR)

    def detect_faces(
        self,
        image_file: FileStorage = None,
        image_np: np.ndarray = None,
        save_result: bool = True,
        return_image: bool = False,
    ):
        try:
            # 입력 처리
            if image_np is None:
                if image_file is None:
                    return {"success": False, "error": "이미지 없음"}
                # 파일 포인터를 처음으로 되돌림
                image_file.seek(0)
                data = np.frombuffer(image_file.read(), np.uint8)
                image = cv2.imdecode(data, cv2.IMREAD_COLOR)
                if image is None:
                    return {"success": False, "error": "이미지 디코딩 실패"}
            else:
                image = image_np.copy()

            ih, iw = image.shape[:2]
            image_enh = self._enhance_contrast(image)
            rgb = cv2.cvtColor(image_enh, cv2.COLOR_BGR2RGB)

            # 검출 시도
            if DEBUG_FACE_DETECTION:
                logger.debug(f"이미지 크기: {iw}x{ih}")
            results = self.det_short.process(rgb)
            if DEBUG_FACE_DETECTION:
                has_detections = (results is not None and hasattr(results, 'detections')
                                 and results.detections is not None)
                logger.debug(f"Short model 결과: {has_detections}")
            
            if not results or not getattr(results, "detections", None):
                if DEBUG_FACE_DETECTION:
                    logger.debug("Long model로 재시도...")
                results = self.det_long.process(rgb)
                if DEBUG_FACE_DETECTION:
                    has_detections = (results is not None and hasattr(results, 'detections')
                                     and results.detections is not None)
                    logger.debug(f"Long model 결과: {has_detections}")

            faces = []
            preview_img = image.copy()
            if results and getattr(results, "detections", None):
                if DEBUG_FACE_DETECTION:
                    logger.debug(f"감지된 얼굴 수: {len(results.detections)}")
                for i, det in enumerate(results.detections, 1):
                    if not getattr(det, "location_data", None):
                        if DEBUG_FACE_DETECTION:
                            logger.debug(f"얼굴 {i}: location_data 없음")
                        continue
                    box = det.location_data.relative_bounding_box
                    x, y = int(box.xmin * iw), int(box.ymin * ih)
                    ww, hh = int(box.width * iw), int(box.height * ih)
                    score = float(det.score[0]) if det.score else 0.0
                    if DEBUG_FACE_DETECTION:
                        logger.debug(f"얼굴 {i}: 위치=({x},{y},{ww},{hh}), 신뢰도={score:.3f}")
                    
                    cv2.rectangle(preview_img, (x, y), (x + ww, y + hh), (0, 255, 0), 2)
                    faces.append(
                        {"index": i, "box": {"x": x, "y": y, "w": ww, "h": hh}, "score": score}
                    )
            else:
                if DEBUG_FACE_DETECTION:
                    logger.debug("얼굴이 감지되지 않았습니다.")

            result_image_url = None
            if save_result:
                # 결과 이미지 저장 (박스 덧씌운 프리뷰)
                saved_path = save_path_with_timestamp(
                    self.save_dir, prefix="face", ext=".jpg"
                )
                cv2.imwrite(saved_path, preview_img)

                # /data/... 형태의 URL 생성
                # BASE_DATA_DIR은 backend/data/results이고, URL은 /data/results/face/... 형태여야 함
                # saved_path에서 BASE_DATA_DIR을 제거한 나머지 경로를 사용
                rel_to_base = os.path.relpath(saved_path, BASE_DATA_DIR)
                result_image_url = f"/data/results/{rel_to_base.replace(os.sep, '/')}"

            response = {
                "success": True,
                "count": len(faces),
                "faces": faces,
                "message": f"{len(faces)}개의 얼굴이 감지되었습니다" if faces else "얼굴이 감지되지 않았습니다",
                "result_image_url": result_image_url,
            }

            if return_image:
                return response, preview_img
            return response

        except Exception as e:
            logger.error(f"얼굴 검출 중 오류: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
