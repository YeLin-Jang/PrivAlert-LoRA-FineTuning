# -*- coding: utf-8 -*-
import os
import logging
import torch
from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForTokenClassification
from peft import PeftModel, PeftConfig

logger = logging.getLogger(__name__)

class WorkplaceDetectionService:
    """직장명 탐지 서비스 (KLUE BERT + LoRA 모델 사용)"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.ner_pipeline = None
        self.model_loaded = False
        self.model_path = os.path.join(os.path.dirname(__file__), '../../models/KLUE-NER-Organization-Model/klue-ner-lora-org-v2-final')
        
    def _load_model(self):
        """모델 로드 (지연 로딩)"""
        if self.model_loaded:
            return
            
        try:
            logger.info("직장명 탐지 모델 로딩 시작...")
            
            # LoRA 모델 설정 로드
            peft_config = PeftConfig.from_pretrained(self.model_path)
            base_model_name = peft_config.base_model_name_or_path
            
            # 기본 모델과 토크나이저 로드
            self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)
            base_model = AutoModelForTokenClassification.from_pretrained(
                base_model_name,
                num_labels=13,  # 실제 모델의 클래스 수
                id2label={i: f"LABEL_{i}" for i in range(13)},
                label2id={f"LABEL_{i}": i for i in range(13)}
            )
            
            # LoRA 어댑터 로드
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            self.model.eval()
            
            # NER 파이프라인은 PEFT 모델과 호환되지 않으므로 직접 추론 사용
            # self.ner_pipeline = pipeline(...)  # 제거
            
            self.model_loaded = True
            logger.info("직장명 탐지 모델 로딩 완료")
            
        except Exception as e:
            logger.error(f"모델 로딩 실패: {e}")
            self.model_loaded = False
            raise e
    
    def detect_workplaces(self, text: str) -> Dict:
        """
        텍스트에서 직장명을 탐지
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            탐지 결과 딕셔너리
        """
        if not text or not text.strip():
            return {
                "detected": False,
                "total_count": 0,
                "workplaces": [],
                "message": "텍스트가 없습니다"
            }
        
        try:
            # 모델이 로드되지 않았으면 로드
            if not self.model_loaded:
                self._load_model()
            
            # 토크나이징
            inputs = self.tokenizer(text, return_tensors='pt', padding=True, truncation=True)
            tokens = self.tokenizer.convert_ids_to_tokens(inputs['input_ids'][0])
            
            # 모델 예측
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_labels = torch.argmax(predictions, dim=-1)
            
            # LABEL_4 (직장명) 탐지
            workplaces = []
            current_entity = ""
            
            for i, (token, label, probs) in enumerate(zip(tokens, predicted_labels[0], predictions[0])):
                if token in ['[CLS]', '[SEP]', '[PAD]']:
                    continue
                    
                # 토큰의 실제 위치 계산
                if token.startswith('##'):
                    # 서브워드 토큰
                    token_text = token[2:]
                else:
                    token_text = token
                
                # LABEL_4 (직장명)이고 신뢰도가 0.3 이상인 경우
                if label.item() == 4 and probs[label].item() > 0.3:
                    if current_entity == "":
                        # 새로운 엔티티 시작
                        current_entity = token_text
                    else:
                        # 기존 엔티티에 추가
                        current_entity += token_text
                else:
                    # 엔티티가 끝남
                    if current_entity != "":
                        # 실제 텍스트에서 위치 찾기
                        entity_text = current_entity.replace('##', '')
                        if entity_text in text:
                            start_pos = text.find(entity_text)
                            end_pos = start_pos + len(entity_text)
                            workplaces.append({
                                "text": entity_text,
                                "start": start_pos,
                                "end": end_pos,
                                "score": probs[label].item()
                            })
                        current_entity = ""
            
            # 마지막 엔티티 처리
            if current_entity != "":
                entity_text = current_entity.replace('##', '')
                if entity_text in text:
                    start_pos = text.find(entity_text)
                    end_pos = start_pos + len(entity_text)
                    workplaces.append({
                        "text": entity_text,
                        "start": start_pos,
                        "end": end_pos,
                        "score": probs[label].item()
                    })
            
            # 중복 제거 및 정리
            unique_workplaces = self._remove_duplicates(workplaces)
            
            return {
                "detected": len(unique_workplaces) > 0,
                "total_count": len(unique_workplaces),
                "workplaces": unique_workplaces,
                "message": f"{len(unique_workplaces)}개의 직장명이 탐지되었습니다" if unique_workplaces else "직장명이 발견되지 않았습니다"
            }
            
        except Exception as e:
            logger.error(f"직장명 탐지 중 오류: {e}")
            return {
                "detected": False,
                "total_count": 0,
                "workplaces": [],
                "message": f"탐지 중 오류가 발생했습니다: {str(e)}"
            }
    
    def _remove_duplicates(self, workplaces: List[Dict]) -> List[Dict]:
        """중복된 직장명 제거"""
        seen = set()
        unique_workplaces = []
        
        for workplace in workplaces:
            text = workplace['text'].strip()
            if text not in seen and len(text) > 1:  # 1글자 이하는 제외
                seen.add(text)
                unique_workplaces.append(workplace)
        
        return unique_workplaces
    
    def mask_workplaces(self, text: str) -> str:
        """
        텍스트에서 직장명을 마스킹
        
        Args:
            text: 마스킹할 텍스트
            
        Returns:
            마스킹된 텍스트
        """
        detection_result = self.detect_workplaces(text)
        
        if not detection_result['detected']:
            return text
        
        masked_text = text
        # 뒤에서부터 마스킹 (인덱스 변경 방지)
        for workplace in sorted(detection_result['workplaces'], key=lambda x: x['start'], reverse=True):
            start = workplace['start']
            end = workplace['end']
            masked_text = masked_text[:start] + "[직장명]" + masked_text[end:]
        
        return masked_text
    
    def get_model_info(self) -> Dict:
        """모델 정보 반환"""
        return {
            "model_loaded": self.model_loaded,
            "model_path": self.model_path,
            "base_model": "klue/bert-base",
            "model_type": "LoRA + KLUE BERT",
            "task": "Named Entity Recognition (Organization)"
        }

# 서비스 인스턴스 생성
workplace_detection_service = WorkplaceDetectionService()
