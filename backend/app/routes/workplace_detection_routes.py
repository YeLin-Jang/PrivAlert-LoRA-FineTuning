import os
import logging
from flask import Blueprint, request, jsonify
from flasgger.utils import swag_from
from app.services.workplace_detection_service import workplace_detection_service
from app.utils.api_utils import APIResponse
from config import DOCS_DIR

logger = logging.getLogger(__name__)

# 블루프린트 생성
workplace_bp = Blueprint('workplace_detection', __name__)

@workplace_bp.route('/detect', methods=['POST'])
def detect_workplaces():
    """
    텍스트에서 직장명을 탐지합니다.
    
    ---
    consumes:
      - application/json
    parameters:
      - name: text
        in: body
        type: string
        required: true
        description: 분석할 텍스트
        example: "저는 삼성전자에서 근무하고 있습니다. LG전자와 협력하고 있어요."
    responses:
      200:
        description: 직장명 탐지 성공
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "2개의 직장명이 탐지되었습니다"
            data:
              type: object
              properties:
                detected:
                  type: boolean
                  example: true
                total_count:
                  type: integer
                  example: 2
                workplaces:
                  type: array
                  items:
                    type: object
                    properties:
                      text:
                        type: string
                        example: "삼성전자"
                      start:
                        type: integer
                        example: 3
                      end:
                        type: integer
                        example: 7
                      score:
                        type: number
                        example: 0.95
      400:
        description: 잘못된 요청
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              example: "텍스트가 필요합니다"
      500:
        description: 서버 오류
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              example: "모델 로딩에 실패했습니다"
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return APIResponse.error("텍스트가 필요합니다", code=400)
        
        text = data['text'].strip()
        if not text:
            return APIResponse.error("텍스트가 비어있습니다", code=400)
        
        # 텍스트 길이 제한
        if len(text) > 3000:
            return APIResponse.error("텍스트가 너무 깁니다 (최대 3,000자)", code=400)
        
        # 직장명 탐지 실행
        result = workplace_detection_service.detect_workplaces(text)
        
        return APIResponse.success(result, result['message'])
        
    except Exception as e:
        logger.error(f"직장명 탐지 API 오류: {e}")
        return APIResponse.error(f"직장명 탐지 중 오류가 발생했습니다: {str(e)}", code=500)

@workplace_bp.route('/mask', methods=['POST'])
def mask_workplaces():
    """
    텍스트에서 직장명을 마스킹합니다.
    
    ---
    consumes:
      - application/json
    parameters:
      - name: text
        in: body
        type: string
        required: true
        description: 마스킹할 텍스트
        example: "저는 삼성전자에서 근무하고 있습니다."
    responses:
      200:
        description: 직장명 마스킹 성공
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "직장명이 마스킹되었습니다"
            data:
              type: object
              properties:
                original_text:
                  type: string
                  example: "저는 삼성전자에서 근무하고 있습니다."
                masked_text:
                  type: string
                  example: "저는 [직장명]에서 근무하고 있습니다."
                workplaces_found:
                  type: integer
                  example: 1
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return APIResponse.error("텍스트가 필요합니다", code=400)
        
        text = data['text'].strip()
        if not text:
            return APIResponse.error("텍스트가 비어있습니다", code=400)
        
        # 텍스트 길이 제한
        if len(text) > 3000:
            return APIResponse.error("텍스트가 너무 깁니다 (최대 3,000자)", code=400)
        
        # 직장명 탐지 및 마스킹
        detection_result = workplace_detection_service.detect_workplaces(text)
        masked_text = workplace_detection_service.mask_workplaces(text)
        
        result = {
            "original_text": text,
            "masked_text": masked_text,
            "workplaces_found": detection_result['total_count'],
            "workplaces": detection_result['workplaces']
        }
        
        message = f"{detection_result['total_count']}개의 직장명이 마스킹되었습니다" if detection_result['detected'] else "직장명이 발견되지 않았습니다"
        
        return APIResponse.success(result, message)
        
    except Exception as e:
        logger.error(f"직장명 마스킹 API 오류: {e}")
        return APIResponse.error(f"직장명 마스킹 중 오류가 발생했습니다: {str(e)}", code=500)

@workplace_bp.route('/model-info', methods=['GET'])
def get_model_info():
    """
    직장명 탐지 모델 정보를 반환합니다.
    
    ---
    responses:
      200:
        description: 모델 정보 반환 성공
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                model_loaded:
                  type: boolean
                  example: true
                model_path:
                  type: string
                  example: "/path/to/model"
                base_model:
                  type: string
                  example: "klue/bert-base"
                model_type:
                  type: string
                  example: "LoRA + KLUE BERT"
                task:
                  type: string
                  example: "Named Entity Recognition (Organization)"
    """
    try:
        model_info = workplace_detection_service.get_model_info()
        return APIResponse.success(model_info, "모델 정보를 성공적으로 가져왔습니다")
        
    except Exception as e:
        logger.error(f"모델 정보 조회 오류: {e}")
        return APIResponse.error(f"모델 정보 조회 중 오류가 발생했습니다: {str(e)}", code=500)
