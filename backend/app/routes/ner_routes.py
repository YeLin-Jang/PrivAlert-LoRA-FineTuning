# -*- coding: utf-8 -*-
"""
NER API 라우트 - 사람 이름 추출
"""

from flask import Blueprint, request, jsonify
import logging

from ..services.ner_service import ner_service

logger = logging.getLogger(__name__)

# Blueprint 생성
ner_bp = Blueprint('ner', __name__)


@ner_bp.route('/name', methods=['POST'])
def extract_names():
    """
    텍스트에서 사람 이름(PER)만 추출합니다.
    
    요청 형식:
    {
        "text": "홍길동과 김수민이 함께 갔습니다."
    }
    
    응답 형식:
    {
        "names": ["홍길동", "김수민"]
    }
    """
    try:
        # Content-Type 확인
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
        else:
            # Form data로 처리
            data = request.form.to_dict()
        
        if not data:
            return jsonify({
                "error": "요청 데이터가 없습니다."
            }), 400
        
        text = data.get('text', '')
        
        # 입력 검증
        if not text or not text.strip():
            return jsonify({
                "error": "텍스트를 입력해주세요."
            }), 400
        
        # 길이 제한 (2000자)
        MAX_LENGTH = 2000
        if len(text) > MAX_LENGTH:
            return jsonify({
                "error": f"입력 텍스트는 최대 {MAX_LENGTH}자까지 가능합니다."
            }), 400
        
        # 이름 추출
        result = ner_service.extract_names(text)
        
        if not result["success"]:
            # 서버 오류는 500, 검증 오류는 400
            status_code = 500 if "서버 내부" in result.get("error", "") else 400
            return jsonify({
                "error": result.get("error", "알 수 없는 오류가 발생했습니다.")
            }), status_code
        
        # 성공 응답
        return jsonify({
            "names": result["names"]
        }), 200
        
    except Exception as e:
        # 개인정보 보호: 로그에 입력 텍스트나 추출된 이름을 직접 저장하지 않음
        logger.error(f"NER API 오류: {str(e)}", exc_info=True)
        return jsonify({
            "error": "서버 오류가 발생했습니다."
        }), 500

