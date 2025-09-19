import cv2
import numpy as np
import os
import mediapipe as mp
from werkzeug.datastructures import FileStorage
from app.utils.file_utils import save_path_with_timestamp, to_public_url


class HandDetectionService:
    TIP_INDEXES = [4, 8, 12, 16, 20]
    DIP_MAP = {4: 3, 8: 7, 12: 11, 16: 15, 20: 19}

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.detector = self.mp_hands.Hands(
            static_image_mode=True, max_num_hands=4, min_detection_confidence=0.7
        )

        # 내부 민감 데이터 저장소 (원본)
        self.save_dir_internal = os.path.join("data", "results", "hand")
        # 외부 공개 프리뷰 저장소 (박스 덧씌운 결과만 저장)
        self.save_dir_public = os.path.join("static", "results", "hand")

    def detect_fingertips(
        self,
        image_file: FileStorage = None,
        image_np: np.ndarray = None,
        save_preview: bool = True,
        return_image: bool = False,
    ):
        try:
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
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.detector.process(rgb)

            fingers = []
            preview_img = image.copy()
            if results and getattr(results, "multi_hand_landmarks", None):
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    for tip_idx in self.TIP_INDEXES:
                        dip_idx = self.DIP_MAP[tip_idx]
                        tip = (
                            hand_landmarks.landmark[tip_idx].x * iw,
                            hand_landmarks.landmark[tip_idx].y * ih,
                        )
                        cx, cy = int(tip[0]), int(tip[1])
                        cv2.circle(preview_img, (cx, cy), 8, (0, 0, 255), -1)
                        fingers.append({"index": tip_idx, "pos": {"x": cx, "y": cy}})

            result_image_url = None
            if save_preview:
                # 내부 저장 (원본)
                internal_path = save_path_with_timestamp(
                    self.save_dir_internal, prefix="hand", ext=".jpg"
                )
                cv2.imwrite(internal_path, image)

                # 외부 프리뷰 저장 (박스/포인트 덧씌운 결과)
                public_path = save_path_with_timestamp(
                    self.save_dir_public, prefix="hand", ext=".jpg"
                )
                cv2.imwrite(public_path, preview_img)

                rel_path = os.path.join("static", "results", "hand", os.path.basename(public_path))
                result_image_url = to_public_url(rel_path)

            response = {
                "success": True,
                "count": len(fingers),
                "fingers": fingers,
                "message": f"{len(fingers)}개의 손가락 끝이 감지되었습니다"
                if fingers
                else "손가락이 감지되지 않았습니다",
                "result_image_url": result_image_url,
            }

            if return_image:
                return response, preview_img
            return response

        except Exception as e:
            return {"success": False, "error": str(e)}
