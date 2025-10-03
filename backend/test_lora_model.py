# -*- coding: utf-8 -*-
"""LoRA 모델 테스트 스크립트"""

import sys
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 현재 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_lora_model():
    """LoRA 모델 테스트"""
    try:
        from app.services.name_detection_service import name_detection_service
        
        # 테스트 텍스트들
        test_texts = [
            "안녕하세요 김철수입니다.",
            "저는 이영희라고 합니다.",
            "박민수와 최지영이 함께 왔습니다.",
            "담당자는 정수현입니다.",
            "김영수, 이민호, 박지영이 회의에 참석했습니다."
        ]
        
        print("=" * 50)
        print("LoRA 모델 테스트 시작")
        print("=" * 50)
        
        # 모델 로드 테스트
        print("\n1. 모델 로딩 테스트...")
        if name_detection_service.load_model():
            print("✅ 모델 로드 성공!")
        else:
            print("❌ 모델 로드 실패!")
            return
        
        # 각 테스트 텍스트에 대해 이름 탐지
        print("\n2. 이름 탐지 테스트...")
        for i, text in enumerate(test_texts, 1):
            print(f"\n테스트 {i}: {text}")
            result = name_detection_service.detect_names(text)
            
            if result["success"]:
                print(f"✅ 성공: {result['message']}")
                if result["names"]:
                    for name in result["names"]:
                        print(f"   - {name['text']} (신뢰도: {name['score']:.3f})")
                else:
                    print("   - 탐지된 이름 없음")
            else:
                print(f"❌ 실패: {result['message']}")
        
        # 마스킹 테스트
        print("\n3. 이름 마스킹 테스트...")
        test_text = "김철수와 이영희가 박민수와 함께 왔습니다."
        print(f"원본: {test_text}")
        
        mask_result = name_detection_service.mask_names(test_text)
        if mask_result["success"]:
            print(f"마스킹: {mask_result['masked_text']}")
        else:
            print(f"마스킹 실패: {mask_result['message']}")
        
        print("\n" + "=" * 50)
        print("테스트 완료!")
        print("=" * 50)
        
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_lora_model()
