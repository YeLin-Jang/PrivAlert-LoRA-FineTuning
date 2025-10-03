# -*- coding: utf-8 -*-
"""이름 탐지 테스트"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.name_detection_service import name_detection_service

# 테스트 텍스트
test_text = "안녕하세요 김철수입니다. 저는 이영희라고 합니다."

print("테스트 텍스트:", test_text)
print()

# 모델 로드 테스트
print("모델 로드 중...")
if name_detection_service.load_model():
    print("모델 로드 성공!")
    
    # 이름 탐지 테스트
    result = name_detection_service.detect_names(test_text)
    print("탐지 결과:", result)
    print()

    # 이름 마스킹 테스트
    mask_result = name_detection_service.mask_names(test_text)
    print("마스킹 결과:", mask_result)
else:
    print("모델 로드 실패!")
