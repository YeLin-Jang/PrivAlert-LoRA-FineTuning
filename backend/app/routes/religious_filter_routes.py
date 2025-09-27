from flask import Blueprint, request
from flasgger import swag_from
import logging
import os
from app.services.religious_filter_service import ReligiousFilterService
from app.utils.api_utils import APIResponse, validate_text_input, handle_api_exception
from config import DOCS_DIR

# 블루프린트 생성
religious_filter_bp = Blueprint('religious_filter', __name__)

logger = logging.getLogger(__name__)


@religious_filter_bp.route('/detect', methods=['POST'])
@swag_from(os.path.join(DOCS_DIR, 'religious_filter_detect.yml'))
@handle_api_exception
def detect_religious_content():
    """
    종교 관련 민감 텍스트 탐지
    
    현재 구현된 필터링 기준:
    - 기독교: "하나님 비하", "예수 모독", "교회 훼손" 등
    - 이슬람: "알라 비하", "무함마드 모독", "꾸란 훼손" 등  
    - 불교: "부처 비하", "석가모니 모독", "불교 욕" 등
    - 일반 종교: "종교 비하", "신앙 모독", "신성 욕" 등
    
    일반적인 종교 용어는 필터링하지 않습니다:
    - "교회에 다닌다", "절에 가다", "성당에서 미사" 등
    """
    data = request.get_json()
    
    # 텍스트 입력 검증
    is_valid, result = validate_text_input(data, 'text', 10000)
    if not is_valid:
        return result
    
    text = result
    
    # 종교 필터링 서비스 호출
    service = ReligiousFilterService()
    filter_result = service.filter_text(text, mask_char="*")
    
    if not filter_result.get("success"):
        return APIResponse.error(
            filter_result.get("error", "필터링 처리 중 오류가 발생했습니다"),
            code=500
        )
    
    # 응답 데이터 구성
    detected_count = filter_result["statistics"]["total_detected"]
    response_data = {
        "original_text": filter_result["original_text"],
        "filtered_text": filter_result["filtered_text"],
        "detected_words": filter_result["detected_words"],
        "statistics": filter_result["statistics"],
        "compliance": filter_result["compliance"],
        "standards_applied": filter_result["standards_applied"],
        "has_sensitive_content": detected_count > 0
    }
    
    message = f"{detected_count}개의 민감한 종교 관련 표현이 감지되었습니다" if detected_count > 0 else "민감한 종교 관련 표현이 감지되지 않았습니다"
    
    logger.info(f"종교 필터링 완료: {detected_count}개 감지")
    return APIResponse.success(response_data, message)


@religious_filter_bp.route('/stats', methods=['GET'])
@swag_from(os.path.join(DOCS_DIR, 'religious_filter_stats.yml'))
@handle_api_exception
def get_filtering_stats():
    """
    종교 필터링 통계 정보 조회
    
    현재 적용된 필터링 기준과 통계를 반환합니다.
    """
    service = ReligiousFilterService()
    
    # 민감 단어 데이터 통계
    sensitive_words = service.sensitive_words
    stats = {
        "total_religions": len([k for k in sensitive_words.keys() if k not in ['context_exceptions', 'bypass_patterns']]),
        "religions": {},
        "total_keywords": 0,
        "total_patterns": 0
    }
    
    for religion, data in sensitive_words.items():
        if religion in ['context_exceptions', 'bypass_patterns']:
            continue
            
        keywords = data.get('keywords', [])
        patterns = data.get('patterns', [])
        
        stats["religions"][religion] = {
            "keywords_count": len(keywords),
            "patterns_count": len(patterns),
            "keywords": keywords[:5],  # 처음 5개만 표시
            "patterns": patterns[:3]   # 처음 3개만 표시
        }
        
        stats["total_keywords"] += len(keywords)
        stats["total_patterns"] += len(patterns)
    
    # 필터링 기준 정보
    standards = service.standards.get('standards', {})
    stats["filtering_criteria"] = {
        "legal_basis": standards.get('legal_basis', {}),
        "filtering_levels": list(standards.get('filtering_criteria', {}).keys()),
        "quality_assurance": standards.get('quality_assurance', {})
    }
    
    return APIResponse.success(
        {"statistics": stats},
        "종교 필터링 통계를 성공적으로 조회했습니다"
    )


@religious_filter_bp.route('/test', methods=['POST'])
@swag_from(os.path.join(DOCS_DIR, 'religious_filter_test.yml'))
@handle_api_exception
def test_religious_filter():
    """
    종교 필터링 테스트
    
    다양한 테스트 케이스를 통해 필터링 정확도를 검증합니다.
    """
    data = request.get_json() or {}
    test_cases = data.get('test_cases', [])
    
    if not test_cases:
        # 기본 테스트 케이스
        test_cases = [
            "하나님 비하하는 말",  # 감지되어야 함
            "교회에 다닌다",      # 감지되지 않아야 함
            "예수 모독하는 내용",  # 감지되어야 함
            "교수님이 좋다",      # 감지되지 않아야 함
            "부처 욕하는 글",     # 감지되어야 함
            "절에 가서 참배한다",  # 감지되지 않아야 함
            "알라 비하 표현",     # 감지되어야 함
            "이슬람 문화를 배운다", # 감지되지 않아야 함
            "종교 비하 발언",     # 감지되어야 함
            "신호등이 파란색이다"  # 감지되지 않아야 함
        ]
    
    service = ReligiousFilterService()
    results = []
    
    for i, test_text in enumerate(test_cases):
        result = service.filter_text(test_text, mask_char="*")
        results.append({
            "test_case": i + 1,
            "text": test_text,
            "detected": result["statistics"]["total_detected"] > 0,
            "detected_words": result["detected_words"],
            "expected": "감지되어야 함" if any(keyword in test_text for keyword in ["비하", "모독", "욕"]) else "감지되지 않아야 함",
            "correct": (result["statistics"]["total_detected"] > 0) == any(keyword in test_text for keyword in ["비하", "모독", "욕"])
        })
    
    # 전체 정확도 계산
    correct_count = sum(1 for r in results if r["correct"])
    total_count = len(results)
    accuracy = (correct_count / total_count * 100) if total_count > 0 else 0
    
    summary = {
        "total_tests": total_count,
        "correct_tests": correct_count,
        "accuracy": round(accuracy, 2),
        "message": f"테스트 완료: {correct_count}/{total_count} 정확 ({accuracy:.1f}%)"
    }
    
    return APIResponse.success(
        {"test_results": results, "summary": summary},
        f"테스트 완료: {correct_count}/{total_count} 정확 ({accuracy:.1f}%)"
    )
