# -*- coding: utf-8 -*-
import re
import logging
from typing import Dict, List

from ..data.schools import school_list
from .workplace_detection_service import workplace_detection_service
from .address_detection_service import address_detection_service


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
            ],
            "school": [
                # 학교명 패턴 (정규표현식 기반)
                ("SCHOOL_FULL", re.compile(r"[가-힣]{2,}(?:초등학교|중학교|고등학교|대학교)")),
                ("SCHOOL_SHORT", re.compile(r"[가-힣]{2,}(?:고교|대학|여대)")),
            ],
            "address": None,  # Postcodify 서비스 사용
            "driverLicense": [
                # 운전면허번호: 구 형식 (예: 12-34-567890-12)
                ("DRIVER_LICENSE_OLD", re.compile(r"\d{2}-\d{2}-\d{6}-\d{2}")),
                # 운전면허번호: 신 형식 (예: 123456-123456)
                ("DRIVER_LICENSE", re.compile(r"\b\d{6}-\d{6}\b")),
                # 운전면허번호: 12자리 연속 숫자
                ("DRIVER_LICENSE_CONTINUOUS", re.compile(r"\b\d{12}\b")),
            ],
            "postalCode": [
                # 우편번호: 5자리 숫자 (예: 12345)
                ("POSTAL_CODE", re.compile(r"\b\d{5}\b")),
                # 우편번호: 6자리 숫자 (예: 123-456)
                ("POSTAL_CODE_HYPHEN", re.compile(r"\b\d{3}-\d{3}\b")),
            ],
            "workplace": None  # AI 모델 사용
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
            
            # 학교 탐지의 경우 정규표현식과 리스트 모두 사용
            if category == "school":
                # 1. 정규표현식으로 탐지
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
                
                # 2. 학교 리스트로 탐지
                list_schools = self._detect_schools_from_list(text)
                category_results.extend(list_schools)
                category_count += len(list_schools)

            elif category == "address":
                # Postcodify 서비스를 사용한 주소 탐지
                try:
                    detected_addresses = address_detection_service.detect_addresses_in_text(text)
                    category_results.extend(detected_addresses)
                    category_count += len(detected_addresses)
                except Exception as e:
                    logger.error(f"주소 탐지 중 오류: {e}")
            elif category == "workplace":
                # AI 모델을 사용한 직장명 탐지
                try:
                    workplace_result = workplace_detection_service.detect_workplaces(text)
                    if workplace_result["detected"]:
                        for workplace in workplace_result["workplaces"]:
                            category_results.append({
                                "type": "WORKPLACE_AI",
                                "value": workplace["text"],
                                "category": category,
                                "start": workplace["start"],
                                "end": workplace["end"],
                                "score": workplace["score"]
                            })
                            category_count += 1
                except Exception as e:
                    logger.error(f"직장명 탐지 중 오류: {e}")
            else:
                # 다른 카테고리는 기존 방식대로
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
    
    def _detect_schools_from_list(self, text: str) -> List[Dict]:
        """schools.py의 학교 리스트를 사용한 학교명 탐지"""
        detected_schools = []
        
        for school in school_list:
            if school in text:
                # 학교명이 발견된 위치 찾기
                start_pos = 0
                while True:
                    pos = text.find(school, start_pos)
                    if pos == -1:
                        break
                    
                    detected_schools.append({
                        "type": "SCHOOL_LIST",
                        "value": school,
                        "category": "school",
                        "start": pos,
                        "end": pos + len(school)
                    })
                    start_pos = pos + 1
        
        return detected_schools
    
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
            
            # 카테고리별 라벨 매핑
            category_labels = {
                "phone": "전화번호",
                "rrn": "주민등록번호", 
                "passport": "여권번호",
                "ip_address": "IP주소",
                "email": "이메일",
                "account": "계좌번호",
                "school": "학교명",
                "address": "주소",
                "driverLicense": "운전면허번호",
                "postalCode": "우편번호",
                "workplace": "직장명"
            }
            
            # 학교 마스킹의 경우 리스트도 함께 사용
            if category == "school":
                # 1. 정규표현식으로 마스킹
                for pattern_name, pattern in self.patterns[category]:
                    def mask_replacer(match):
                        return f"[{category_labels.get(category, category.upper())}]"
                    masked_text = pattern.sub(mask_replacer, masked_text)
                
                # 2. 학교 리스트로 마스킹
                for school in school_list:
                    if school in masked_text:
                        masked_text = masked_text.replace(school, f"[{category_labels.get(category, category.upper())}]")
            elif category == "address":
                # Postcodify 서비스를 사용한 주소 마스킹
                try:
                    masked_text = address_detection_service.mask_addresses(masked_text)
                except Exception as e:
                    logger.error(f"주소 마스킹 중 오류: {e}")
            elif category == "workplace":
                # AI 모델을 사용한 직장명 마스킹
                try:
                    masked_text = workplace_detection_service.mask_workplaces(masked_text)
                except Exception as e:
                    logger.error(f"직장명 마스킹 중 오류: {e}")
            else:
                # 다른 카테고리는 기존 방식대로
                for pattern_name, pattern in self.patterns[category]:
                    def mask_replacer(match):
                        return f"[{category_labels.get(category, category.upper())}]"
                    masked_text = pattern.sub(mask_replacer, masked_text)
        
        return masked_text

# 서비스 인스턴스 생성
mask_regex_service = MaskRegexService()