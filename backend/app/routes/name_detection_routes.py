# -*- coding: utf-8 -*-
"""
이름 탐지 API 라우트
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from
import os
import logging

from ..services.name_detection_service import name_detection_service

logger = logging.getLogger(__name__)

# Blueprint 생성
name_detection_bp = Blueprint('name_detection', __name__)

@name_detection_bp.route('/detect', methods=['POST'])
@swag_from('../../docs/name_detection.yml')
def detect_names():
    """
    텍스트에서 이름을 탐지합니다.
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
                "success": False,
                "message": "요청 데이터가 없습니다.",
                "data": None
            }), 400
        
        text = data.get('text', '')
        
        if not text or not text.strip():
            return jsonify({
                "success": False,
                "message": "텍스트를 입력해주세요.",
                "data": None
            }), 400
        
        # 이름 탐지 실행
        result = name_detection_service.detect_names(text)
        
        return jsonify({
            "success": result["success"],
            "message": result["message"],
            "data": {
                "names": result["names"],
                "count": result["count"]
            }
        }), 200 if result["success"] else 500
        
    except Exception as e:
        logger.error(f"이름 탐지 API 오류: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"서버 오류가 발생했습니다: {str(e)}",
            "data": None
        }), 500

@name_detection_bp.route('/mask', methods=['POST'])
@swag_from('../../docs/name_mask.yml')
def mask_names():
    """
    텍스트에서 이름을 마스킹합니다.
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
                "success": False,
                "message": "요청 데이터가 없습니다.",
                "data": None
            }), 400
        
        text = data.get('text', '')
        
        if not text or not text.strip():
            return jsonify({
                "success": False,
                "message": "텍스트를 입력해주세요.",
                "data": None
            }), 400
        
        # 이름 마스킹 실행
        result = name_detection_service.mask_names(text)
        
        return jsonify({
            "success": result["success"],
            "message": result["message"],
            "data": {
                "original_text": result["original_text"],
                "masked_text": result["masked_text"],
                "names": result["names"],
                "count": result["count"]
            }
        }), 200 if result["success"] else 500
        
    except Exception as e:
        logger.error(f"이름 마스킹 API 오류: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"서버 오류가 발생했습니다: {str(e)}",
            "data": None
        }), 500
