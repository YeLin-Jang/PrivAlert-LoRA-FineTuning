# -*- coding: utf-8 -*-
import re
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class MaskRegexService:
    """정형 데이터 마스킹 서비스"""
    
    def __init__(self):
        # 정형 데이터 패턴 정의 (고정된 패턴이 있는 데이터만)
        self.patterns = {
            "phone": [
                # 전화번호: 모바일/지역번호/단축번호 +82 포함
                ("PHONE", re.compile(
                    r"(?<!\d)(?:"
                    r"\+82[-.\s]?\d{1,2}[-.\s]?\d{3,4}[-.\s]?\d{4}"   # +82 국가번호
                    r"|010[-.\s]?\d{3,4}[-.\s]?\d{4}"                # 010 모바일
                    r"|0\d{1,2}[-\).\s]?\d{3,4}[-.\s]?\d{4}"         # 지역번호 포함 일반 전화
                    r"|\d{4}[-.\s]\d{4}"                               # 대표번호는 구분자 필수
                    r")(?!\d)"  
                )),
            ],
            "rrn": [
                # 주민등록번호 / 외국인 등록번호
                ("RRN", re.compile(r"\d{6}-?\d{7}")),
            ],
            "passport": [
                # 여권번호
                ("PASSPORT1", re.compile(r"[A-Za-z]\d{3}[A-Za-z]\d{4}", re.IGNORECASE)),
                ("PASSPORT2", re.compile(r"[A-Za-z]\d{8}", re.IGNORECASE)),
                ("PASSPORT3", re.compile(r"[A-Za-z]{2}\d{7}", re.IGNORECASE)),
            ],
            "ip_address": [
                # IPv4
                ("IPV4", re.compile(
                    r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)"
                    r"(?:\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}"
                )),
                # IPv6
                ("IPV6", re.compile(
                    r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
                    r"|(?:[0-9a-fA-F]{1,4}:){1,7}:"
                    r"|::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}"
                )),
            ],
            "email": [
                # 이메일
                ("EMAIL", re.compile(r"(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")),
            ],
            "account": [
                # 계좌번호: 은행 포맷 (2~6자리)-(2~6자리)-(2~7자리), 구분자(하이픈/공백) 필수
                ("ACCOUNT", re.compile(r"\b\d{2,6}[-\s]\d{2,6}[-\s]\d{2,7}\b")),
            ]
        }
    
    def detect_sensitive_data(self, text: str, detection_options: Dict[str, bool]) -> Dict:
        """
        선택된 탐지 옵션에 따라 민감 데이터를 탐지
        
        Args:
            text: 분석할 텍스트
            detection_options: 탐지 옵션 딕셔너리
                예: {"name": True, "address": False, "phone": True, ...}
        
        Returns:
            탐지 결과 딕셔너리
        """
        if not text or not text.strip():
            return {
                "detected": False,
                "total_count": 0,
                "categories": {},
                "details": []
            }
        
        results = {
            "detected": False,
            "total_count": 0,
            "categories": {},
            "details": []
        }
        
        # 선택된 옵션만 탐지
        for category, is_enabled in detection_options.items():
            if not is_enabled or category not in self.patterns:
                continue
                
            category_results = []
            category_count = 0
            
            for pattern_name, pattern in self.patterns[category]:
                matches = pattern.findall(text)
                if matches:
                    for match in matches:
                        category_results.append({
                            "type": pattern_name,
                            "value": match,
                            "category": category
                        })
                        category_count += 1
            
            if category_results:
                results["categories"][category] = {
                    "count": category_count,
                    "items": category_results
                }
                results["details"].extend(category_results)
                results["total_count"] += category_count
                results["detected"] = True
        
        logger.info(f"정형 데이터 탐지 완료: 총 {results['total_count']}개 탐지")
        return results
    
    def mask_sensitive_data(self, text: str, detection_options: Dict[str, bool]) -> str:
        """
        선택된 탐지 옵션에 따라 민감 데이터를 마스킹
        
        Args:
            text: 마스킹할 텍스트
            detection_options: 탐지 옵션 딕셔너리
        
        Returns:
            마스킹된 텍스트
        """
        if not text or not text.strip():
            return text
        
        masked_text = text
        
        # 선택된 옵션만 마스킹
        for category, is_enabled in detection_options.items():
            if not is_enabled or category not in self.patterns:
                continue
                
            for pattern_name, pattern in self.patterns[category]:
                # 카테고리별 라벨 매핑
                category_labels = {
                    "phone": "전화번호",
                    "rrn": "주민등록번호", 
                    "passport": "여권번호",
                    "ip_address": "IP주소",
                    "email": "이메일",
                    "account": "계좌번호"
                }
                
                # 마스킹 패턴 생성 - [라벨] 형태로 치환
                def mask_replacer(match):
                    return f"[{category_labels.get(category, category.upper())}]"
                
                masked_text = pattern.sub(mask_replacer, masked_text)
        
        return masked_text

# 서비스 인스턴스 생성
mask_regex_service = MaskRegexService()