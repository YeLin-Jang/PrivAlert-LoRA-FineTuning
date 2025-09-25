"""
통합 필터링 서비스

이 서비스는 OCR로 추출된 텍스트나 일반 텍스트를 여러 필터링 모델을 통해 처리합니다.
종교, KLIE 등 다양한 민감 정보를 탐지하고 필터링합니다.
"""

import logging
from typing import Dict, List, Any
from app.services.religious_filter_service import ReligiousFilterService

logger = logging.getLogger(__name__)


class IntegratedFilterService:
    """통합 필터링 서비스"""
    
    def __init__(self):
        """서비스 초기화"""
        self.religious_filter = ReligiousFilterService()
        # 향후 KLIE 등 다른 필터링 서비스들 추가 예정
        # self.klie_filter = KLIEFilterService()
        # self.personal_info_filter = PersonalInfoFilterService()
        
        logger.info("통합 필터링 서비스 초기화 완료")
    
    def filter_text(self, text: str, mask_char: str = "*", filters: List[str] = None) -> Dict:
        """
        텍스트를 여러 필터링 모델을 통해 처리
        
        Args:
            text: 필터링할 텍스트
            mask_char: 마스킹에 사용할 문자
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
        
        # 기본 필터 목록 (모든 필터 적용)
        if filters is None:
            filters = ["religious"]
        
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
                if filter_name == "religious":
                    result = self.religious_filter.filter_text(text, mask_char)
                    if result["success"]:
                        filter_results["religious"] = result
                        # 필터링된 텍스트로 업데이트
                        filtered_text = result["filtered_text"]
                        overall_statistics["total_detected"] += result["statistics"]["total_detected"]
                
                # 향후 다른 필터들 추가
                # elif filter_name == "klie":
                #     result = self.klie_filter.filter_text(text, mask_char)
                #     if result["success"]:
                #         filter_results["klie"] = result
                #         filtered_text = result["filtered_text"]
                #         overall_statistics["total_detected"] += result["statistics"]["total_detected"]
                
                # elif filter_name == "personal_info":
                #     result = self.personal_info_filter.filter_text(text, mask_char)
                #     if result["success"]:
                #         filter_results["personal_info"] = result
                #         filtered_text = result["filtered_text"]
                #         overall_statistics["total_detected"] += result["statistics"]["total_detected"]
                
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
        return ["religious"]  # 향후 "klie", "personal_info" 등 추가
    
    def get_filter_statistics(self) -> Dict[str, Any]:
        """각 필터별 통계 정보 반환"""
        stats = {}
        
        # 종교 필터 통계
        religious_stats = {}
        for religion, data in self.religious_filter.sensitive_words.items():
            if religion != "bypass_patterns":
                religious_stats[religion] = {
                    "keywords": len(data.get("keywords", [])),
                    "patterns": len(data.get("patterns", [])),
                    "total": len(data.get("keywords", [])) + len(data.get("patterns", []))
                }
        
        stats["religious"] = religious_stats
        
        # 향후 다른 필터들의 통계도 추가
        # stats["klie"] = self.klie_filter.get_statistics()
        # stats["personal_info"] = self.personal_info_filter.get_statistics()
        
        return stats
