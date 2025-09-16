import cv2
import numpy as np
import os
import uuid
import mediapipe as mp
from werkzeug.datastructures import FileStorage

class FaceDetectionService:
    """Mediapipe 기반 얼굴 검출 서비스"""

    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.detector = self.mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.6)
        self.save_dir = os.path.join("app", "static", "results")
        os.makedirs(self.save_dir, exist_ok=True)

    def detect_faces(self, image_file: FileStorage, save_result=True):
        try:
            # 파일 읽기 → numpy 배열
            file_bytes = np.frombuffer(image_file.read(), np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            # BGR → RGB (Mediapipe는 RGB 필요)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # 얼굴 검출
            results = self.detector.process(rgb_image)

            faces = []
            if results.detections:
                h, w, _ = image.shape
                for i, detection in enumerate(results.detections, 1):
                    bboxC = detection.location_data.relative_bounding_box
                    x, y, width, height = (int(bboxC.xmin * w), int(bboxC.ymin * h),
                                           int(bboxC.width * w), int(bboxC.height * h))

                    faces.append({
                        "index": i,
                        "box": {"x": x, "y": y, "w": width, "h": height},
                        "score": float(detection.score[0])
                    })

                    # 얼굴 박스 그리기
                    cv2.rectangle(image, (x, y), (x + width, y + height), (0, 255, 0), 2)

            # 결과 이미지 저장
            image_url = None
            if save_result:
                filename = f"face_{uuid.uuid4().hex}.jpg"
                save_path = os.path.join(self.save_dir, filename)
                cv2.imwrite(save_path, image)
                image_url = f"/static/results/{filename}"

            return {
                "success": True,
                "count": len(faces),
                "faces": faces,
                "message": f"{len(faces)}개의 얼굴이 감지되었습니다" if faces else "얼굴이 감지되지 않았습니다",
                "result_image_url": image_url
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
