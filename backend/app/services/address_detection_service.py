# -*- coding: utf-8 -*-
"""
Postcodify API를 사용한 주소 탐지 서비스
Postcodify: https://github.com/poesis/postcodify
라이선스: LGPL-3.0, GPL-3.0
"""
import re
import logging
import requests
from typing import List, Dict, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class AddressDetectionService:
    """Postcodify API를 사용한 주소 탐지 서비스"""
    
    # Postcodify 무료 API 엔드포인트
    POSTCODIFY_API_URL = "https://postcodify.daum.net/search"
    
    # 입력 검증 상수
    MAX_TEXT_LENGTH = 10000  # 최대 텍스트 길이 (DoS 방지)
    MAX_ADDRESS_QUERY_LENGTH = 100  # API 쿼리 최대 길이
    REQUEST_TIMEOUT = 3  # 타임아웃 (초)
    MAX_CANDIDATES_PER_REQUEST = 10  # 요청당 최대 후보 수 (Rate limiting)
    
    # 한국 주소 패턴 (시/군/구, 도로명 등)
    ADDRESS_PATTERNS = [
        # 시/도 + 시/군/구 패턴
        re.compile(r"[가-힣]+(?:도|특별시|광역시|특별자치도|특별자치시)\s+[가-힣]+(?:시|군|구)"),
        # 시/군/구 패턴
        re.compile(r"[가-힣]+(?:시|군|구)(?:\s+[가-힣]+(?:구|동|리|읍|면))?"),
        # 도로명 주소 패턴
        re.compile(r"[가-힣]+(?:로|길|대로)\s*\d+(?:-\d+)?(?:번지)?"),
        # 지번 주소 패턴
        re.compile(r"\d+(?:-\d+)?번지"),
        # 우편번호 포함 주소
        re.compile(r"\d{5}\s+[가-힣]+"),
        # 동/리/읍/면 포함 주소
        re.compile(r"[가-힣]+(?:동|리|읍|면)\s*\d+"),
    ]
    
    def __init__(self):
        """주소 탐지 서비스 초기화"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
        # SSL 검증 활성화 (보안)
        self.session.verify = True
        # 초기화 완료 (로그 제거)
    
    def detect_addresses_in_text(self, text: str) -> List[Dict]:
        """
        텍스트에서 주소를 탐지
        
        시큐어 코딩 가이드 준수:
        - 입력 타입 및 길이 검증
        - Rate limiting (최대 후보 수 제한)
        - 예외 처리 및 안전한 응답
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            탐지된 주소 목록 (각 항목은 type, value, start, end, category 포함)
        """
        # 입력 검증
        if not isinstance(text, str):
            logger.warning("주소 탐지: 잘못된 입력 타입")
            return []
        
        if not text or not text.strip():
            return []
        
        # DoS 공격 방지: 텍스트 길이 제한
        if len(text) > self.MAX_TEXT_LENGTH:
            logger.warning(f"주소 탐지: 텍스트 길이 초과 (최대: {self.MAX_TEXT_LENGTH})")
            text = text[:self.MAX_TEXT_LENGTH]
        
        try:
            detected_addresses = []
            
            # 1. 패턴 기반 주소 후보 추출
            address_candidates = self._extract_address_candidates(text)
            
            # Rate limiting: 최대 후보 수 제한
            if len(address_candidates) > self.MAX_CANDIDATES_PER_REQUEST:
                logger.debug(f"주소 후보 수 제한: {len(address_candidates)} -> {self.MAX_CANDIDATES_PER_REQUEST}")
                address_candidates = address_candidates[:self.MAX_CANDIDATES_PER_REQUEST]
            
            # 2. Postcodify API로 검증 및 보강
            for candidate in address_candidates:
                # Postcodify API로 주소 검증 및 상세 정보 가져오기
                validated_address = self._validate_with_postcodify(candidate['value'])
                
                if validated_address:
                    detected_addresses.append({
                        "type": "ADDRESS_POSTCODIFY",
                        "value": validated_address.get('full_address', candidate['value']),
                        "category": "address",
                        "start": candidate['start'],
                        "end": candidate['end'],
                        "postcode": validated_address.get('postcode'),
                        "road_address": validated_address.get('road_address'),
                        "jibun_address": validated_address.get('jibun_address'),
                    })
                else:
                    # API 검증 실패해도 패턴 매칭된 주소는 포함
                    detected_addresses.append({
                        "type": "ADDRESS_PATTERN",
                        "value": candidate['value'],
                        "category": "address",
                        "start": candidate['start'],
                        "end": candidate['end'],
                    })
            
            # 중복 제거 (같은 위치의 주소는 하나만)
            unique_addresses = self._remove_duplicates(detected_addresses)
            
            logger.debug(f"주소 탐지 완료: {len(unique_addresses)}개 탐지")
            return unique_addresses
            
        except Exception as e:
            logger.error(f"주소 탐지 중 예상치 못한 오류: {e}", exc_info=True)
            return []  # 안전한 폴백 응답
    
    def _extract_address_candidates(self, text: str) -> List[Dict]:
        """패턴 기반으로 주소 후보 추출"""
        candidates = []
        
        for pattern in self.ADDRESS_PATTERNS:
            for match in pattern.finditer(text):
                candidates.append({
                    "value": match.group(),
                    "start": match.start(),
                    "end": match.end(),
                })
        
        # 길이 순으로 정렬 (긴 주소 우선)
        candidates.sort(key=lambda x: x['end'] - x['start'], reverse=True)
        
        # 겹치는 주소 제거 (짧은 주소가 긴 주소에 포함되면 제거)
        filtered_candidates = []
        for candidate in candidates:
            is_overlapped = False
            for existing in filtered_candidates:
                if (candidate['start'] >= existing['start'] and 
                    candidate['end'] <= existing['end']):
                    is_overlapped = True
                    break
            if not is_overlapped:
                filtered_candidates.append(candidate)
        
        return filtered_candidates
    
    def _validate_with_postcodify(self, address_query: str) -> Optional[Dict]:
        """
        Postcodify API로 주소 검증
        
        시큐어 코딩 가이드 준수:
        - 입력 검증 및 길이 제한
        - 타임아웃 설정
        - 응답 검증 및 안전한 파싱
        - 민감 정보 로깅 방지
        
        Args:
            address_query: 검증할 주소 문자열
            
        Returns:
            검증된 주소 정보 또는 None
        """
        # 입력 검증
        if not isinstance(address_query, str) or not address_query.strip():
            return None
        
        # 길이 제한 (DoS 방지)
        address_query = address_query[:self.MAX_ADDRESS_QUERY_LENGTH].strip()
        if not address_query:
            return None
        
        try:
            # URL 인코딩 (보안: 특수문자 처리)
            encoded_query = quote(address_query, safe='')
            
            # API 요청 (무료 API는 쿼리 파라미터로 검색)
            params = {
                'q': encoded_query,
                'output': 'json'
            }
            
            response = self.session.get(
                self.POSTCODIFY_API_URL,
                params=params,
                timeout=self.REQUEST_TIMEOUT,
                allow_redirects=False  # 리다이렉트 방지 (보안)
            )
            
            # HTTP 상태 코드 검증
            if response.status_code != 200:
                logger.debug(f"Postcodify API 오류: HTTP {response.status_code}")
                return None
            
            # Content-Type 검증
            content_type = response.headers.get('Content-Type', '')
            if 'application/json' not in content_type and 'text/json' not in content_type:
                logger.debug(f"Postcodify API: 예상치 못한 Content-Type: {content_type}")
                return None
            
            # JSON 파싱 (안전한 파싱)
            try:
                data = response.json()
            except ValueError as e:
                logger.warning(f"Postcodify API: JSON 파싱 실패: {e}")
                return None
            
            # 응답 구조 검증
            if not isinstance(data, dict):
                logger.debug("Postcodify API: 응답이 딕셔너리가 아님")
                return None
            
            # API 응답 구조에 따라 파싱
            if data.get('status') == 'success' and data.get('results'):
                results = data.get('results', [])
                if not isinstance(results, list) or len(results) == 0:
                    return None
                
                result = results[0]  # 첫 번째 결과 사용
                if not isinstance(result, dict):
                    return None
                
                # 안전하게 데이터 추출
                return {
                    'full_address': result.get('full_address', '') or address_query,
                    'postcode': result.get('postcode'),
                    'road_address': result.get('road_address'),
                    'jibun_address': result.get('jibun_address'),
                }
            
            return None
            
        except requests.exceptions.Timeout:
            logger.debug("Postcodify API 타임아웃")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Postcodify API 요청 실패: {type(e).__name__}")
            return None
        except Exception as e:
            logger.warning(f"Postcodify API 처리 중 오류: {type(e).__name__}")
            return None
    
    def _remove_duplicates(self, addresses: List[Dict]) -> List[Dict]:
        """중복 주소 제거"""
        seen = set()
        unique = []
        
        for addr in addresses:
            # 위치 기반 키 생성
            key = (addr['start'], addr['end'])
            if key not in seen:
                seen.add(key)
                unique.append(addr)
        
        return unique
    
    def mask_addresses(self, text: str) -> str:
        """
        텍스트에서 주소를 마스킹
        
        시큐어 코딩 가이드 준수:
        - 입력 검증
        - 안전한 문자열 처리
        
        Args:
            text: 마스킹할 텍스트
            
        Returns:
            마스킹된 텍스트
        """
        # 입력 검증
        if not isinstance(text, str):
            logger.warning("주소 마스킹: 잘못된 입력 타입")
            return text if text else ""
        
        if not text or not text.strip():
            return text
        
        try:
            addresses = self.detect_addresses_in_text(text)
            
            # 역순으로 정렬하여 뒤에서부터 마스킹 (인덱스 변경 방지)
            addresses.sort(key=lambda x: x.get('start', 0), reverse=True)
            
            masked_text = text
            for addr in addresses:
                start = addr.get('start', 0)
                end = addr.get('end', 0)
                
                # 인덱스 범위 검증
                if 0 <= start < len(masked_text) and start <= end <= len(masked_text):
                    masked_text = masked_text[:start] + "[주소]" + masked_text[end:]
            
            return masked_text
            
        except Exception as e:
            logger.error(f"주소 마스킹 중 오류: {e}", exc_info=True)
            return text  # 오류 발생 시 원본 반환


# 서비스 인스턴스 생성 (다른 서비스들과 동일한 패턴)
address_detection_service = AddressDetectionService()

