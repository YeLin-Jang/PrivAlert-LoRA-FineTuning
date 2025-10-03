"""
통합 필터링 서비스
"""

import logging
from typing import Dict, List, Any
from app.services.mask_regex import mask_regex_service

logger = logging.getLogger(__name__)


class IntegratedFilterService:
    """통합 필터링 서비스"""
    
    def __init__(self):
        """서비스 초기화"""
        # 정형 데이터 마스킹 서비스 사용
        self.mask_service = mask_regex_service
        
        logger.info("통합 필터링 서비스 초기화 완료")
    
    def filter_text(self, text: str, use_replacements: bool = True, filters: List[str] = None) -> Dict:
        """
        텍스트를 여러 필터링 모델을 통해 처리
        
        Args:
            text: 필터링할 텍스트
            use_replacements: 대체 단어 사용 여부
            filters: 적용할 필터 목록 (None이면 모든 필터 적용)
            
        Returns:
            통합 필터링 결과
        """
        if not text or not isinstance(text, str):
            return {
                "success": False,
                "error": "유효하지 않은 텍스트입니다",
                "original_text": text,
                "filtered_text": text,
                "filter_results": {},
                "overall_statistics": {}
            }
        
        # 기본 필터 목록 (모든 정형 데이터)
        if filters is None:
            filters = self.get_available_filters()
        
        original_text = text
        filtered_text = text
        filter_results = {}
        overall_statistics = {
            "total_detected": 0,
            "total_words": len(text.split()),
            "detection_rate": 0.0,
            "applied_filters": filters
        }
        
        # 각 필터별로 처리
        for filter_name in filters:
            try:
                # 개별 정형 데이터 필터 처리
                if filter_name in self.get_available_filters():
                    # 해당 필터만 활성화한 탐지 옵션 생성
                    detection_options = {filter_name: True}
                    
                    # 탐지
                    detection_result = self.mask_service.detect_sensitive_data(text, detection_options)
                    
                    # 마스킹
                    masked_text = self.mask_service.mask_sensitive_data(text, detection_options)
                    
                    if detection_result.get("detected", False):
                        filter_results[filter_name] = {
                            "success": True,
                            "detected_words": detection_result.get("details", []),
                            "statistics": {
                                "total_detected": detection_result.get("total_count", 0),
                                "categories": detection_result.get("categories", {})
                            },
                            "filtered_text": masked_text
                        }
                        filtered_text = masked_text
                        overall_statistics["total_detected"] += detection_result.get("total_count", 0)
                    else:
                        filter_results[filter_name] = {
                            "success": True,
                            "detected_words": [],
                            "statistics": {"total_detected": 0, "categories": {}},
                            "filtered_text": text
                        }
                else:
                    # 지원하지 않는 필터
                    filter_results[filter_name] = {
                        "success": False,
                        "error": f"지원하지 않는 필터: {filter_name}",
                        "detected_words": [],
                        "statistics": {}
                    }
                    
            except Exception as e:
                logger.error(f"{filter_name} 필터링 중 오류 발생: {e}")
                filter_results[filter_name] = {
                    "success": False,
                    "error": f"{filter_name} 필터링 중 오류 발생",
                    "detected_words": [],
                    "statistics": {}
                }
        
        # 전체 통계 계산
        if overall_statistics["total_words"] > 0:
            overall_statistics["detection_rate"] = round(
                (overall_statistics["total_detected"] / overall_statistics["total_words"] * 100), 2
            )
        
        # 민감 정보 감지 여부
        has_sensitive_content = overall_statistics["total_detected"] > 0
        
        result = {
            "success": True,
            "original_text": original_text,
            "filtered_text": filtered_text,
            "filter_results": filter_results,
            "overall_statistics": overall_statistics,
            "has_sensitive_content": has_sensitive_content
        }
        
        logger.info(f"통합 필터링 완료: 원본 길이={len(original_text)}, "
                   f"감지된 민감 정보={overall_statistics['total_detected']}개, "
                   f"적용된 필터={filters}")
        
        return result
    
    def get_available_filters(self) -> List[str]:
        """사용 가능한 필터 목록 반환"""
        return [
            "phone",         # 전화번호
            "rrn",           # 주민등록번호
            "passport",      # 여권번호
            "ip_address",    # IP주소
            "email",         # 이메일
            "account",       # 계좌번호
            "school",        # 학교명
            "address",       # 주소
            "driverLicense", # 운전면허번호
            "postalCode",    # 우편번호
            "workplace"      # 직장명 (AI 모델)
        ]
    
    def get_filter_statistics(self) -> Dict[str, Any]:
        """각 필터별 통계 정보 반환"""
        stats = {}
        
        # 개별 정형 데이터 필터 통계
        for category, patterns in self.mask_service.patterns.items():
            stats[category] = {
                "patterns": len(patterns),
                "description": {
                    "phone": "전화번호",
                    "rrn": "주민등록번호",
                    "passport": "여권번호",
                    "ip_address": "IP주소",
                    "email": "이메일",
                    "account": "계좌번호",
                    "school": "학교명"
                }.get(category, category),
                "supported": True
            }
        
        return stats
