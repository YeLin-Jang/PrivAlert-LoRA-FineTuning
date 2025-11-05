# -*- coding: utf-8 -*-
import re
import logging
from typing import Dict, List

from ..data.schools import school_list
from ..data.addresses import address_list
from .workplace_detection_service import workplace_detection_service

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
                    r"|\d{4}[-.\s]\d{4}"                             # 대표번호 (구분자 필수)
                    r")(?!\d)"
                )),
            ],
            "rrn": [
                ("RRN", re.compile(r"\d{6}-?\d{7}")),
            ],
            "passport": [
                ("PASSPORT1", re.compile(r"[A-Za-z]\d{3}[A-Za-z]\d{4}", re.IGNORECASE)),
                ("PASSPORT2", re.compile(r"[A-Za-z]\d{8}", re.IGNORECASE)),
                ("PASSPORT3", re.compile(r"[A-Za-z]{2}\d{7}", re.IGNORECASE)),
            ],
            "ip_address": [
                ("IPV4", re.compile(
                    r"(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)"
                    r"(?:\.(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)){3}"
                )),
                ("IPV6", re.compile(
                    r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
                    r"|(?:[0-9a-fA-F]{1,4}:){1,7}:"
                    r"|::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}"
                )),
            ],
            "email": [
                ("EMAIL", re.compile(r"(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")),
            ],
            "account": [
                # 계좌번호: 은행 포맷 (2~6자리)-(2~6자리)-(2~7자리)
                ("ACCOUNT", re.compile(r"\b\d{2,6}[-\s]\d{2,6}[-\s]\d{2,7}\b")),
            ],
            "school": [
                ("SCHOOL_FULL", re.compile(r"[가-힣]{2,}(?:초등학교|중학교|고등학교|대학교)")),
                ("SCHOOL_SHORT", re.compile(r"[가-힣]{2,}(?:고교|대학|여대)")),
            ],
            "address": [
                ("ADDRESS_AREA", re.compile(r"[가-힣]{2,}(특별시|광역시|특별자치도|특별자치시|읍)")),
                ("ADDRESS_NUMBER", re.compile(r"\d{1,4}(-\d{1,4})?번지")),
                ("ADDRESS_ROAD", re.compile(r"[가-힣]+(로|길)\s?\d{1,4}(-\d{1,4})?")),
                ("ADDRESS_GIL", re.compile(r"\d+(?:-\d+)?길")),
                ("ADDRESS_SUBWAY", re.compile(r"[가-힣]+(역)")),
            ],
            "workplace": None  # AI 모델 사용
        }

    def detect_sensitive_data(self, text: str, detection_options: Dict[str, bool]) -> Dict:
        """
        선택된 탐지 옵션에 따라 민감 데이터를 탐지
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

        phone_spans = []  # 📍 전화번호 탐지된 위치 저장

        # 전화번호와 계좌번호가 함께 활성화된 경우, 전화번호를 먼저 탐지
        if detection_options.get("phone", False):
            for pattern_name, pattern in self.patterns["phone"]:
                for match in pattern.finditer(text):
                    start, end = match.span()
                    phone_spans.append((start, end))

        # 선택된 옵션만 탐지
        for category, is_enabled in detection_options.items():
            if not is_enabled or category not in self.patterns:
                continue

            category_results = []
            category_count = 0

            # 📞 전화번호 탐지 (우선 탐지)
            if category == "phone":
                for pattern_name, pattern in self.patterns["phone"]:
                    for match in pattern.finditer(text):
                        start, end = match.span()
                        category_results.append({
                            "type": pattern_name,
                            "value": match.group(),
                            "category": category,
                            "start": start,
                            "end": end
                        })
                        category_count += 1

            # 💳 계좌번호 탐지 (전화번호 영역 제외)
            elif category == "account":
                for pattern_name, pattern in self.patterns["account"]:
                    for match in pattern.finditer(text):
                        start, end = match.span()
                        # 전화번호 영역과 겹치면 skip
                        if any(s <= start < e or s < end <= e for s, e in phone_spans):
                            continue
                        category_results.append({
                            "type": pattern_name,
                            "value": match.group(),
                            "category": category,
                            "start": start,
                            "end": end
                        })
                        category_count += 1

            elif category == "school":
                for pattern_name, pattern in self.patterns[category]:
                    for match in pattern.finditer(text):
                        category_results.append({
                            "type": pattern_name,
                            "value": match.group(),
                            "category": category
                        })
                        category_count += 1

                list_schools = self._detect_schools_from_list(text)
                category_results.extend(list_schools)
                category_count += len(list_schools)

            elif category == "address":
                for pattern_name, pattern in self.patterns[category]:
                    for match in pattern.finditer(text):
                        category_results.append({
                            "type": pattern_name,
                            "value": match.group(),
                            "category": category
                        })
                        category_count += 1

                for addr in address_list:
                    start_pos = 0
                    while True:
                        pos = text.find(addr, start_pos)
                        if pos == -1:
                            break
                        category_results.append({
                            "type": "ADDRESS_LIST",
                            "value": addr,
                            "category": category,
                            "start": pos,
                            "end": pos + len(addr)
                        })
                        category_count += 1
                        start_pos = pos + 1

            elif category == "workplace":
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
                for pattern_name, pattern in self.patterns[category]:
                    for match in pattern.finditer(text):
                        category_results.append({
                            "type": pattern_name,
                            "value": match.group(),
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
        """선택된 탐지 옵션에 따라 민감 데이터를 마스킹"""
        if not text or not text.strip():
            return text

        masked_text = text

        category_labels = {
            "phone": "전화번호",
            "rrn": "주민등록번호",
            "passport": "여권번호",
            "ip_address": "IP주소",
            "email": "이메일",
            "account": "계좌번호",
            "school": "학교명",
            "address": "주소",
            "workplace": "직장명"
        }

        # 전화번호와 계좌번호가 함께 활성화된 경우, 전화번호를 먼저 탐지
        phone_spans = []
        if detection_options.get("phone", False):
            for pattern_name, pattern in self.patterns["phone"]:
                for match in pattern.finditer(text):
                    start, end = match.span()
                    phone_spans.append((start, end, match.group()))

        # 모든 마스킹할 위치를 수집 (카테고리별로 구분)
        masking_positions = {}  # category -> [(start, end, label), ...]
        
        for category, is_enabled in detection_options.items():
            if not is_enabled or category not in self.patterns:
                continue
            
            if category == "phone":
                masking_positions[category] = [(s, e, category_labels.get(category)) for s, e, _ in phone_spans]
            elif category == "account":
                account_positions = []
                for pattern_name, pattern in self.patterns[category]:
                    for match in pattern.finditer(text):
                        start, end = match.span()
                        # 전화번호 영역과 겹치면 skip
                        if any(s <= start < e or s < end <= e for s, e, _ in phone_spans):
                            continue
                        account_positions.append((start, end, category_labels.get(category)))
                masking_positions[category] = account_positions

            elif category == "school":
                for pattern_name, pattern in self.patterns[category]:
                    for match in pattern.finditer(text):
                        start, end = match.span()
                        if category not in masking_positions:
                            masking_positions[category] = []
                        masking_positions[category].append((start, end, category_labels.get(category)))
                for school in school_list:
                    start_pos = 0
                    while True:
                        pos = text.find(school, start_pos)
                        if pos == -1:
                            break
                        if category not in masking_positions:
                            masking_positions[category] = []
                        masking_positions[category].append((pos, pos + len(school), category_labels.get(category)))
                        start_pos = pos + 1

            elif category == "address":
                for pattern_name, pattern in self.patterns[category]:
                    for match in pattern.finditer(text):
                        start, end = match.span()
                        if category not in masking_positions:
                            masking_positions[category] = []
                        masking_positions[category].append((start, end, "[주소]"))
                for addr in address_list:
                    start_pos = 0
                    while True:
                        pos = text.find(addr, start_pos)
                        if pos == -1:
                            break
                        if category not in masking_positions:
                            masking_positions[category] = []
                        masking_positions[category].append((pos, pos + len(addr), "[주소]"))
                        start_pos = pos + 1

            elif category == "workplace":
                try:
                    workplace_result = workplace_detection_service.detect_workplaces(text)
                    if workplace_result.get("detected", False):
                        if category not in masking_positions:
                            masking_positions[category] = []
                        for workplace in workplace_result.get("workplaces", []):
                            masking_positions[category].append((workplace["start"], workplace["end"], category_labels.get(category)))
                except Exception as e:
                    logger.error(f"직장명 마스킹 중 오류: {e}")

            elif category not in ["phone", "account"]:
                # 기타 카테고리
                for pattern_name, pattern in self.patterns[category]:
                    for match in pattern.finditer(text):
                        start, end = match.span()
                        if category not in masking_positions:
                            masking_positions[category] = []
                        masking_positions[category].append((start, end, category_labels.get(category)))

        # 모든 마스킹 위치를 하나의 리스트로 합치고 역순으로 정렬하여 마스킹
        all_positions = []
        for positions in masking_positions.values():
            all_positions.extend(positions)
        
        # 역순으로 정렬하여 뒤에서부터 마스킹 (인덱스 유지)
        all_positions.sort(key=lambda x: x[0], reverse=True)
        
        for start, end, label in all_positions:
            masked_text = masked_text[:start] + f"[{label}]" + masked_text[end:]

        return masked_text


# 서비스 인스턴스 생성
mask_regex_service = MaskRegexService()
