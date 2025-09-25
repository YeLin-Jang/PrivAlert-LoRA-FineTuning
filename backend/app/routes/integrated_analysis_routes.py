"""
통합 분석 API 라우트

이미지와 텍스트를 한번에 처리하여 얼굴, 손가락, OCR, 종교 필터링을 수행합니다.
"""

import os
import logging
from flask import Blueprint, request, jsonify
from flasgger.utils import swag_from
from app.services.face_detection_service import FaceDetectionService
from app.services.hand_detection_service import HandDetectionService
from app.services.ocr_service import OCRService
from app.services.integrated_filter_service import IntegratedFilterService
from config import DOCS_DIR

logger = logging.getLogger(__name__)

# 블루프린트 생성
integrated_analysis_bp = Blueprint('integrated_analysis', __name__)

# 서비스 인스턴스들
face_service = FaceDetectionService()
hand_service = HandDetectionService()
ocr_service = OCRService()
filter_service = IntegratedFilterService()

@integrated_analysis_bp.route('/analyze', methods=['POST'])
@swag_from(os.path.join(DOCS_DIR, 'integrated_analysis.yml'))
def analyze_content():
    """
    이미지와 텍스트를 통합 분석
    
    요청:
    - image: 이미지 파일 (선택)
    - text: 텍스트 (선택)
    - blur_fingers: 손가락 블러 처리 여부 (기본값: true)
    - show_faces: 얼굴 표시 여부 (기본값: false)
    
    응답:
    - face_detection: 얼굴 검출 결과
    - hand_detection: 손가락 검출 결과
    - text_analysis: OCR 및 텍스트 필터링 결과
    - summary: 전체 요약
    """
    try:
        # 요청 데이터 검증
        image_file = request.files.get('image')
        text_input = request.form.get('text', '').strip()
        
        if not image_file and not text_input:
            return jsonify({
                "success": False,
                "error": "이미지 파일 또는 텍스트가 필요합니다",
                "code": 400
            }), 400
        
        # 이미지 파일 검증
        if image_file and image_file.filename == '':
            return jsonify({
                "success": False,
                "error": "유효하지 않은 이미지 파일입니다",
                "code": 400
            }), 400
        
        # 텍스트 길이 검증
        if text_input and len(text_input) > 10000:
            return jsonify({
                "success": False,
                "error": "텍스트가 너무 깁니다 (최대 10,000자)",
                "code": 400
            }), 400
        
        # 옵션 파라미터
        blur_fingers = request.form.get('blur_fingers', 'true').lower() in ['true', '1', 'yes']
        show_faces = request.form.get('show_faces', 'false').lower() in ['true', '1', 'yes']
        input_text = request.form.get('text', '')
        
        results = {
            "success": True,
            "face_detection": None,
            "hand_detection": None,
            "text_analysis": None,
            "summary": {
                "faces_detected": 0,
                "fingers_detected": 0,
                "sensitive_text_found": False,
                "religious_content_detected": False
            }
        }
        
        # 여러 이미지 분석
        image_files = request.files.getlist('image')
        if image_files and any(f.filename for f in image_files):
            all_face_count = 0
            all_finger_count = 0
            all_ocr_text = []
            face_results = []
            hand_results = []
            
            for idx, image_file in enumerate(image_files):
                if not image_file.filename:
                    continue
                    
                logger.info(f"이미지 {idx + 1} 분석 시작: {image_file.filename}")
                
                # 얼굴 검출
                face_result = face_service.detect_faces(image_file, save_result=True, return_image=show_faces)
                if show_faces and isinstance(face_result, tuple):
                    face_data, face_image = face_result
                else:
                    face_data = face_result
                    
                if face_data.get("success"):
                    all_face_count += face_data["count"]
                    face_results.append({
                        "image_index": idx + 1,
                        "filename": image_file.filename,
                        "count": face_data["count"],
                        "faces": face_data["faces"] if show_faces else None,
                        "result_image_url": face_data.get("result_image_url")
                    })
                
                # 손가락 검출
                hand_result = hand_service.detect_fingertips(image_file, save_preview=True, return_image=blur_fingers)
                if blur_fingers and isinstance(hand_result, tuple):
                    hand_data, hand_image = hand_result
                else:
                    hand_data = hand_result
                    
                if hand_data.get("success"):
                    all_finger_count += hand_data["count"]
                    hand_results.append({
                        "image_index": idx + 1,
                        "filename": image_file.filename,
                        "count": hand_data["count"],
                        "fingers": hand_data["fingers"] if blur_fingers else None,
                        "result_image_url": hand_data.get("result_image_url")
                    })
                
                # OCR 텍스트 추출
                try:
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                        image_file.save(tmp_file.name)
                        ocr_text = ocr_service.detect_text(tmp_file.name)
                        os.unlink(tmp_file.name)
                        
                        if ocr_text:
                            all_ocr_text.append(f"[이미지 {idx + 1}] {ocr_text}")
                except Exception as e:
                    logger.warning(f"이미지 {idx + 1} OCR 처리 중 오류: {e}")
            
            # 전체 결과 정리
            if face_results:
                results["face_detection"] = {
                    "total_count": all_face_count,
                    "message": f"총 {all_face_count}개의 얼굴이 {len(face_results)}개 이미지에서 감지되었습니다",
                    "images": face_results
                }
                results["summary"]["faces_detected"] = all_face_count
            
            if hand_results:
                results["hand_detection"] = {
                    "total_count": all_finger_count,
                    "message": f"총 {all_finger_count}개의 손가락이 {len(hand_results)}개 이미지에서 감지되었습니다",
                    "images": hand_results
                }
                results["summary"]["fingers_detected"] = all_finger_count
            
            # OCR 텍스트 합치기
            if all_ocr_text:
                input_text += "\n" + "\n".join(all_ocr_text)
        
        # 텍스트 분석 (OCR 결과 + 직접 입력 텍스트)
        if input_text.strip():
            # 종교 필터링 적용
            filter_result = filter_service.filter_text(input_text.strip(), mask_char="*", filters=["religious"])
            
            results["text_analysis"] = {
                "original_text": input_text.strip(),
                "filtered_text": filter_result.get("filtered_text", input_text.strip()),
                "religious_content_detected": filter_result.get("has_sensitive_content", False),
                "detected_words": filter_result.get("filter_results", {}).get("religious", {}).get("detected_words", []),
                "statistics": filter_result.get("overall_statistics", {})
            }
            
            results["summary"]["sensitive_text_found"] = filter_result.get("has_sensitive_content", False)
            results["summary"]["religious_content_detected"] = filter_result.get("has_sensitive_content", False)
        
        # 전체 요약 메시지 생성
        summary_parts = []
        if results["summary"]["faces_detected"] > 0:
            summary_parts.append(f"{results['summary']['faces_detected']}개의 얼굴이 탐지되었습니다")
        if results["summary"]["fingers_detected"] > 0:
            summary_parts.append(f"{results['summary']['fingers_detected']}개의 손가락이 탐지되었습니다")
        if results["summary"]["religious_content_detected"]:
            summary_parts.append("종교 관련 민감 텍스트가 발견되었습니다")
        
        results["summary"]["message"] = "; ".join(summary_parts) if summary_parts else "민감 정보가 발견되지 않았습니다"
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"통합 분석 중 오류 발생: {e}")
        return jsonify({
            "success": False,
            "error": "서버 내부 오류가 발생했습니다",
            "code": 500
        }), 500
