# 통합 필터링 API

from flask import Blueprint, request
import logging
from app.services.integrated_filter_service import IntegratedFilterService
from app.utils.api_utils import APIResponse, validate_text_input

# 블루프린트 생성
integrated_filter_bp = Blueprint('integrated_filter', __name__)

logger = logging.getLogger(__name__)


@integrated_filter_bp.route('/filter', methods=['POST'])
def filter_text():
    """
    텍스트를 여러 필터링 모델을 통해 처리
    
    ---
    tags: [Integrated Filter]
    summary: 텍스트 필터링
    consumes: [application/json]
    produces: [application/json]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [text]
          properties:
            text: 
              type: string
              example: "개인정보: 010-1234-5678, 이메일: test@example.com"
              description: "분석할 텍스트"
            use_replacements:
              type: boolean
              default: true
              example: true
              description: "대체 단어 제시 여부"
            filters: 
              type: array
              items: {type: string}
              example: ["structured_data"]
              description: "적용할 필터 목록 (기본값: 모든 필터)"
    responses:
      200: {description: 성공}
      400: {description: 잘못된 요청}
      500: {description: 서버 오류}
    """
    # Content-Type 검증
    if not request.is_json:
        return APIResponse.error("Content-Type이 application/json이어야 합니다", code=400)
    
    data = request.get_json()
    
    # 데이터 형식 검증
    if not isinstance(data, dict):
        return APIResponse.error("요청 데이터 형식이 올바르지 않습니다", code=400)
    
    # 텍스트 입력 검증
    is_valid, result = validate_text_input(data, 'text', 10000)
    if not is_valid:
        return result
    
    text = result
    
    # 선택적 매개변수 검증
    use_replacements = data.get('use_replacements', True)
    if not isinstance(use_replacements, bool):
        return APIResponse.error("use_replacements는 boolean 값이어야 합니다", code=400)
    
    filters = data.get('filters')  # None이면 모든 필터 적용
    if filters is not None:
        if not isinstance(filters, list):
            return APIResponse.error("필터 목록은 배열이어야 합니다", code=400)
        
        # 사용 가능한 필터 검증
        filter_service = IntegratedFilterService()
        available_filters = filter_service.get_available_filters()
        invalid_filters = [f for f in filters if f not in available_filters]
        if invalid_filters:
            return APIResponse.error(f"지원하지 않는 필터입니다: {invalid_filters}", code=400)
    
    # 통합 필터링 서비스 실행
    filter_service = IntegratedFilterService()
    result = filter_service.filter_text(text, use_replacements, filters)
    
    if not result.get("success"):
        return APIResponse.error(
            result.get("error", "필터링 처리 중 오류가 발생했습니다"),
            code=500
        )
    
    # 응답 데이터 정리
    response_data = {
        "original_text": result["original_text"],
        "filtered_text": result["filtered_text"],
        "filter_results": result["filter_results"],
        "overall_statistics": result["overall_statistics"],
        "has_sensitive_content": result["has_sensitive_content"]
    }
    
    detected_count = result["overall_statistics"].get("total_detected", 0)
    message = f"{detected_count}개의 민감 정보가 감지되었습니다" if detected_count > 0 else "민감 정보가 감지되지 않았습니다"
    
    logger.info(f"통합 필터링 완료: {detected_count}개 감지, 필터: {filters or 'all'}")
    return APIResponse.success(response_data, message)


@integrated_filter_bp.route('/filters', methods=['GET'])
def get_available_filters():
    """
    사용 가능한 필터 목록 조회
    
    ---
    tags: [Integrated Filter]
    summary: 필터 목록 조회
    produces: [application/json]
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            success: {type: boolean}
            filters: {type: array, items: {type: string}}
            message: {type: string}
      500:
        description: 서버 오류
    """
    filter_service = IntegratedFilterService()
    filters = filter_service.get_available_filters()
    
    logger.info(f"사용 가능한 필터 목록 조회: {len(filters)}개")
    return APIResponse.success({"filters": filters}, "사용 가능한 필터 목록을 성공적으로 조회했습니다")


@integrated_filter_bp.route('/statistics', methods=['GET'])
def get_filter_statistics():
    """
    각 필터별 통계 정보 조회
    
    ---
    tags: [Integrated Filter]
    summary: 필터 통계 조회
    produces: [application/json]
    responses:
      200:
        description: 성공
        schema:
          type: object
          properties:
            success: {type: boolean}
            statistics: {type: object}
            message: {type: string}
      500:
        description: 서버 오류
    """
    filter_service = IntegratedFilterService()
    statistics = filter_service.get_filter_statistics()
    
    logger.info("필터 통계 정보 조회 완료")
    return APIResponse.success({"statistics": statistics}, "필터 통계 정보를 성공적으로 조회했습니다")
