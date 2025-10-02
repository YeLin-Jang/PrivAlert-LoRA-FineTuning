# -*- coding: utf-8 -*-
"""
이름 탐지 및 마스킹 처리 API 라우트
"""

import os
import logging
from flask import Blueprint, request, jsonify
from flasgger import swag_from
from app.services.name_detection_service import name_detection_service
from app.utils.api_utils import validate_request_data

logger = logging.getLogger(__name__)

# 블루프린트 생성
name_bp = Blueprint('name_detection', __name__)

@name_bp.route('/detect', methods=['POST'])
@swag_from({
    'tags': ['Name Detection'],
    'summary': '텍스트에서 이름 탐지',
    'description': '주어진 텍스트에서 개인 이름을 탐지합니다.',
    'parameters': [
        {
            'name': 'text',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': '분석할 텍스트'
        }
    ],
    'responses': {
        200: {
            'description': '이름 탐지 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'original_text': {'type': 'string'},
                            'detected_names': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'text': {'type': 'string'},
                                        'start': {'type': 'integer'},
                                        'end': {'type': 'integer'},
                                        'confidence': {'type': 'number'}
                                    }
                                }
                            },
                            'name_count': {'type': 'integer'}
                        }
                    }
                }
            }
        },
        400: {
            'description': '잘못된 요청',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'error': {'type': 'string'}
                }
            }
        }
    }
})
def detect_names():
    """텍스트에서 이름 탐지"""
    try:
        # 요청 데이터 검증
        data = request.get_json() or request.form
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': '텍스트가 제공되지 않았습니다'
            }), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({
                'success': False,
                'error': '텍스트가 비어있습니다'
            }), 400
        
        # 이름 탐지
        detected_names = name_detection_service.detect_names(text)
        
        return jsonify({
            'success': True,
            'data': {
                'original_text': text,
                'detected_names': detected_names,
                'name_count': len(detected_names)
            }
        })
        
    except Exception as e:
        logger.error(f"이름 탐지 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'이름 탐지 중 오류가 발생했습니다: {str(e)}'
        }), 500

@name_bp.route('/mask', methods=['POST'])
@swag_from({
    'tags': ['Name Detection'],
    'summary': '텍스트에서 이름 마스킹',
    'description': '주어진 텍스트에서 개인 이름을 마스킹 처리합니다.',
    'parameters': [
        {
            'name': 'text',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': '마스킹할 텍스트'
        },
        {
            'name': 'mask_char',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'description': '마스킹에 사용할 문자 (기본값: *)'
        }
    ],
    'responses': {
        200: {
            'description': '이름 마스킹 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'original_text': {'type': 'string'},
                            'masked_text': {'type': 'string'},
                            'detected_names': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'text': {'type': 'string'},
                                        'start': {'type': 'integer'},
                                        'end': {'type': 'integer'},
                                        'confidence': {'type': 'number'}
                                    }
                                }
                            },
                            'mask_count': {'type': 'integer'}
                        }
                    }
                }
            }
        }
    }
})
def mask_names():
    """텍스트에서 이름 마스킹 처리"""
    try:
        # 요청 데이터 검증
        data = request.get_json() or request.form
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': '텍스트가 제공되지 않았습니다'
            }), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({
                'success': False,
                'error': '텍스트가 비어있습니다'
            }), 400
        
        mask_char = data.get('mask_char', '*')
        
        # 이름 마스킹 처리
        result = name_detection_service.mask_names(text, mask_char)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        logger.error(f"이름 마스킹 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'이름 마스킹 중 오류가 발생했습니다: {str(e)}'
        }), 500

@name_bp.route('/rewrite', methods=['POST'])
@swag_from({
    'tags': ['Name Detection'],
    'summary': '마스킹된 텍스트 리라이팅',
    'description': '마스킹된 텍스트를 자연스럽게 리라이팅합니다.',
    'parameters': [
        {
            'name': 'text',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': '리라이팅할 텍스트'
        },
        {
            'name': 'use_openai',
            'in': 'formData',
            'type': 'boolean',
            'required': False,
            'description': 'OpenAI API 사용 여부 (기본값: false)'
        }
    ],
    'responses': {
        200: {
            'description': '텍스트 리라이팅 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'original_text': {'type': 'string'},
                            'rewritten_text': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
})
def rewrite_text():
    """마스킹된 텍스트 리라이팅"""
    try:
        # 요청 데이터 검증
        data = request.get_json() or request.form
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': '텍스트가 제공되지 않았습니다'
            }), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({
                'success': False,
                'error': '텍스트가 비어있습니다'
            }), 400
        
        use_openai = data.get('use_openai', False)
        
        # 텍스트 리라이팅
        rewritten_text = name_detection_service.rewrite_text(text, use_openai)
        
        return jsonify({
            'success': True,
            'data': {
                'original_text': text,
                'rewritten_text': rewritten_text
            }
        })
        
    except Exception as e:
        logger.error(f"텍스트 리라이팅 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'텍스트 리라이팅 중 오류가 발생했습니다: {str(e)}'
        }), 500

@name_bp.route('/process', methods=['POST'])
@swag_from({
    'tags': ['Name Detection'],
    'summary': '이름 탐지, 마스킹, 리라이팅 통합 처리',
    'description': '텍스트에서 이름을 탐지하고 마스킹 처리한 후 리라이팅까지 한 번에 처리합니다.',
    'parameters': [
        {
            'name': 'text',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': '처리할 텍스트'
        },
        {
            'name': 'mask_char',
            'in': 'formData',
            'type': 'string',
            'required': False,
            'description': '마스킹에 사용할 문자 (기본값: *)'
        },
        {
            'name': 'use_openai',
            'in': 'formData',
            'type': 'boolean',
            'required': False,
            'description': 'OpenAI API 사용 여부 (기본값: false)'
        }
    ],
    'responses': {
        200: {
            'description': '통합 처리 성공',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'original_text': {'type': 'string'},
                            'masked_text': {'type': 'string'},
                            'rewritten_text': {'type': 'string'},
                            'detected_names': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'text': {'type': 'string'},
                                        'start': {'type': 'integer'},
                                        'end': {'type': 'integer'},
                                        'confidence': {'type': 'number'}
                                    }
                                }
                            },
                            'mask_count': {'type': 'integer'}
                        }
                    }
                }
            }
        }
    }
})
def process_text():
    """이름 탐지, 마스킹, 리라이팅 통합 처리"""
    try:
        # 요청 데이터 검증
        data = request.get_json() or request.form
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': '텍스트가 제공되지 않았습니다'
            }), 400
        
        text = data['text'].strip()
        if not text:
            return jsonify({
                'success': False,
                'error': '텍스트가 비어있습니다'
            }), 400
        
        mask_char = data.get('mask_char', '*')
        use_openai = data.get('use_openai', False)
        
        # 1단계: 이름 마스킹 처리
        mask_result = name_detection_service.mask_names(text, mask_char)
        
        # 2단계: 리라이팅 처리
        rewritten_text = name_detection_service.rewrite_text(
            mask_result['masked_text'], 
            use_openai
        )
        
        return jsonify({
            'success': True,
            'data': {
                'original_text': text,
                'masked_text': mask_result['masked_text'],
                'rewritten_text': rewritten_text,
                'detected_names': mask_result['detected_names'],
                'mask_count': mask_result['mask_count']
            }
        })
        
    except Exception as e:
        logger.error(f"통합 처리 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'텍스트 처리 중 오류가 발생했습니다: {str(e)}'
        }), 500

@name_bp.route('/status', methods=['GET'])
@swag_from({
    'tags': ['Name Detection'],
    'summary': '이름 탐지 서비스 상태 확인',
    'description': '이름 탐지 모델의 로딩 상태를 확인합니다.',
    'responses': {
        200: {
            'description': '서비스 상태',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'model_loaded': {'type': 'boolean'},
                            'device': {'type': 'string'},
                            'service_status': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
})
def get_status():
    """이름 탐지 서비스 상태 확인"""
    try:
        return jsonify({
            'success': True,
            'data': {
                'model_loaded': name_detection_service.model_loaded,
                'device': name_detection_service.device,
                'service_status': 'ready' if name_detection_service.model_loaded else 'not_loaded'
            }
        })
        
    except Exception as e:
        logger.error(f"상태 확인 API 오류: {e}")
        return jsonify({
            'success': False,
            'error': f'상태 확인 중 오류가 발생했습니다: {str(e)}'
        }), 500
