# -*- coding: utf-8 -*-
"""
NER 서비스 - 사람 이름(PER) 탐지
pytorch-bert-crf-ner 모델을 사용하여 한국어 텍스트에서 사람 이름만 추출합니다.
"""

import os
import logging
import sys
from pathlib import Path

# models 디렉토리를 Python 경로에 추가
current_dir = Path(__file__).parent
backend_dir = current_dir.parent.parent
models_dir = backend_dir / "models"
# backend 디렉토리를 sys.path에 추가 (models 모듈을 찾기 위해)
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

logger = logging.getLogger(__name__)

class NERService:
    """NER 서비스 - PER 엔티티만 추출"""
    
    def __init__(self):
        self.model_loaded = False
        # 지연 로딩: 앱 시작 시 모델을 로드하지 않음 (실제 사용 시 로드)
    
    def _load_model(self):
        """모델 로드 (지연 로딩, 전역 캐시 사용)"""
        if self.model_loaded:
            return
        
        try:
            # inference.py의 load_ner_model 함수 사용
            from models.ner_model.inference import load_ner_model
            
            # 모델 디렉토리 경로 설정
            # 환경변수로 경로 지정 가능, 없으면 기본 경로 사용
            model_dir = os.getenv("NER_MODEL_DIR", None)
            
            # 모델 디렉토리가 지정되지 않았으면 상대 경로로 시도
            if model_dir is None:
                # backend/models/ner_model 기준으로 상대 경로 탐색
                current_dir = Path(__file__).parent
                backend_dir = current_dir.parent.parent
                # 일반적인 모델 디렉토리 위치들
                possible_paths = [
                    backend_dir / "experiments" / "base_model_with_crf_val",
                    backend_dir.parent / "experiments" / "base_model_with_crf_val",
                    Path("./experiments/base_model_with_crf_val"),
                ]
                for path in possible_paths:
                    if path.exists() and (path / "config.json").exists():
                        model_dir = str(path)
                        logger.info(f"모델 디렉토리 자동 탐지: {model_dir}")
                        break
            
            logger.info("NER 모델 로딩 시작...")
            load_ner_model(model_dir=model_dir)
            self.model_loaded = True
            logger.info("NER 모델 로딩 완료")
            
        except ImportError as e:
            logger.warning(f"NER 모델 의존성 로드 실패: {str(e)}. 모델 파일이나 의존성(kobert, gluonnlp 등)이 필요합니다.")
            self.model_loaded = False
        except FileNotFoundError as e:
            logger.warning(f"NER 모델 파일을 찾을 수 없습니다: {str(e)}")
            self.model_loaded = False
        except Exception as e:
            logger.error(f"NER 모델 로딩 실패: {str(e)}", exc_info=True)
            self.model_loaded = False
    
    def extract_names(self, text):
        """
        텍스트에서 사람 이름(PER)만 추출합니다.
        
        Args:
            text: 입력 텍스트 (최대 2000자)
        
        Returns:
            dict: {
                "success": bool,
                "names": list[str],
                "error": str (optional)
            }
        """
        try:
            # 입력 검증
            if not text or not text.strip():
                return {
                    "success": False,
                    "names": [],
                    "error": "입력 텍스트가 비어있습니다."
                }
            
            # 길이 제한
            MAX_LENGTH = 2000
            if len(text) > MAX_LENGTH:
                text = text[:MAX_LENGTH]
                logger.warning(f"입력 텍스트가 {MAX_LENGTH}자를 초과하여 잘렸습니다.")
            
            # 모델이 로드되지 않은 경우 재시도
            if not self.model_loaded:
                self._load_model()
            
            # 모델이 여전히 로드되지 않은 경우
            if not self.model_loaded:
                return {
                    "success": False,
                    "names": [],
                    "error": "NER 모델이 로드되지 않았습니다. 모델 파일과 의존성을 확인해주세요."
                }
            
            # PER 엔티티 추출
            from models.ner_model.inference import extract_per_entities
            names = extract_per_entities(text)
            
            # 개인정보 보호: 로그에 실제 이름이나 텍스트를 저장하지 않음
            logger.info(f"PER 엔티티 추출 완료: {len(names)}개 발견")
            
            return {
                "success": True,
                "names": names
            }
            
        except Exception as e:
            logger.error(f"이름 추출 중 오류 발생: {str(e)}", exc_info=True)
            return {
                "success": False,
                "names": [],
                "error": "서버 내부 오류가 발생했습니다."
            }


# 전역 서비스 인스턴스
ner_service = NERService()

