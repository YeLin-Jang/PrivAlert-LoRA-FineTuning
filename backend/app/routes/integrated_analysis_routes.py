# 통합 분석 API

import logging
import os
import tempfile
from flask import Blueprint, request
from app.services.face_detection_service import FaceDetectionService
from app.services.hand_detection_service import HandDetectionService
from app.services.ocr_service import OCRService
from app.services.integrated_filter_service import IntegratedFilterService
from app.utils.api_utils import APIResponse, handle_api_exception

logger = logging.getLogger(__name__)

# 블루프린트 생성
integrated_analysis_bp = Blueprint('integrated_analysis', __name__)

@integrated_analysis_bp.route('/analyze', methods=['POST'])
def analyze_content():
    """
    이미지와 텍스트를 통합 분석하여 민감 정보를 탐지합니다.
    
    ---
    consumes:
      - multipart/form-data
    parameters:
      - name: image
        in: formData
        type: file
        required: false
        description: 분석할 이미지 파일 (jpg, png 등)
      - name: text
        in: formData
        type: string
        required: false
        description: 분석할 텍스트
      - name: blur_fingers
        in: formData
        type: boolean
        required: false
        default: true
        description: 손가락 블러 처리 여부
      - name: show_faces
        in: formData
        type: boolean
        required: false
        default: false
        description: 얼굴 상세 표시 여부
    responses:
      200:
        description: 통합 분석 성공
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            message:
              type: string
              example: "민감 정보가 발견되지 않았습니다"
            face_detection:
              type: object
              properties:
                total_count:
                  type: integer
                  example: 2
                message:
                  type: string
                  example: "총 2개의 얼굴이 1개 이미지에서 감지되었습니다"
                images:
                  type: array
                  items:
                    type: object
                    properties:
                      image_index:
                        type: integer
                        example: 1
                      filename:
                        type: string
                        example: "test.jpg"
                      count:
                        type: integer
                        example: 2
                      faces:
                        type: array
                        items:
                          type: object
                      result_image_url:
                        type: string
                        example: "/static/results/face/face_abc123.jpg"
            hand_detection:
              type: object
              properties:
                total_count:
                  type: integer
                  example: 5
                message:
                  type: string
                  example: "총 5개의 손가락이 1개 이미지에서 감지되었습니다"
                images:
                  type: array
                  items:
                    type: object
                    properties:
                      image_index:
                        type: integer
                        example: 1
                      filename:
                        type: string
                        example: "test.jpg"
                      count:
                        type: integer
                        example: 5
                      fingers:
                        type: array
                        items:
                          type: object
                      result_image_url:
                        type: string
                        example: "/static/results/hand/hand_abc123.jpg"
            text_analysis:
              type: object
              properties:
                original_text:
                  type: string
                  example: "원본 텍스트"
                filtered_text:
                  type: string
                  example: "필터링된 텍스트"
                religious_content_detected:
                  type: boolean
                  example: false
                detected_words:
                  type: array
                  items:
                    type: object
                statistics:
                  type: object
            summary:
              type: object
              properties:
                faces_detected:
                  type: integer
                  example: 2
                fingers_detected:
                  type: integer
                  example: 5
                sensitive_text_found:
                  type: boolean
                  example: false
                religious_content_detected:
                  type: boolean
                  example: false
                message:
                  type: string
                  example: "2개의 얼굴이 탐지되었습니다; 5개의 손가락이 탐지되었습니다"
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
              example: "이미지 파일 또는 텍스트가 필요합니다"
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
              example: "서버 내부 오류가 발생했습니다"
    """
    # 입력 데이터 검증
    image_files = request.files.getlist('image')
    text_input = request.form.get('text', '').strip()
    
    # 최소 하나의 입력이 필요
    valid_images = [f for f in image_files if f and f.filename]
    if not valid_images and not text_input:
        return APIResponse.error("이미지 파일 또는 텍스트가 필요합니다", code=400)
    
    # 텍스트 길이 검증
    if text_input and len(text_input) > 10000:
        return APIResponse.error("텍스트가 너무 깁니다 (최대 10,000자)", code=400)
    
    # 옵션 파라미터
    blur_fingers = request.form.get('blur_fingers', 'true').lower() in ['true', '1', 'yes']
    show_faces = request.form.get('show_faces', 'false').lower() in ['true', '1', 'yes']
    
    # 서비스 인스턴스 생성
    face_service = FaceDetectionService()
    hand_service = HandDetectionService()
    ocr_service = OCRService()
    filter_service = IntegratedFilterService()
    
    # 결과 초기화
    results = {
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
    
    # 이미지 분석 처리
    if valid_images:
        all_face_count = 0
        all_finger_count = 0
        all_ocr_text = []
        face_results = []
        hand_results = []
        
        for idx, image_file in enumerate(valid_images):
            logger.info(f"이미지 {idx + 1} 분석 시작: {image_file.filename}")
            
            # 얼굴 검출
            face_result = face_service.detect_faces(image_file, save_result=True, return_image=show_faces)
            if show_faces and isinstance(face_result, tuple):
                face_data, _ = face_result
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
            
            # 손가락 검출 (항상 실행)
            logger.info(f"손가락 감지 시작: blur_fingers={blur_fingers}")
            hand_result = hand_service.detect_fingertips(image_file, save_preview=True, return_image=True)
            if isinstance(hand_result, tuple):
                hand_data, _ = hand_result
                logger.info(f"손가락 감지 결과: success={hand_data.get('success', False)}, count={hand_data.get('count', 0)}")
            else:
                logger.info(f"손가락 감지 결과: success={hand_result.get('success', False)}, count={hand_result.get('count', 0)}")
            
            if blur_fingers and isinstance(hand_result, tuple):
                hand_data, _ = hand_result
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
                logger.info(f"손가락 감지 성공: {hand_data['count']}개, 이미지 URL: {hand_data.get('result_image_url')}")
            else:
                logger.warning(f"손가락 감지 실패: {hand_data}")
            
            # OCR 텍스트 추출 (파일 접근 충돌 방지를 위해 다른 방식 사용)
            try:
                # 파일 포인터를 처음으로 되돌림
                image_file.seek(0)
                image_data = image_file.read()
                
                if image_data:
                    # OCR 서비스에 직접 이미지 데이터 전달
                    ocr_text = ocr_service.detect_text_from_bytes(image_data)
                    
                    logger.info(f"이미지 {idx + 1} OCR 결과: '{ocr_text}' (타입: {type(ocr_text)})")
                    
                    if ocr_text and ocr_text.strip():
                        all_ocr_text.append(f"[이미지 {idx + 1}] {ocr_text}")
                        logger.info(f"OCR 텍스트 추가됨: {len(all_ocr_text)}개")
                    else:
                        logger.warning(f"이미지 {idx + 1} OCR 텍스트가 비어있음")
                else:
                    logger.warning(f"이미지 {idx + 1} 데이터가 비어있음")
            except Exception as e:
                logger.warning(f"이미지 {idx + 1} OCR 처리 중 오류: {e}")
        
        # 이미지 분석 결과 정리
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
        
        # OCR 텍스트 결과 추가 (항상 포함)
        logger.info(f"최종 OCR 텍스트 배열: {all_ocr_text} (개수: {len(all_ocr_text)})")
        results["ocr_text"] = {
            "texts": all_ocr_text,
            "total_count": len(all_ocr_text),
            "message": f"총 {len(all_ocr_text)}개 이미지에서 텍스트가 추출되었습니다" if all_ocr_text else "텍스트를 발견하지 못했습니다"
        }
        if all_ocr_text:
            text_input += "\n" + "\n".join(all_ocr_text)
    
    # 텍스트 분석 (OCR 결과 + 직접 입력 텍스트) - 항상 포함
    if text_input.strip():
        # 종교 필터만 적용
        filter_result = filter_service.filter_text(text_input.strip(), use_replacements=True, filters=["religious"])
        
        # 종교 관련 민감 정보
        religious_detected = filter_result.get("filter_results", {}).get("religious", {}).get("has_sensitive_content", False)
        religious_words = filter_result.get("filter_results", {}).get("religious", {}).get("detected_words", [])
        
        # 종교 내용 감지 여부 수정
        if religious_words:
            religious_detected = True
        
        results["text_analysis"] = {
            "original_text": text_input.strip(),
            "filtered_text": filter_result.get("filtered_text", text_input.strip()),
            "religious_content_detected": religious_detected,
            "detected_words": religious_words,
            "statistics": filter_result.get("overall_statistics", {})
        }
        
        results["summary"]["sensitive_text_found"] = filter_result.get("has_sensitive_content", False)
        results["summary"]["religious_content_detected"] = religious_detected
    else:
        # 텍스트가 없는 경우
        results["text_analysis"] = {
            "original_text": "",
            "filtered_text": "",
            "religious_content_detected": False,
            "detected_words": [],
            "statistics": {},
            "message": "텍스트를 발견하지 못했습니다"
        }
        results["summary"]["sensitive_text_found"] = False
        results["summary"]["religious_content_detected"] = False
    
    # 전체 요약 메시지 생성
    summary_parts = []
    if results["summary"]["faces_detected"] > 0:
        summary_parts.append(f"{results['summary']['faces_detected']}개의 얼굴이 탐지되었습니다")
    if results["summary"]["fingers_detected"] > 0:
        summary_parts.append(f"{results['summary']['fingers_detected']}개의 손가락이 탐지되었습니다")
    if results["summary"]["religious_content_detected"]:
        summary_parts.append("종교 관련 민감 텍스트가 발견되었습니다")
    
    results["summary"]["message"] = "; ".join(summary_parts) if summary_parts else "민감 정보가 발견되지 않았습니다"
    
    # 로깅
    total_detected = (results["summary"]["faces_detected"] + 
                     results["summary"]["fingers_detected"] + 
                     (1 if results["summary"]["religious_content_detected"] else 0))
    logger.info(f"통합 분석 완료: {total_detected}개 민감 정보 감지")
    
    return APIResponse.success({"data": results}, results["summary"]["message"])
