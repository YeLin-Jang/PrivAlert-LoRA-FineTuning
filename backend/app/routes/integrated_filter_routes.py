"""
통합 필터링 API 라우트

이 모듈은 OCR로 추출된 텍스트나 일반 텍스트를 여러 필터링 모델을 통해 처리하는 API 엔드포인트를 제공합니다.
종교, KLIE 등 다양한 민감 정보를 탐지하고 필터링합니다.
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from
import logging
import os
from app.services.integrated_filter_service import IntegratedFilterService
from config import DOCS_DIR

# 블루프린트 생성
integrated_filter_bp = Blueprint('integrated_filter', __name__)

# 서비스 인스턴스 (싱글톤 패턴)
_filter_service = None

def get_filter_service():
    """통합 필터링 서비스 인스턴스 반환 (싱글톤)"""
    global _filter_service
    if _filter_service is None:
        _filter_service = IntegratedFilterService()
    return _filter_service

logger = logging.getLogger(__name__)


@integrated_filter_bp.route('/filter', methods=['POST'])
@swag_from(os.path.join(DOCS_DIR, 'integrated_filter.yml'))
def filter_text():
    """
    텍스트를 여러 필터링 모델을 통해 처리
    
    요청 본문:
    - text: 필터링할 텍스트 (필수)
    - mask_char: 마스킹에 사용할 문자 (선택, 기본값: "*")
    - filters: 적용할 필터 목록 (선택, 기본값: 모든 필터)
    
    응답:
    - success: 성공 여부
    - original_text: 원본 텍스트
    - filtered_text: 필터링된 텍스트
    - filter_results: 각 필터별 결과
    - overall_statistics: 전체 통계
    - has_sensitive_content: 민감 정보 감지 여부
    """
    try:
        # 요청 데이터 검증
        if not request.is_json:
            return jsonify({
                "success": False,
                "error": "Content-Type이 application/json이어야 합니다",
                "code": 400
            }), 400
        
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "요청 본문이 비어있습니다",
                "code": 400
            }), 400
        
        text = data.get('text')
        if not text:
            return jsonify({
                "success": False,
                "error": "텍스트가 제공되지 않았습니다",
                "code": 400
            }), 400
        
        if not isinstance(text, str):
            return jsonify({
                "success": False,
                "error": "텍스트는 문자열이어야 합니다",
                "code": 400
            }), 400
        
        # 텍스트 길이 제한 (10,000자)
        if len(text) > 10000:
            return jsonify({
                "success": False,
                "error": "텍스트가 너무 깁니다 (최대 10,000자)",
                "code": 400
            }), 400
        
        # 선택적 매개변수
        mask_char = data.get('mask_char', '*')
        filters = data.get('filters')  # None이면 모든 필터 적용
        
        # 마스킹 문자 검증
        if not isinstance(mask_char, str) or len(mask_char) != 1:
            return jsonify({
                "success": False,
                "error": "마스킹 문자는 한 글자여야 합니다",
                "code": 400
            }), 400
        
        # 필터 목록 검증
        if filters is not None:
            if not isinstance(filters, list):
                return jsonify({
                    "success": False,
                    "error": "필터 목록은 배열이어야 합니다",
                    "code": 400
                }), 400
            
            available_filters = get_filter_service().get_available_filters()
            invalid_filters = [f for f in filters if f not in available_filters]
            if invalid_filters:
                return jsonify({
                    "success": False,
                    "error": f"지원하지 않는 필터입니다: {invalid_filters}",
                    "code": 400
                }), 400
        
        # 통합 필터링 서비스 실행
        filter_service = get_filter_service()
        result = filter_service.filter_text(text, mask_char, filters)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"통합 필터링 중 오류 발생: {e}")
        return jsonify({
            "success": False,
            "error": "서버 내부 오류가 발생했습니다",
            "code": 500
        }), 500


@integrated_filter_bp.route('/filters', methods=['GET'])
@swag_from(os.path.join(DOCS_DIR, 'integrated_filter_list.yml'))
def get_available_filters():
    """
    사용 가능한 필터 목록 조회
    
    응답:
    - success: 성공 여부
    - filters: 사용 가능한 필터 목록
    """
    try:
        filter_service = get_filter_service()
        filters = filter_service.get_available_filters()
        
        return jsonify({
            "success": True,
            "filters": filters
        })
        
    except Exception as e:
        logger.error(f"필터 목록 조회 중 오류 발생: {e}")
        return jsonify({
            "success": False,
            "error": "서버 내부 오류가 발생했습니다",
            "code": 500
        }), 500


@integrated_filter_bp.route('/statistics', methods=['GET'])
@swag_from(os.path.join(DOCS_DIR, 'integrated_filter_stats.yml'))
def get_filter_statistics():
    """
    각 필터별 통계 정보 조회
    
    응답:
    - success: 성공 여부
    - statistics: 각 필터별 통계 정보
    """
    try:
        filter_service = get_filter_service()
        statistics = filter_service.get_filter_statistics()
        
        return jsonify({
            "success": True,
            "statistics": statistics
        })
        
    except Exception as e:
        logger.error(f"통계 조회 중 오류 발생: {e}")
        return jsonify({
            "success": False,
            "error": "서버 내부 오류가 발생했습니다",
            "code": 500
        }), 500
