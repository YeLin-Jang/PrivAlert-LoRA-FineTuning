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
            # 현재 파일의 디렉토리를 기준으로 절대 경로 생성
            current_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = os.path.join(current_dir, "..", "..", "models", "LoRA_DataSet", "model")
            abs_model_path = os.path.abspath(model_path)
            
            logger.info(f"모델 경로 확인: {abs_model_path}")
            logger.info(f"모델 경로 존재 여부: {os.path.exists(abs_model_path)}")
            
            if not os.path.exists(abs_model_path):
                logger.error(f"모델 경로를 찾을 수 없습니다: {abs_model_path}")
                # 대안 경로들도 시도
                alternative_paths = [
                    os.path.join(current_dir, "..", "models", "LoRA_DataSet", "model"),
                    os.path.join(os.getcwd(), "models", "LoRA_DataSet", "model"),
                    os.path.join(os.getcwd(), "backend", "models", "LoRA_DataSet", "model")
                ]
                
                for alt_path in alternative_paths:
                    alt_abs_path = os.path.abspath(alt_path)
                    if os.path.exists(alt_abs_path):
                        abs_model_path = alt_abs_path
                        logger.info(f"대안 경로 사용: {abs_model_path}")
                        break
                else:
                    logger.error("모든 대안 경로에서 모델을 찾을 수 없습니다.")
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
            
            # LoRA 모델 로드 (adapter_config_fixed.json 사용)
            # adapter_config_fixed.json이 더 완전한 설정이므로 우선 사용
            config_path = os.path.join(abs_model_path, "adapter_config_fixed.json")
            if not os.path.exists(config_path):
                config_path = os.path.join(abs_model_path, "adapter_config.json")
                logger.info("adapter_config_fixed.json을 찾을 수 없어 adapter_config.json을 사용합니다.")
            else:
                logger.info("adapter_config_fixed.json을 사용합니다.")
            
            # 모델 파일 존재 확인
            adapter_model_path = os.path.join(abs_model_path, "adapter_model.safetensors")
            if not os.path.exists(adapter_model_path):
                logger.error(f"adapter_model.safetensors 파일을 찾을 수 없습니다: {adapter_model_path}")
                return False
            
            logger.info(f"LoRA 모델 로딩 시작: {abs_model_path}")
            logger.info(f"설정 파일: {config_path}")
            logger.info(f"모델 파일: {adapter_model_path}")
            
            self.model = PeftModel.from_pretrained(base_model, abs_model_path)
            self.model.eval()
            
            # 모델이 제대로 로드되었는지 확인
            logger.info(f"LoRA 모델 로드 완료. 모델 타입: {type(self.model)}")
            logger.info(f"모델 디바이스: {next(self.model.parameters()).device}")
            
            logger.info("LoRA 모델 로딩 완료")
            logger.info("NER 파이프라인 생성 시작")
            
            # PEFT 모델은 직접 추론 사용 (파이프라인 지원 안함)
            self.pipeline = None
            logger.info("PEFT 모델 직접 추론 모드로 설정")
            
            self.is_loaded = True
            logger.info("이름 탐지 모델이 성공적으로 로드되었습니다.")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"모델 파일을 찾을 수 없습니다: {str(e)}")
            logger.error("모델 경로를 확인해주세요: " + abs_model_path)
            return False
        except ImportError as e:
            logger.error(f"필요한 라이브러리가 설치되지 않았습니다: {str(e)}")
            logger.error("pip install transformers peft torch 명령으로 설치해주세요.")
            return False
        except Exception as e:
            logger.error(f"모델 로드 중 예상치 못한 오류 발생: {str(e)}")
            logger.error(f"오류 타입: {type(e).__name__}")
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
                logger.error("AI 모델 로드 실패, 이름 탐지를 수행할 수 없습니다.")
                return {
                    "success": False,
                    "message": "AI 모델을 로드할 수 없어 이름 탐지를 수행할 수 없습니다.",
                    "names": [],
                    "count": 0
                }
        
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
            current_score = 0.0
            
            for i, (token, label, probs) in enumerate(zip(tokens, predicted_labels[0], predictions[0])):
                if token in ['[CLS]', '[SEP]', '[PAD]']:
                    continue
                    
                # 토큰의 실제 위치 계산
                if token.startswith('##'):
                    token_text = token[2:]
                else:
                    token_text = token
                    current_start = i
                
                label_id = label.item()
                confidence = probs[label_id].item()
                
                # B-PERSON (1) 또는 I-PERSON (2)이고 신뢰도가 0.7 이상
                if (label_id == 1 or label_id == 2) and confidence > 0.7:
                    # 한국어 문자만 허용 (한글, 영문, 숫자 제외)
                    if token_text and not token_text.isdigit() and not token_text in ['[UNK]', '[UNKNOWN]']:
                        if current_entity == "":
                            current_entity = token_text
                            current_score = confidence
                        else:
                            current_entity += token_text
                            current_score = max(current_score, confidence)
                else:
                    # 엔티티가 끝남
                    if current_entity != "" and len(current_entity) >= 2:  # 최소 2글자 이상
                        # 실제 텍스트에서 위치 찾기
                        entity_text = current_entity.replace('##', '')
                        if entity_text in text and len(entity_text) >= 2:
                            start_pos = text.find(entity_text)
                            end_pos = start_pos + len(entity_text)
                            names.append({
                                "text": entity_text,
                                "start": start_pos,
                                "end": end_pos,
                                "score": current_score,
                                "label": "B-PERSON"
                            })
                        current_entity = ""
                        current_score = 0.0
            
            # 마지막 엔티티 처리
            if current_entity != "" and len(current_entity) >= 2:
                entity_text = current_entity.replace('##', '')
                if entity_text in text and len(entity_text) >= 2:
                    start_pos = text.find(entity_text)
                    end_pos = start_pos + len(entity_text)
                    names.append({
                        "text": entity_text,
                        "start": start_pos,
                        "end": end_pos,
                        "score": current_score,
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
    

# 전역 인스턴스
name_detection_service = NameDetectionService()
