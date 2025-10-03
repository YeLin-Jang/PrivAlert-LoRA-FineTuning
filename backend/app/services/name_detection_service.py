# -*- coding: utf-8 -*-
"""
이름 탐지 서비스
KLUE BERT + LoRA 모델을 사용하여 한국어 이름을 탐지합니다.
"""

import os
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from peft import PeftModel
import logging

logger = logging.getLogger(__name__)

class NameDetectionService:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self.is_loaded = False
        
    def load_model(self):
        """모델을 로드합니다."""
        try:
            # LoRA_DateSet의 모델 경로 사용 (절대 경로)
            model_path = r"D:\도전보안벨\LoRA_DateSet\model"
            
            # 절대 경로로 변환하여 로깅
            abs_model_path = os.path.abspath(model_path)
            logger.info(f"모델 경로 확인: {abs_model_path}")
            logger.info(f"모델 경로 존재 여부: {os.path.exists(abs_model_path)}")
            
            if not os.path.exists(abs_model_path):
                logger.error(f"모델 경로를 찾을 수 없습니다: {abs_model_path}")
                return False
                
            # 기본 모델명 직접 지정 (PeftConfig 사용하지 않음)
            base_model_name = "klue/bert-base"
            logger.info(f"기본 모델 로딩 시작: {base_model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
            base_model = AutoModelForTokenClassification.from_pretrained(
                base_model_name,
                num_labels=3,  # O, B-PERSON, I-PERSON
                id2label={0: "O", 1: "B-PERSON", 2: "I-PERSON"},
                label2id={"O": 0, "B-PERSON": 1, "I-PERSON": 2}
            )
            
            logger.info("기본 모델 로딩 완료")
            logger.info(f"LoRA 모델 로딩 시작: {abs_model_path}")
            
            # LoRA 모델 로드
            self.model = PeftModel.from_pretrained(base_model, abs_model_path)
            self.model.eval()
            
            logger.info("LoRA 모델 로딩 완료")
            logger.info("NER 파이프라인 생성 시작")
            
            # PEFT 모델은 직접 추론 사용 (파이프라인 지원 안함)
            self.pipeline = None
            logger.info("PEFT 모델 직접 추론 모드로 설정")
            
            self.is_loaded = True
            logger.info("이름 탐지 모델이 성공적으로 로드되었습니다.")
            return True
            
        except Exception as e:
            logger.error(f"모델 로드 중 오류 발생: {str(e)}")
            return False
    
    def detect_names(self, text: str) -> dict:
        """
        텍스트에서 이름을 탐지합니다.
        
        Args:
            text (str): 분석할 텍스트
            
        Returns:
            dict: 탐지 결과
        """
        if not self.is_loaded:
            if not self.load_model():
                logger.warning("AI 모델 로드 실패, 정규표현식 방식으로 폴백")
                return self._detect_names_regex(text)
        
        try:
            if not text or not text.strip():
                return {
                    "success": True,
                    "message": "입력된 텍스트가 없습니다.",
                    "names": [],
                    "count": 0
                }
            
            # 직접 추론 실행 (PEFT 모델)
            import torch
            
            # 토크나이징
            inputs = self.tokenizer(text, return_tensors='pt', padding=True, truncation=True)
            tokens = self.tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
            
            # 모델 예측
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_labels = torch.argmax(predictions, dim=-1)
            
            # 이름만 필터링 (B-PERSON=1, I-PERSON=2)
            names = []
            current_entity = ""
            current_start = 0
            
            for i, (token, label, probs) in enumerate(zip(tokens, predicted_labels[0], predictions[0])):
                if token in ['[CLS]', '[SEP]', '[PAD]']:
                    continue
                    
                # 토큰의 실제 위치 계산
                if token.startswith('##'):
                    token_text = token[2:]
                else:
                    token_text = token
                    current_start = i
                
                # B-PERSON (1) 또는 I-PERSON (2)이고 신뢰도가 0.8 이상, 숫자나 특수문자 제외
                if (label.item() == 1 or label.item() == 2) and probs[label].item() > 0.8 and token_text.isalpha():
                    if current_entity == "":
                        current_entity = token_text
                    else:
                        current_entity += token_text
                else:
                    # 엔티티가 끝남
                    if current_entity != "":
                        # 실제 텍스트에서 위치 찾기
                        entity_text = current_entity.replace('##', '')
                        if entity_text in text:
                            start_pos = text.find(entity_text)
                            end_pos = start_pos + len(entity_text)
                            names.append({
                                "text": entity_text,
                                "start": start_pos,
                                "end": end_pos,
                                "score": probs[label].item(),
                                "label": "B-PERSON" if label.item() == 1 else "I-PERSON"
                            })
                        current_entity = ""
            
            # 마지막 엔티티 처리
            if current_entity != "":
                entity_text = current_entity.replace('##', '')
                if entity_text in text:
                    start_pos = text.find(entity_text)
                    end_pos = start_pos + len(entity_text)
                    names.append({
                        "text": entity_text,
                        "start": start_pos,
                        "end": end_pos,
                        "score": 0.8,
                        "label": "B-PERSON"
                    })
            
            return {
                "success": True,
                "message": f"{len(names)}개의 이름을 탐지했습니다.",
                "names": names,
                "count": len(names)
            }
            
        except Exception as e:
            logger.error(f"이름 탐지 중 오류 발생: {str(e)}")
            return {
                "success": False,
                "message": f"이름 탐지 중 오류가 발생했습니다: {str(e)}",
                "names": [],
                "count": 0
            }
    
    def mask_names(self, text: str) -> dict:
        """
        텍스트에서 이름을 마스킹합니다.
        
        Args:
            text (str): 마스킹할 텍스트
            
        Returns:
            dict: 마스킹 결과
        """
        detection_result = self.detect_names(text)
        
        if not detection_result["success"]:
            return detection_result
        
        if detection_result["count"] == 0:
            return {
                "success": True,
                "message": "마스킹할 이름이 없습니다.",
                "original_text": text,
                "masked_text": text,
                "names": [],
                "count": 0
            }
        
        try:
            masked_text = text
            names = detection_result["names"]
            
            # 뒤에서부터 마스킹 (인덱스 변경 방지)
            for name in sorted(names, key=lambda x: x["start"], reverse=True):
                masked_text = masked_text[:name["start"]] + "[이름]" + masked_text[name["end"]:]
            
            return {
                "success": True,
                "message": f"{len(names)}개의 이름을 마스킹했습니다.",
                "original_text": text,
                "masked_text": masked_text,
                "names": names,
                "count": len(names)
            }
            
        except Exception as e:
            logger.error(f"이름 마스킹 중 오류 발생: {str(e)}")
            return {
                "success": False,
                "message": f"이름 마스킹 중 오류가 발생했습니다: {str(e)}",
                "original_text": text,
                "masked_text": text,
                "names": [],
                "count": 0
            }
    
    def _detect_names_regex(self, text: str) -> dict:
        """정규표현식 기반 이름 탐지 (폴백용)"""
        try:
            import re
            
            # 한국어 이름 패턴 (2-4글자)
            name_pattern = r'[가-힣]{2,4}'
            matches = re.finditer(name_pattern, text)
            
            # 일반적인 한국 성씨
            common_surnames = ['김', '이', '박', '최', '정', '강', '조', '윤', '장', '임', '한', '오', '서', '신', '권', '황', '안', '송', '전', '고', '문', '양', '손', '배', '백', '허', '유', '남', '심', '노', '하', '곽', '성', '차', '주', '우', '구', '원', '나', '민', '진', '지', '엄', '채', '천', '공', '현', '함', '변', '여', '추', '도', '소', '시', '선', '설', '마', '길', '연', '위', '표', '명', '기', '반', '왕', '금', '옥', '육', '인', '맹', '제', '모', '탁', '국', '어', '은', '편', '용']
            
            names = []
            for match in matches:
                name = match.group()
                # 한국 성씨 체크 (최소 2글자, 최대 4글자, 숫자나 특수문자 제외)
                if len(name) >= 2 and len(name) <= 4 and name[0] in common_surnames and name.isalpha():
                    names.append({
                        "text": name,
                        "start": match.start(),
                        "end": match.end(),
                        "score": 0.8,
                        "label": "B-PERSON"
                    })
            
            return {
                "success": True,
                "message": f"{len(names)}개의 이름을 탐지했습니다. (정규표현식)",
                "names": names,
                "count": len(names)
            }
            
        except Exception as e:
            logger.error(f"정규표현식 이름 탐지 중 오류: {str(e)}")
            return {
                "success": False,
                "message": f"이름 탐지 중 오류가 발생했습니다: {str(e)}",
                "names": [],
                "count": 0
            }

# 전역 인스턴스
name_detection_service = NameDetectionService()
