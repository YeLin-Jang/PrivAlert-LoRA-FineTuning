import cv2
import numpy as np
import os
import mediapipe as mp
from werkzeug.datastructures import FileStorage
from app.utils.file_utils import save_path_with_timestamp, to_public_url


class FaceDetectionService:
    def __init__(self):
        self.mp_face = mp.solutions.face_detection
        self.det_short = self.mp_face.FaceDetection(model_selection=0, min_detection_confidence=0.3)
        self.det_long = self.mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.3)

        # 내부 민감 데이터 저장소 (원본 보관, 외부 공개 ❌)
        self.save_dir_internal = os.path.join("data", "results", "face")
        # 외부 공개 프리뷰 저장소 (박스 덧씌운 결과만 저장)
        self.save_dir_public = os.path.join("static", "results", "face")

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
            print(f"이미지 크기: {iw}x{ih}")
            results = self.det_short.process(rgb)
            print(f"Short model 결과: {results is not None and hasattr(results, 'detections') and results.detections is not None}")
            
            if not results or not getattr(results, "detections", None):
                print("Long model로 재시도...")
                results = self.det_long.process(rgb)
                print(f"Long model 결과: {results is not None and hasattr(results, 'detections') and results.detections is not None}")

            faces = []
            preview_img = image.copy()
            if results and getattr(results, "detections", None):
                print(f"감지된 얼굴 수: {len(results.detections)}")
                for i, det in enumerate(results.detections, 1):
                    if not getattr(det, "location_data", None):
                        print(f"얼굴 {i}: location_data 없음")
                        continue
                    box = det.location_data.relative_bounding_box
                    x, y = int(box.xmin * iw), int(box.ymin * ih)
                    ww, hh = int(box.width * iw), int(box.height * ih)
                    score = float(det.score[0]) if det.score else 0.0
                    print(f"얼굴 {i}: 위치=({x},{y},{ww},{hh}), 신뢰도={score:.3f}")
                    
                    cv2.rectangle(preview_img, (x, y), (x + ww, y + hh), (0, 255, 0), 2)
                    faces.append(
                        {"index": i, "box": {"x": x, "y": y, "w": ww, "h": hh}, "score": score}
                    )
            else:
                print("얼굴이 감지되지 않았습니다.")

            result_image_url = None
            if save_result:
                # 내부 민감 데이터 저장 (원본)
                internal_path = save_path_with_timestamp(
                    self.save_dir_internal, prefix="face", ext=".jpg"
                )
                cv2.imwrite(internal_path, image)

                # 외부 공개 프리뷰 저장 (박스 덧씌운 결과)
                public_path = save_path_with_timestamp(
                    self.save_dir_public, prefix="face", ext=".jpg"
                )
                cv2.imwrite(public_path, preview_img)

                rel_path = os.path.join("static", "results", "face", os.path.basename(public_path))
                result_image_url = to_public_url(rel_path)

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
            return {"success": False, "error": str(e)}
