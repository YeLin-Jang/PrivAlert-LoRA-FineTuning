# -*- coding: utf-8 -*-
"""
이름 탐지 및 마스킹 처리 서비스
LoRA 파인튜닝된 KLUE BERT 모델을 사용하여 한국어 텍스트에서 이름을 탐지하고 마스킹 처리
"""

import os
import re
import logging
from typing import List, Dict, Tuple, Optional
import torch
from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification,
    pipeline
)
from peft import PeftModel

logger = logging.getLogger(__name__)

class NameDetectionService:
    """이름 탐지 및 마스킹 처리 서비스"""
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.nlp_pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model_loaded = False
        
    def load_model(self, model_path: str = None, lora_path: str = None):
        """
        LoRA 파인튜닝된 모델 로드
        
        Args:
            model_path: 기본 KLUE BERT 모델 경로
            lora_path: LoRA 어댑터 경로
        """
        try:
            if model_path is None:
                model_path = "klue/bert-base"
            
            logger.info(f"기본 모델 로딩: {model_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            base_model = AutoModelForTokenClassification.from_pretrained(
                model_path,
                num_labels=3,  # O, B-PER, I-PER
                id2label={0: "O", 1: "B-PER", 2: "I-PER"},
                label2id={"O": 0, "B-PER": 1, "I-PER": 2}
            )
            
            if lora_path and os.path.exists(lora_path):
                logger.info(f"LoRA 어댑터 로딩: {lora_path}")
                self.model = PeftModel.from_pretrained(base_model, lora_path)
            else:
                logger.warning("LoRA 경로가 없거나 존재하지 않음. 기본 모델 사용")
                self.model = base_model
            
            self.model.to(self.device)
            self.model.eval()
            
            # NER 파이프라인 생성
            self.nlp_pipeline = pipeline(
                "ner",
                model=self.model,
                tokenizer=self.tokenizer,
                aggregation_strategy="simple",
                device=0 if self.device == "cuda" else -1
            )
            
            self.model_loaded = True
            logger.info("이름 탐지 모델 로딩 완료")
            
        except Exception as e:
            logger.error(f"모델 로딩 실패: {e}")
            self.model_loaded = False
            raise
    
    def detect_names(self, text: str) -> List[Dict]:
        """
        텍스트에서 이름 탐지
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            탐지된 이름 정보 리스트
        """
        if not self.model_loaded:
            raise RuntimeError("모델이 로드되지 않았습니다. load_model()을 먼저 호출하세요.")
        
        try:
            # NER 파이프라인으로 이름 탐지
            entities = self.nlp_pipeline(text)
            
            # PER 태그만 필터링
            names = []
            for entity in entities:
                if entity['entity_group'] == 'PER':
                    names.append({
                        'text': entity['word'],
                        'start': entity['start'],
                        'end': entity['end'],
                        'confidence': entity['score']
                    })
            
            logger.info(f"탐지된 이름 수: {len(names)}")
            return names
            
        except Exception as e:
            logger.error(f"이름 탐지 실패: {e}")
            return []
    
    def mask_names(self, text: str, mask_char: str = "*") -> Dict:
        """
        텍스트에서 이름을 마스킹 처리
        
        Args:
            text: 원본 텍스트
            mask_char: 마스킹에 사용할 문자
            
        Returns:
            마스킹된 텍스트와 탐지된 이름 정보
        """
        if not self.model_loaded:
            raise RuntimeError("모델이 로드되지 않았습니다. load_model()을 먼저 호출하세요.")
        
        try:
            # 이름 탐지
            detected_names = self.detect_names(text)
            
            if not detected_names:
                return {
                    'original_text': text,
                    'masked_text': text,
                    'detected_names': [],
                    'mask_count': 0
                }
            
            # 이름을 마스킹 처리
            masked_text = text
            mask_count = 0
            
            # 끝에서부터 시작하여 인덱스 변경 문제 방지
            for name_info in sorted(detected_names, key=lambda x: x['start'], reverse=True):
                start = name_info['start']
                end = name_info['end']
                name_text = name_info['text']
                
                # 마스킹 처리 (조사 보존)
                masked_name = self._mask_name_with_particles(name_text, mask_char)
                masked_text = masked_text[:start] + masked_name + masked_text[end:]
                mask_count += 1
            
            return {
                'original_text': text,
                'masked_text': masked_text,
                'detected_names': detected_names,
                'mask_count': mask_count
            }
            
        except Exception as e:
            logger.error(f"이름 마스킹 실패: {e}")
            return {
                'original_text': text,
                'masked_text': text,
                'detected_names': [],
                'mask_count': 0,
                'error': str(e)
            }
    
    def _mask_name_with_particles(self, name: str, mask_char: str = "*") -> str:
        """
        이름을 조사와 함께 마스킹 처리
        
        Args:
            name: 마스킹할 이름
            mask_char: 마스킹 문자
            
        Returns:
            조사가 보존된 마스킹된 이름
        """
        # 한국어 조사 패턴
        particle_patterns = [
            r'(이|가|을|를|은|는|의|에|에서|로|으로|와|과|도|만|부터|까지|처럼|같이|보다|에게|한테|께|더러|에게서|한테서|께서)$',
            r'(님|씨|군|양|님들|씨들)$'
        ]
        
        # 조사 분리
        particles = []
        name_part = name
        
        for pattern in particle_patterns:
            match = re.search(pattern, name)
            if match:
                particles.append(match.group(1))
                name_part = name[:match.start()]
                break
        
        # 이름 부분을 마스킹
        if len(name_part) <= 1:
            masked_name = mask_char
        else:
            masked_name = name_part[0] + mask_char * (len(name_part) - 1)
        
        # 조사 추가
        return masked_name + ''.join(particles)
    
    def rewrite_text(self, masked_text: str, use_openai: bool = False) -> str:
        """
        마스킹된 텍스트를 자연스럽게 리라이팅
        
        Args:
            masked_text: 마스킹된 텍스트
            use_openai: OpenAI API 사용 여부
            
        Returns:
            리라이팅된 텍스트
        """
        if use_openai:
            try:
                import openai
                # OpenAI API를 사용한 리라이팅 (API 키가 설정된 경우)
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "다음 텍스트를 자연스럽게 리라이팅하되, 개인정보는 보호하세요."},
                        {"role": "user", "content": masked_text}
                    ],
                    max_tokens=500,
                    temperature=0.7
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.warning(f"OpenAI 리라이팅 실패: {e}")
                return masked_text
        else:
            # 간단한 리라이팅 (기본)
            return self._simple_rewrite(masked_text)
    
    def _simple_rewrite(self, text: str) -> str:
        """
        간단한 리라이팅 처리
        
        Args:
            text: 마스킹된 텍스트
            
        Returns:
            리라이팅된 텍스트
        """
        # 기본적인 문장 구조 개선
        rewrites = {
            r'\*+님': '해당자',
            r'\*+씨': '해당자',
            r'\*+군': '해당자',
            r'\*+양': '해당자',
            r'\*+': 'OOO',
        }
        
        result = text
        for pattern, replacement in rewrites.items():
            result = re.sub(pattern, replacement, result)
        
        return result

# 전역 서비스 인스턴스
name_detection_service = NameDetectionService()
