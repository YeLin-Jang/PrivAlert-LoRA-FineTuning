import cv2
import numpy as np
import os
import mediapipe as mp
from werkzeug.datastructures import FileStorage
from app.utils.file_utils import save_path_with_timestamp, to_public_url

class HandDetectionService:
    """
    Mediapipe 기반 — 지문 노출 방지용 손가락 '끝' 영역 감지
    정확도 개선:
      - 대비 보정(CLAHE)
      - min_detection_confidence 상향(0.7)
      - DIP~TIP 거리 기반 정규화된 사각형 크기
      - handedness score 기반 저신뢰 hand 필터링
    """
    TIP_INDEXES = [4, 8, 12, 16, 20]  # 엄지/검지/중지/약지/소지 tip
    DIP_MAP = {4: 3, 8: 7, 12: 11, 16: 15, 20: 19}

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.detector = self.mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=4,
            min_detection_confidence=0.7
        )
        self.save_dir_fs = os.path.join("app", "static", "results")
        self.save_dir_web = "static/results"

    def _enhance_contrast(self, bgr: np.ndarray) -> np.ndarray:
        ycrcb = cv2.cvtColor(bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        y_eq = clahe.apply(y)
        ycrcb_eq = cv2.merge([y_eq, cr, cb])
        return cv2.cvtColor(ycrcb_eq, cv2.COLOR_YCrCb2BGR)

    def _clip_box(self, x, y, w, h, iw, ih):
        x = max(0, x)
        y = max(0, y)
        w = max(1, min(w, iw - x))
        h = max(1, min(h, ih - y))
        return x, y, w, h

    def _tip_box_from_dip(self, tip, dip, iw, ih, base_max):
        """
        DIP~TIP 거리 기반으로 사각형 크기 산정 (지문 영역을 더 정확히 커버)
        - size ~= k * dist(DIP, TIP), [MIN_BOX, MAX_FRAC * hand_base] 범위 클램프
        """
        MIN_BOX = 36
        MAX_FRAC = 0.25  # 손 기준 최대 25%
        k = 4.0          # 거리 배수 (강도)

        dx = (tip[0] - dip[0])
        dy = (tip[1] - dip[1])
        dist = max(1.0, (dx*dx + dy*dy) ** 0.5)
        size = int(max(MIN_BOX, min(k * dist, base_max * MAX_FRAC)))
        half = size // 2

        cx, cy = int(tip[0]), int(tip[1])
        x, y = cx - half, cy - half
        return self._clip_box(x, y, size, size, iw, ih)

    def detect_fingertips(self, image_file: FileStorage, save_preview: bool = True):
        try:
            data = np.frombuffer(image_file.read(), np.uint8)
            image = cv2.imdecode(data, cv2.IMREAD_COLOR)
            if image is None:
                return {"success": False, "error": "이미지 디코딩 실패"}

            ih, iw = image.shape[:2]
            image_enh = self._enhance_contrast(image)
            rgb = cv2.cvtColor(image_enh, cv2.COLOR_BGR2RGB)

            results = self.detector.process(rgb)

            fingers = []
            if results.multi_hand_landmarks:
                # handedness는 landmarks와 같은 순서. score로 저신뢰 hand 제거
                handed = (results.multi_handedness or [])
                for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
                    score = 1.0
                    if idx < len(handed) and handed[idx].classification:
                        score = handed[idx].classification[0].score
                    if score < 0.6:
                        continue  # 저신뢰 hand skip

                    xs = [lm.x * iw for lm in hand_landmarks.landmark]
                    ys = [lm.y * ih for lm in hand_landmarks.landmark]
                    hand_w = int(max(xs) - min(xs))
                    hand_h = int(max(ys) - min(ys))
                    base_max = max(hand_w, hand_h)

                    for tip_idx in self.TIP_INDEXES:
                        dip_idx = self.DIP_MAP[tip_idx]
                        tip = (hand_landmarks.landmark[tip_idx].x * iw,
                               hand_landmarks.landmark[tip_idx].y * ih)
                        dip = (hand_landmarks.landmark[dip_idx].x * iw,
                               hand_landmarks.landmark[dip_idx].y * ih)

                        x, y, w, h = self._tip_box_from_dip(tip, dip, iw, ih, base_max)
                        # 프리뷰 박스
                        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        fingers.append({
                            "index": int(tip_idx),
                            "box": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
                            "hand_score": float(score)
                        })

            image_url = None
            if save_preview:
                save_path = save_path_with_timestamp(self.save_dir_fs, prefix="hand", ext=".jpg")
                cv2.imwrite(save_path, image)
                rel_path = os.path.join(self.save_dir_web, os.path.basename(save_path))
                image_url = to_public_url(rel_path)

            return {
                "success": True,
                "count": len(fingers),
                "fingers": fingers,
                "result_image_url": image_url,
                "message": f"{len(fingers)}개의 지문 노출 가능 영역이 감지되었습니다" if fingers else "지문 노출 가능 영역이 감지되지 않았습니다"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
