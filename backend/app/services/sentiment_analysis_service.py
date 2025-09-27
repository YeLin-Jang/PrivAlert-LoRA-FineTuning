"""
감정 분석 서비스
KLUE 모델을 사용하여 문맥을 파악하고 종교적 모독 여부를 판단
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger(__name__)

class SentimentAnalysisService:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
        
        # 종교별 키워드와 패턴
        self.religious_keywords = {
            'christianity': ['하느님', '하나님', '예수', '교회', '성경', '기독교', '그리스도', '예수님', '예수그리스도'],
            'buddhism': ['부처', '불교', '절', '스님', '불상', '법당', '부처님'],
            'islam': ['알라', '이슬람', '모스크', '코란', '무슬림', '알라신'],
            'general_religious': ['신', '신앙', '종교', '기도', '신성', '신님']
        }
        
        # 욕설 및 부정적 표현 패턴 (철자 변형 포함)
        self.negative_patterns = [
            r'씨발', r'시발', r'새끼', r'지랄', r'개새끼', r'병신', r'미친', r'바보',
            r'좆', r'꺼져', r'닥쳐', r'죽어', r'빌어먹을', r'제기랄',
            r'ㅅㅂ', r'ㅆㅂ', r'ㅅ발', r'ㅆ발'  # 자음/모음 분리 형태
        ]
        
        # 존경 표현 패턴
        self.respectful_patterns = [
            r'존경', r'경배', r'찬양', r'감사', r'은혜', r'축복',
            r'기도', r'예배', r'신앙', r'믿음', r'사랑'
        ]

    def _load_model(self):
        """KLUE 모델 로드"""
        try:
            # KLUE 감정 분석 모델 사용 (감정 분석에 특화된 모델)
            model_name = "klue/roberta-base"
            logger.info(f"KLUE 모델 로딩 시작: {model_name}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_name,
                num_labels=3,  # 긍정, 부정, 중립
                ignore_mismatched_sizes=True
            )
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"KLUE 모델 로딩 완료: {self.device}")
            
        except Exception as e:
            logger.error(f"KLUE 모델 로딩 실패: {e}")
            # 폴백으로 간단한 규칙 기반 분석 사용
            self.model = None
            self.tokenizer = None

    def analyze_sentiment(self, text: str) -> Dict:
        """
        텍스트의 감정 분석 수행
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            감정 분석 결과 딕셔너리
        """
        try:
            if self.model is None:
                return self._rule_based_sentiment(text)
            
            # 토크나이징
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(self.device)
            
            # 감정 분석 수행
            with torch.no_grad():
                outputs = self.model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                
            # 결과 해석
            sentiment_scores = predictions[0].cpu().numpy()
            sentiment_labels = ['negative', 'neutral', 'positive']
            
            max_score_idx = sentiment_scores.argmax()
            sentiment = sentiment_labels[max_score_idx]
            confidence = float(sentiment_scores[max_score_idx])
            
            return {
                'sentiment': sentiment,
                'confidence': confidence,
                'scores': {
                    'negative': float(sentiment_scores[0]),
                    'neutral': float(sentiment_scores[1]),
                    'positive': float(sentiment_scores[2])
                }
            }
            
        except Exception as e:
            logger.error(f"감정 분석 실패: {e}")
            return self._rule_based_sentiment(text)

    def _rule_based_sentiment(self, text: str) -> Dict:
        """규칙 기반 감정 분석 (폴백)"""
        negative_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                            for pattern in self.negative_patterns)
        respectful_count = sum(len(re.findall(pattern, text, re.IGNORECASE)) 
                              for pattern in self.respectful_patterns)
        
        if negative_count > respectful_count:
            sentiment = 'negative'
            confidence = min(0.8, 0.5 + (negative_count * 0.1))
        elif respectful_count > negative_count:
            sentiment = 'positive'
            confidence = min(0.8, 0.5 + (respectful_count * 0.1))
        else:
            sentiment = 'neutral'
            confidence = 0.5
            
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'scores': {
                'negative': 0.8 if sentiment == 'negative' else 0.1,
                'neutral': 0.8 if sentiment == 'neutral' else 0.1,
                'positive': 0.8 if sentiment == 'positive' else 0.1
            }
        }

    def detect_religious_blasphemy(self, text: str) -> Dict:
        """
        종교적 모독 여부 감지
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            종교적 모독 감지 결과
        """
        try:
            logger.info(f"종교적 모독 감지 시작: '{text}'")
            
            # 1. 종교 키워드 감지
            detected_religions = []
            for religion, keywords in self.religious_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        detected_religions.append(religion)
                        logger.info(f"종교 키워드 감지: '{keyword}' -> {religion}")
                        break
            
            if not detected_religions:
                return {
                    'is_blasphemy': False,
                    'detected_religions': [],
                    'confidence': 0.0,
                    'reason': 'No religious keywords detected'
                }
            
            # 2. 감정 분석
            sentiment_result = self.analyze_sentiment(text)
            
            # 3. 욕설 패턴 감지
            negative_pattern_matches = []
            for pattern in self.negative_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    negative_pattern_matches.extend(matches)
            
            # 4. 종교 키워드와 욕설의 근접성 분석
            blasphemy_score = 0.0
            blasphemy_reasons = []
            
            for religion in detected_religions:
                for keyword in self.religious_keywords[religion]:
                    if keyword in text:
                        # 종교 키워드 주변에 욕설이 있는지 확인
                        keyword_pos = text.find(keyword)
                        context_start = max(0, keyword_pos - 10)
                        context_end = min(len(text), keyword_pos + len(keyword) + 10)
                        context = text[context_start:context_end]
                        
                        # 컨텍스트에서 욕설 감지
                        context_negative_count = sum(
                            len(re.findall(pattern, context, re.IGNORECASE))
                            for pattern in self.negative_patterns
                        )
                        
                        if context_negative_count > 0:
                            blasphemy_score += 0.5
                            blasphemy_reasons.append(f"{keyword} 주변에 부정적 표현 감지")
            
            # 5. 최종 판단
            is_blasphemy = (
                sentiment_result['sentiment'] == 'negative' and 
                sentiment_result['confidence'] > 0.6 and
                len(negative_pattern_matches) > 0 and
                blasphemy_score > 0.3
            )
            
            confidence = min(1.0, 
                (sentiment_result['confidence'] * 0.4 + 
                 len(negative_pattern_matches) * 0.3 + 
                 blasphemy_score * 0.3)
            )
            
            return {
                'is_blasphemy': is_blasphemy,
                'detected_religions': detected_religions,
                'confidence': confidence,
                'sentiment': sentiment_result,
                'negative_patterns': negative_pattern_matches,
                'blasphemy_score': blasphemy_score,
                'reasons': blasphemy_reasons
            }
            
        except Exception as e:
            logger.error(f"종교적 모독 감지 실패: {e}")
            return {
                'is_blasphemy': False,
                'detected_religions': [],
                'confidence': 0.0,
                'reason': f'Error: {str(e)}'
            }

    def get_replacement_message(self, detected_religions: List[str]) -> str:
        """
        감지된 종교에 따른 대체 메시지 생성
        
        Args:
            detected_religions: 감지된 종교 리스트
            
        Returns:
            대체 메시지
        """
        if not detected_religions:
            return "다양한 종교를 존중해주세요!"
        
        religion_messages = {
            'christianity': '기독교를 존중해주세요!',
            'buddhism': '불교를 존중해주세요!',
            'islam': '이슬람을 존중해주세요!',
            'general_religious': '종교를 존중해주세요!'
        }
        
        if len(detected_religions) == 1:
            return religion_messages.get(detected_religions[0], '종교를 존중해주세요!')
        else:
            return "다양한 종교를 존중해주세요!"

# 전역 인스턴스
sentiment_service = SentimentAnalysisService()
