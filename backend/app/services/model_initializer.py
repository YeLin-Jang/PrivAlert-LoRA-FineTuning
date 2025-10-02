# -*- coding: utf-8 -*-
"""
모델 초기화 서비스
애플리케이션 시작 시 필요한 모델들을 로드합니다.
"""

import os
import logging
from app.services.name_detection_service import name_detection_service

logger = logging.getLogger(__name__)

def initialize_models():
    """모델 초기화"""
    try:
        logger.info("모델 초기화 시작...")
        
        # 이름 탐지 모델 초기화
        initialize_name_detection_model()
        
        logger.info("모델 초기화 완료")
        
    except Exception as e:
        logger.error(f"모델 초기화 실패: {e}")
        raise

def initialize_name_detection_model():
    """이름 탐지 모델 초기화"""
    try:
        # 모델 경로 설정
        model_path = os.getenv("NAME_MODEL_PATH", "klue/bert-base")
        lora_path = os.getenv("NAME_LORA_PATH", None)
        
        # LoRA 경로가 설정되지 않은 경우 기본 경로 확인
        if not lora_path:
            # LoRA_DateSet 폴더에서 모델 찾기
            lora_dataset_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "LoRA_DateSet")
            if os.path.exists(lora_dataset_path):
                # 가능한 LoRA 경로들 확인
                possible_paths = [
                    os.path.join(lora_dataset_path, "lora_model"),
                    os.path.join(lora_dataset_path, "model"),
                    os.path.join(lora_dataset_path, "output"),
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        lora_path = path
                        break
        
        logger.info(f"이름 탐지 모델 경로: {model_path}")
        logger.info(f"LoRA 경로: {lora_path}")
        
        # 모델 로드
        name_detection_service.load_model(model_path, lora_path)
        
        logger.info("이름 탐지 모델 초기화 완료")
        
    except Exception as e:
        logger.warning(f"이름 탐지 모델 초기화 실패: {e}")
        logger.warning("이름 탐지 기능을 사용할 수 없습니다.")
        # 모델 로딩 실패해도 애플리케이션은 계속 실행
