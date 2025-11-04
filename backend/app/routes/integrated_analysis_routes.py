# 통합 분석 API

import logging
import os
import tempfile
import uuid
from io import BytesIO
from flask import Blueprint, request
from werkzeug.datastructures import FileStorage
from app.services.face_detection_service import FaceDetectionService
from app.services.hand_detection_service import HandDetectionService
from app.services.ocr_service import OCRService
from app.services.integrated_filter_service import IntegratedFilterService
from app.services.mask_regex import mask_regex_service
from app.utils.api_utils import APIResponse, handle_api_exception
from app.utils.image_sanitize import sanitize_image
from config import BASE_DATA_DIR

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
    
    # 보안: 파일 리스트 검증 (최대 5개)
    from app.utils.security_utils import validate_file_list, validate_text_input, validate_image_file
    
    # 파일 개수 검증 (최대 5개)
    # 빈 파일 제외하고 실제 파일 개수 확인
    actual_files = [f for f in image_files if f and f.filename]
    if len(actual_files) > 5:
        return APIResponse.error("이미지/영상 파일은 최대 5개까지 업로드할 수 있습니다", code=400)
    
    valid_images = []
    for f in actual_files:
        is_valid, error_msg = validate_image_file(f)
        if is_valid:
            valid_images.append(f)
        else:
            logger.warning(f"파일 검증 실패: {f.filename}")
            # 검증 실패한 파일은 건너뛰기
    
    # 최소 하나의 입력이 필요
    if not valid_images and not text_input:
        return APIResponse.error("이미지 파일 또는 텍스트가 필요합니다", code=400)
    
    # 보안: 텍스트 검증 (최대 3000자)
    if text_input:
        is_valid, error_msg = validate_text_input(text_input, max_length=3000)
        if not is_valid:
            return APIResponse.error(error_msg or "텍스트 입력 검증 실패", code=400)
    
    # 옵션 파라미터
    blur_fingers = request.form.get('blur_fingers', 'true').lower() in ['true', '1', 'yes']
    show_faces = request.form.get('show_faces', 'false').lower() in ['true', '1', 'yes']
    
    # 탐지 옵션 파라미터 (프론트엔드에서 전달) - 정형 데이터 + AI 탐지
    detection_options = {
        'phone': request.form.get('detect_phone', 'false').lower() in ['true', '1', 'yes'],
        'rrn': request.form.get('detect_rrn', 'false').lower() in ['true', '1', 'yes'],
        'passport': request.form.get('detect_passport', 'false').lower() in ['true', '1', 'yes'],
        'ip_address': request.form.get('detect_ip_address', 'false').lower() in ['true', '1', 'yes'],
        'email': request.form.get('detect_email', 'false').lower() in ['true', '1', 'yes'],
        'account': request.form.get('detect_account', 'false').lower() in ['true', '1', 'yes'],
        'school': request.form.get('detect_school', 'false').lower() in ['true', '1', 'yes'],
        'workplace': request.form.get('detect_workplace', 'false').lower() in ['true', '1', 'yes'],
        'name': request.form.get('detect_name', 'false').lower() in ['true', '1', 'yes'],
        'address': request.form.get('detect_address', 'false').lower() in ['true', '1', 'yes'],
        'driverLicense': request.form.get('detect_driverLicense', 'false').lower() in ['true', '1', 'yes'],
        'postalCode': request.form.get('detect_postalCode', 'false').lower() in ['true', '1', 'yes']
    }
    
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
            "sensitive_text_found": False
        }
    }
    
    # 이미지 분석 처리
    if valid_images:
        all_face_count = 0
        all_finger_count = 0
        all_ocr_text = []
        face_results = []
        hand_results = []
        sanitize_results = []
        
        for idx, image_file in enumerate(valid_images):
            logger.info(f"이미지 {idx + 1} 분석 시작: {image_file.filename}")

            # 0) 업로드 즉시 EXIF/메타데이터 제거 (프론트 수정 없이 투명 처리)
            try:
                image_file.seek(0)
                original_bytes = image_file.read()
                cleaned_bytes, cleaned_ext, report = sanitize_image(original_bytes, keep_icc=True, target_format=None)

                # 결과 저장 (결과 페이지에서 다운로드할 수 있도록 URL 제공)
                os.makedirs(os.path.join(BASE_DATA_DIR, "image"), exist_ok=True)
                new_name = f"sanitized_{uuid.uuid4().hex}.{cleaned_ext}"
                save_path = os.path.join(BASE_DATA_DIR, "image", new_name)
                with open(save_path, "wb") as f:
                    f.write(cleaned_bytes)
                sanitized_url = f"/data/image/{new_name}"

                # 한국어 요약 생성
                def _human_size(n: int) -> str:
                    units = ["B", "KB", "MB", "GB"]
                    i = 0
                    x = float(n)
                    while x >= 1024 and i < len(units) - 1:
                        x /= 1024.0
                        i += 1
                    return f"{x:.1f} {units[i]}"

                msgs = []
                exif_removed = bool(report.get("exif_removed"))
                gps_removed = bool(report.get("gps_removed"))
                if exif_removed:
                    msgs.append("EXIF 정보를 제거했어요")
                else:
                    msgs.append("EXIF 정보가 없었어요")
                if gps_removed:
                    msgs.append("위치정보(GPS)를 제거했어요")
                else:
                    msgs.append("위치정보(GPS)가 없었어요")

                target_fmt = report.get("target_format") or "-"
                msgs.append(f"저장 포맷: {target_fmt}")
                size_val = report.get("size")
                if isinstance(size_val, int):
                    msgs.append(f"최종 크기: {_human_size(size_val)}")

                sanitize_results.append({
                    "image_index": idx + 1,
                    "filename": image_file.filename,
                    "sanitized_filename": new_name,
                    "sanitized_url": sanitized_url,
                    "report": report,
                    "summary_ko": " · ".join(msgs),
                    "details_ko": {
                        "exif": "제거됨" if exif_removed else "없음",
                        "gps": "제거됨" if gps_removed else "없음",
                        "format": target_fmt,
                        "size": _human_size(size_val) if isinstance(size_val, int) else None
                    }
                })

                # 이후 파이프라인은 정제된 바이트로 진행
                image_file = FileStorage(stream=BytesIO(cleaned_bytes), filename=new_name, content_type=f"image/{cleaned_ext}")
            except Exception as e:
                logger.warning(f"이미지 {idx + 1} EXIF 정제 중 오류: {e}")
            
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
            
            # hand_result가 튜플인지 딕셔너리인지 확인
            if isinstance(hand_result, tuple):
                hand_data, _ = hand_result
            else:
                hand_data = hand_result
                
            logger.info(f"손가락 감지 결과: success={hand_data.get('success', False)}, count={hand_data.get('count', 0)}")
                
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

        # EXIF/메타데이터 제거 결과 추가 (프론트는 이 정보를 사용해 변화 설명과 다운로드 제공 가능)
        if sanitize_results:
            results["image_sanitization"] = {
                "message": f"총 {len(sanitize_results)}개 이미지의 메타데이터를 제거했습니다",
                "items": sanitize_results
            }
        
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
        # 활성화된 필터 목록 생성
        active_filters = [key for key, value in detection_options.items() if value]
        logger.info(f"활성화된 탐지 필터: {active_filters}")
        
        # 통합 필터 서비스 사용 (이름 탐지 포함)
        filter_result = filter_service.filter_text(text_input.strip(), use_replacements=True, filters=active_filters)
        
        # 결과 처리
        structured_data_result = {
            "detected": filter_result.get("overall_statistics", {}).get("total_detected", 0) > 0,
            "total_count": filter_result.get("overall_statistics", {}).get("total_detected", 0),
            "categories": {}
        }
        
        # 필터별 결과를 카테고리로 변환
        for filter_name, result in filter_result.get("filter_results", {}).items():
            if result.get("success") and result.get("statistics", {}).get("total_detected", 0) > 0:
                structured_data_result["categories"][filter_name] = {
                    "count": result["statistics"]["total_detected"],
                    "items": result["detected_words"]
                }
        
        masked_text = filter_result.get("filtered_text", text_input.strip())
        
        results["text_analysis"] = {
            "original_text": text_input.strip(),
            "masked_text": masked_text,  # 마스킹된 텍스트 추가
            "statistics": {},
            "structured_data": structured_data_result
        }
        
        results["summary"]["sensitive_text_found"] = structured_data_result.get("detected", False)
        
        # 정형 데이터 탐지 결과 요약에 추가
        if structured_data_result.get("detected", False):
            results["summary"]["structured_data_detected"] = True
            results["summary"]["structured_data_count"] = structured_data_result.get("total_count", 0)
    else:
        # 텍스트가 없는 경우
        results["text_analysis"] = {
            "original_text": "",
            "masked_text": "",
            "statistics": {},
            "message": "텍스트를 발견하지 못했습니다"
        }
        results["summary"]["sensitive_text_found"] = False
    
    # 전체 요약 메시지 생성
    summary_parts = []
    if results["summary"]["faces_detected"] > 0:
        summary_parts.append(f"{results['summary']['faces_detected']}개의 얼굴이 탐지되었습니다")
    if results["summary"]["fingers_detected"] > 0:
        summary_parts.append(f"{results['summary']['fingers_detected']}개의 손가락이 탐지되었습니다")
    
    # 정형 데이터 탐지 결과를 개별적으로 추가
    if results.get("text_analysis") and results["text_analysis"].get("structured_data"):
        structured_data = results["text_analysis"]["structured_data"]
        if structured_data.get("detected", False):
            for category, data in structured_data.get("categories", {}).items():
                if data.get("count", 0) > 0:
                    category_names = {
                        "phone": "전화번호",
                        "rrn": "주민등록번호", 
                        "passport": "여권번호",
                        "ip_address": "IP주소",
                        "email": "이메일",
                        "account": "계좌번호",
                        "school": "학교명"
                    }
                    category_name = category_names.get(category, category)
                    summary_parts.append(f"{data['count']}개의 {category_name}이 탐지되었습니다")
    
    results["summary"]["message"] = "; ".join(summary_parts) if summary_parts else "민감 정보가 발견되지 않았습니다"
    
    # 로깅
    total_detected = (results["summary"]["faces_detected"] + 
                     results["summary"]["fingers_detected"] + 
                     (1 if results["summary"]["sensitive_text_found"] else 0))
    logger.info(f"통합 분석 완료: {total_detected}개 민감 정보 감지")
    
    # 보안: 원본 파일 데이터 메모리에서 정리
    # 이미 처리된 파일들은 메모리에서 제거됨
    # 참고: Flask의 FileStorage는 요청 완료 후 자동으로 정리되지만, 명시적으로 처리
    import gc
    gc.collect()  # 가비지 컬렉션 강제 실행
    
    return APIResponse.success({"data": results}, results["summary"]["message"])
