# 통합 분석 API

import logging
import os
import uuid
from io import BytesIO
from flask import Blueprint, request
from werkzeug.datastructures import FileStorage
try:
    from app.services.face_detection_service import FaceDetectionService
    FACE_DETECTION_AVAILABLE = True
except ImportError:
    FACE_DETECTION_AVAILABLE = False
    FaceDetectionService = None

try:
    from app.services.hand_detection_service import HandDetectionService
    HAND_DETECTION_AVAILABLE = True
except ImportError:
    HAND_DETECTION_AVAILABLE = False
    HandDetectionService = None

try:
    from app.services.ocr_service import OCRService
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    OCRService = None
from app.services.integrated_filter_service import IntegratedFilterService
from app.services.mask_regex import mask_regex_service
from app.utils.api_utils import APIResponse, handle_api_exception
from app.utils.image_sanitize import sanitize_image
from app.utils.file_cleanup import (
    generate_session_id, register_file, cleanup_session_files,
    cleanup_file, get_session_files
)
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
                        example: "/data/results/face/face_abc123.jpg"
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
                        example: "/data/results/hand/hand_abc123.jpg"
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
    
    # 보안: 텍스트 검증 (최대 3000자) 및 XSS/SQL Injection 방지
    if text_input:
        # 길이 검증
        is_valid, error_msg = validate_text_input(text_input, max_length=3000)
        if not is_valid:
            return APIResponse.error(error_msg or "텍스트 입력 검증 실패", code=400)
        
        # SQL Injection 패턴 검증
        from app.utils.input_sanitizer import validate_no_sql_injection
        is_safe, sql_error = validate_no_sql_injection(text_input)
        if not is_safe:
            logger.warning(f"SQL Injection 시도 감지: text_length={len(text_input)}, ip={request.remote_addr}")
            return APIResponse.error("허용되지 않은 문자가 포함되어 있습니다", code=400)
    
    # 세션 ID 생성 또는 가져오기 (프론트엔드에서 전달 가능)
    session_id = request.form.get('session_id') or request.headers.get('X-Session-ID')
    if not session_id:
        session_id = generate_session_id()
    
    # 옵션 파라미터
    blur_fingers = request.form.get('blur_fingers', 'true').lower() in ['true', '1', 'yes']
    show_faces = request.form.get('show_faces', 'false').lower() in ['true', '1', 'yes']
    
    # 탐지 옵션 파라미터 (로그인된 사용자는 DB에서, 비로그인은 요청에서)
    # 기본값: 모두 False
    default_detection_options = {
        'phone': False,
        'rrn': False,
        'passport': False,
        'ip_address': False,
        'email': False,
        'account': False,
        'school': False,
        'workplace': False,
        'name': False,
        'address': False,
        'face': False,
        'fingerprint': False,
        'driverLicense': False,
        'postalCode': False
    }
    
    detection_options = default_detection_options.copy()
    
    # 로그인된 사용자인 경우 DB에서 필터링 설정 가져오기
    try:
        from app.utils.decorators import login_required
        from app.models.user import UserFilteringSettings
        
        # 세션 쿠키 확인
        session_id = request.cookies.get('session_id')
        if session_id:
            from app.models.session import UserSession
            session = UserSession.find_by_session_id(session_id)
            if session and session.is_active and not session.is_expired():
                user = session.user
                if user and user.is_active:
                    # 사용자 필터링 설정 조회
                    settings = user.filtering_settings
                    if settings:
                        user_options = settings.get_detection_options()
                        # DB에서 가져온 설정으로 업데이트
                        for key in detection_options.keys():
                            if key in user_options:
                                detection_options[key] = user_options[key]
                        logger.info(f"사용자 필터링 설정 사용: user_id={user.id}, options={detection_options}")
    except Exception as e:
        # 로그인 체크 실패 시 무시하고 기본값 사용
        logger.debug(f"사용자 필터링 설정 로드 실패 (무시됨): {e}")
    
    # 프론트엔드에서 명시적으로 전달된 옵션이 있으면 우선 적용
    for key in detection_options.keys():
        form_value = request.form.get(f'detect_{key}', None)
        if form_value is not None:
            detection_options[key] = form_value.lower() in ['true', '1', 'yes']
    
    # 서비스 인스턴스 생성 (사용 가능한 것만)
    face_service = FaceDetectionService() if FACE_DETECTION_AVAILABLE else None
    hand_service = HandDetectionService() if HAND_DETECTION_AVAILABLE else None
    ocr_service = OCRService() if OCR_AVAILABLE else None
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
            original_bytes = None
            cleaned_bytes = None
            try:
                image_file.seek(0)
                original_bytes = image_file.read()
                cleaned_bytes, cleaned_ext, report = sanitize_image(original_bytes, keep_icc=True, target_format=None)

                # 보안: 원본 바이트 데이터 메모리에서 즉시 정리
                original_bytes = None

                # 결과 저장 (결과 페이지에서 다운로드할 수 있도록 URL 제공)
                os.makedirs(os.path.join(BASE_DATA_DIR, "image"), exist_ok=True)
                new_name = f"sanitized_{uuid.uuid4().hex}.{cleaned_ext}"
                save_path = os.path.join(BASE_DATA_DIR, "image", new_name)
                with open(save_path, "wb") as f:
                    f.write(cleaned_bytes)
                sanitized_url = f"/data/results/image/{new_name}"
                
                # 세션에 파일 등록 (자동 삭제를 위해)
                register_file(session_id, save_path, BASE_DATA_DIR)

                # 보안: 정제된 바이트도 메모리에서 정리 (파일 저장 후)
                cleaned_bytes = None

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

                # 이후 파이프라인은 정제된 파일을 읽어서 사용
                # 보안: 파일 저장 후 원본/정제 바이트 메모리 정리 완료
                # FileStorage는 파일에서 읽어오도록 변경
                with open(save_path, "rb") as f:
                    cleaned_stream = BytesIO(f.read())
                cleaned_stream.seek(0)
                image_file = FileStorage(stream=cleaned_stream, filename=new_name, content_type=f"image/{cleaned_ext}")
                # cleaned_stream은 FileStorage가 관리하므로 자동으로 정리됨
            except Exception as e:
                logger.warning(f"이미지 {idx + 1} EXIF 정제 중 오류: {e}")
                # 보안: 오류 발생 시에도 메모리 정리
                original_bytes = None
                cleaned_bytes = None
            
            # 얼굴 검출 (사용자 선택에 따라)
            if show_faces and face_service:
                face_result = face_service.detect_faces(image_file, save_result=True, return_image=True)
                if isinstance(face_result, tuple):
                    face_data, _ = face_result
                else:
                    face_data = face_result
            elif face_service:
                # 얼굴 검출만 수행 (이미지 반환 안 함)
                face_result = face_service.detect_faces(image_file, save_result=False, return_image=False)
                face_data = face_result if isinstance(face_result, dict) else {"success": False}
            else:
                face_data = {"success": False, "message": "얼굴 탐지 서비스를 사용할 수 없습니다 (OpenCV 미설치)"}
                
            if face_data.get("success"):
                all_face_count += face_data["count"]
                result_url = face_data.get("result_image_url") if show_faces else None
                # URL에서 실제 파일 경로 계산하여 세션에 등록
                if result_url:
                    # /data/results/face/... -> BASE_DATA_DIR/face/...
                    rel_path = result_url.replace("/data/results/", "")
                    file_path = os.path.join(BASE_DATA_DIR, rel_path)
                    if os.path.exists(file_path):
                        register_file(session_id, file_path, BASE_DATA_DIR)
                
                # 사용자가 얼굴 결과를 요청한 경우에만 상세 정보 포함
                if show_faces:
                    face_results.append({
                        "image_index": idx + 1,
                        "filename": image_file.filename,
                        "count": face_data["count"],
                        "faces": face_data.get("faces"),
                        "result_image_url": result_url
                    })
                else:
                    # 얼굴 수만 반환
                    face_results.append({
                        "image_index": idx + 1,
                        "filename": image_file.filename,
                        "count": face_data["count"]
                    })
                logger.info(f"얼굴 감지 성공: {face_data['count']}개, 상세 표시: {show_faces}")
            
            # 손가락 검출 (사용자 선택에 따라)
            if blur_fingers and hand_service:
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
                    result_url = hand_data.get("result_image_url")
                    # URL에서 실제 파일 경로 계산하여 세션에 등록
                    if result_url:
                        # /data/results/hand/... -> BASE_DATA_DIR/hand/...
                        rel_path = result_url.replace("/data/results/", "")
                        file_path = os.path.join(BASE_DATA_DIR, rel_path)
                        if os.path.exists(file_path):
                            register_file(session_id, file_path, BASE_DATA_DIR)
                    
                    hand_results.append({
                        "image_index": idx + 1,
                        "filename": image_file.filename,
                        "count": hand_data["count"],
                        "fingers": hand_data.get("fingers"),
                        "result_image_url": result_url
                    })
                    logger.info(f"손가락 감지 성공: {hand_data['count']}개, 이미지 URL: {result_url}")
                else:
                    logger.warning(f"손가락 감지 실패: {hand_data}")
            elif hand_service:
                # 손가락 검출만 수행 (블러 처리 안 함)
                hand_result = hand_service.detect_fingertips(image_file, save_preview=False, return_image=False)
                if isinstance(hand_result, tuple):
                    hand_data, _ = hand_result
                else:
                    hand_data = hand_result
                if hand_data.get("success"):
                    all_finger_count += hand_data["count"]
                    hand_results.append({
                        "image_index": idx + 1,
                        "filename": image_file.filename,
                        "count": hand_data["count"]
                    })
                    logger.info(f"손가락 감지 성공 (블러 없음): {hand_data['count']}개")
            
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
        
        # OCR 텍스트 결과 처리 (마스킹 결과 출력)
        logger.info(f"최종 OCR 텍스트 배열: {all_ocr_text} (개수: {len(all_ocr_text)})")
        
        # OCR 텍스트를 마스킹 처리
        ocr_masked_texts = []
        ocr_structured_data = {
            "detected": False,
            "total_count": 0,
            "categories": {}
        }
        
        if all_ocr_text:
            # OCR 텍스트들을 하나로 합치기
            ocr_combined = "\n".join(all_ocr_text)
            active_filters = [key for key, value in detection_options.items() if value]
            
            # OCR 텍스트 마스킹 처리
            ocr_filter_result = filter_service.filter_text(ocr_combined, use_replacements=True, filters=active_filters)
            ocr_masked = ocr_filter_result.get("filtered_text", ocr_combined)
            
            # 마스킹된 텍스트를 다시 분리 (원래 형식 유지)
            ocr_masked_lines = ocr_masked.split("\n")
            ocr_masked_texts = ocr_masked_lines[:len(all_ocr_text)]
            
            # OCR 텍스트 탐지 결과
            ocr_statistics = ocr_filter_result.get("overall_statistics", {})
            ocr_structured_data = {
                "detected": ocr_statistics.get("total_detected", 0) > 0,
                "total_count": ocr_statistics.get("total_detected", 0),
                "categories": {}
            }
            
            # 필터별 결과를 카테고리로 변환
            for filter_name, result in ocr_filter_result.get("filter_results", {}).items():
                if result.get("success") and result.get("statistics", {}).get("total_detected", 0) > 0:
                    ocr_structured_data["categories"][filter_name] = {
                        "count": result["statistics"]["total_detected"],
                        "items": result["detected_words"]
                    }
        
        results["ocr_text"] = {
            "original_texts": all_ocr_text,
            "masked_texts": ocr_masked_texts,
            "total_count": len(all_ocr_text),
            "message": f"총 {len(all_ocr_text)}개 이미지에서 텍스트가 추출되었습니다" if all_ocr_text else "텍스트를 발견하지 못했습니다",
            "structured_data": ocr_structured_data
        }
    
    # 직접 입력 텍스트 분석 (LLM 수정문장 생성)
    original_text_input = text_input.strip()
    if original_text_input:
        # 활성화된 필터 목록 생성
        active_filters = [key for key, value in detection_options.items() if value]
        logger.info(f"활성화된 탐지 필터: {active_filters}")
        
        # 직접 입력 텍스트 마스킹 (LLM 입력용)
        filter_result = filter_service.filter_text(original_text_input, use_replacements=True, filters=active_filters)
        masked_text = filter_result.get("filtered_text", original_text_input)
        
        # 탐지 결과
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
        
        # LLM으로 수정문장 생성
        llm_revised_text = original_text_input  # 기본값은 원문
        try:
            from app.services.llm_service import LLMService
            llm_service = LLMService()
            if structured_data_result.get("detected", False):
                # 카테고리를 딕셔너리로 변환 (LLM 서비스 형식)
                categories_dict = {cat: True for cat in structured_data_result.get("categories", {}).keys()}
                llm_result = llm_service.suggest(masked_text, categories_dict, language="ko", tone="educational")
                llm_revised_text = llm_result.get("revised_sentence", original_text_input)
                logger.info(f"LLM 수정문장 생성 완료: {len(llm_revised_text)}자")
            else:
                llm_revised_text = original_text_input
                logger.info("민감 정보 미탐지, LLM 수정문장 생성 생략")
        except Exception as e:
            logger.warning(f"LLM 수정문장 생성 실패: {e}, 원문 사용")
            llm_revised_text = original_text_input
        
        results["text_analysis"] = {
            "original_text": original_text_input,
            "revised_text": llm_revised_text,  # LLM 수정문장
            "masked_text": masked_text,  # 마스킹 결과 (참고용)
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
            "revised_text": "",
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
    logger.info(f"통합 분석 완료: {total_detected}개 민감 정보 감지, 세션 ID: {session_id}")
    
    # 응답에 session_id 포함 (프론트엔드에서 세션 종료 시 사용)
    results["session_id"] = session_id
    
    # 보안: 원본 파일 데이터 메모리에서 정리
    # 이미 처리된 파일들은 메모리에서 제거됨
    # 참고: Flask의 FileStorage는 요청 완료 후 자동으로 정리되지만, 명시적으로 처리
    import gc
    
    # 보안: 민감한 텍스트 데이터 메모리 정리
    if text_input:
        text_input = ""  # 참조 제거
    
    # 보안: 파일 객체 참조 제거
    for img_file in valid_images:
        if hasattr(img_file, 'close'):
            try:
                img_file.close()
            except:
                pass
    
    gc.collect()  # 가비지 컬렉션 강제 실행
    
    return APIResponse.success({"data": results}, results["summary"]["message"])


@integrated_analysis_bp.route('/cleanup', methods=['POST'])
def cleanup_session():
    """세션의 모든 파일 삭제"""
    try:
        session_id = request.json.get('session_id') or request.headers.get('X-Session-ID')
        if not session_id:
            return APIResponse.error("session_id가 필요합니다", code=400)
        
        deleted_count = cleanup_session_files(session_id, BASE_DATA_DIR)
        return APIResponse.success(
            {"deleted_count": deleted_count},
            message=f"{deleted_count}개의 파일이 삭제되었습니다"
        )
    except Exception as e:
        logger.error(f"세션 파일 정리 오류: {e}", exc_info=True)
        return APIResponse.error("파일 정리 중 오류가 발생했습니다", code=500)


@integrated_analysis_bp.route('/download/<path:filename>', methods=['GET'])
def download_file(filename):
    """파일 다운로드 후 삭제"""
    from flask import send_from_directory, request
    
    try:
        # 파일 경로 계산
        rel_path = filename
        file_path = os.path.join(BASE_DATA_DIR, rel_path)
        
        # 보안: 경로 검증
        abs_path = os.path.abspath(file_path)
        base_abs = os.path.abspath(BASE_DATA_DIR)
        if not abs_path.startswith(base_abs):
            logger.warning(f"경로 조작 시도: {filename}")
            return APIResponse.error("잘못된 파일 경로입니다", code=403)
        
        if not os.path.exists(abs_path):
            return APIResponse.error("파일을 찾을 수 없습니다", code=404)
        
        # 파일 다운로드
        directory = os.path.dirname(abs_path)
        file_name = os.path.basename(abs_path)
        response = send_from_directory(directory, file_name, as_attachment=True)
        
        # 다운로드 후 파일 삭제 (백그라운드에서)
        session_id = request.args.get('session_id') or request.headers.get('X-Session-ID')
        if session_id:
            # 다운로드 완료 후 삭제 (약간의 지연)
            import threading
            def delayed_delete():
                import time
                time.sleep(2)  # 다운로드 완료 대기
                cleanup_file(abs_path, BASE_DATA_DIR)
            
            thread = threading.Thread(target=delayed_delete, daemon=True)
            thread.start()
        else:
            # 세션 ID가 없으면 바로 삭제
            cleanup_file(abs_path, BASE_DATA_DIR)
        
        return response
    except Exception as e:
        logger.error(f"파일 다운로드 오류: {e}", exc_info=True)
        return APIResponse.error("파일 다운로드 중 오류가 발생했습니다", code=500)
