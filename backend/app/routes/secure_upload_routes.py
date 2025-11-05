"""
안전한 파일 업로드/다운로드/관리 API
보안: Path Traversal, IDOR, 예측 가능한 세션 ID 방지
"""
import os
import logging
from typing import Optional
from flask import Blueprint, request, jsonify, send_file, abort
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from app.utils.logger import get_logger
from app.utils.secure_storage import (
    generate_session_id, save_file, get_file_path,
    delete_file_atomic, delete_session, list_session_files,
    ALLOWED_EXTENSIONS, MAX_FILE_SIZE
)
from app.utils.api_utils import APIResponse
from app.utils.admin_decorators import admin_required

logger = get_logger(__name__)

secure_upload_bp = Blueprint('secure_upload', __name__)


# 세션 소유자 매핑 (실제로는 DB에 저장해야 함)
# {session_id: user_id}
_session_owners: dict = {}


def get_session_owner(session_id: str) -> Optional[str]:
    """세션 소유자 조회"""
    return _session_owners.get(session_id)


def set_session_owner(session_id: str, user_id: str):
    """세션 소유자 설정"""
    _session_owners[session_id] = user_id


def verify_session_ownership(session_id: str, user_id: str) -> bool:
    """
    세션 소유권 검증 (IDOR 방지)
    보안: 사용자가 자신의 세션에만 접근 가능하도록 검증
    """
    owner = get_session_owner(session_id)
    if owner is None:
        # 세션이 없으면 생성 가능 (새 세션)
        return True
    return owner == user_id


@secure_upload_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """
    파일 업로드
    보안: JWT 인증, 파일 크기/형식 검증, EXIF 제거, 서버 생성 세션 ID
    """
    try:
        # JWT에서 사용자 ID 추출
        user_id = str(get_jwt_identity())
        
        # 파일 검증
        if 'file' not in request.files:
            return APIResponse.error("파일이 필요합니다", code=400)
        
        file = request.files['file']
        if not file or file.filename == '':
            return APIResponse.error("파일이 비어있습니다", code=400)
        
        # 보안: 파일명 검증
        original_filename = file.filename or 'unnamed'
        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            return APIResponse.error(
                f"허용되지 않은 파일 형식입니다. 허용 형식: {', '.join(ALLOWED_EXTENSIONS)}",
                code=400
            )
        
        # 파일 읽기
        file_content = file.read()
        
        # 보안: 파일 크기 검증
        if len(file_content) > MAX_FILE_SIZE:
            return APIResponse.error(
                f"파일 크기가 최대 허용 크기({MAX_FILE_SIZE // 1024 // 1024}MB)를 초과합니다",
                code=400
            )
        
        # 보안: 서버 생성 세션 ID (예측 불가능)
        session_id = generate_session_id()
        
        # 파일 저장 (EXIF 제거 포함)
        result = save_file(file_content, session_id, original_filename)
        
        # 세션 소유자 설정
        set_session_owner(session_id, user_id)
        
        # 보안: 로그에 민감 정보 제외 (파일 경로, 원본 파일명 제외)
        logger.info(f"파일 업로드 성공: user_id={user_id}, session_id={session_id[:8]}...")
        
        return APIResponse.success({
            "session_id": session_id,
            "filename": result["filename"],
            "message": "파일이 업로드되었습니다"
        }, "업로드 성공")
        
    except ValueError as e:
        logger.warning(f"파일 업로드 검증 실패: {e}")
        return APIResponse.error(str(e), code=400)
    except Exception as e:
        logger.error(f"파일 업로드 오류: {e}", exc_info=True)
        return APIResponse.error("파일 업로드 중 오류가 발생했습니다", code=500)


@secure_upload_bp.route('/download/image/<session_id>/<filename>', methods=['GET'])
@jwt_required()
def download_file(session_id: str, filename: str):
    """
    파일 다운로드 (다운로드 후 즉시 삭제)
    보안: IDOR 방지, Path Traversal 방지, 다운로드 후 원자적 삭제
    """
    try:
        # JWT에서 사용자 ID 추출
        user_id = str(get_jwt_identity())
        
        # 보안: 세션 소유권 검증 (IDOR 방지)
        if not verify_session_ownership(session_id, user_id):
            logger.warning(f"세션 소유권 검증 실패: user_id={user_id}, session_id={session_id[:8]}...")
            return APIResponse.error("해당 파일에 접근할 권한이 없습니다", code=403)
        
        # 파일 경로 가져오기 (경로 검증 포함)
        try:
            file_path = get_file_path(session_id, filename)
        except ValueError as e:
            logger.warning(f"경로 검증 실패: {e}")
            return APIResponse.error("잘못된 파일 경로입니다", code=403)
        
        if not file_path or not os.path.exists(file_path):
            return APIResponse.error("파일을 찾을 수 없습니다", code=404)
        
        # 보안: 파일 다운로드 (원자적 처리)
        # 파일을 임시 복사본으로 읽어서 전송 (race condition 방지)
        try:
            # 임시 복사본 생성
            import tempfile
            import shutil
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
                shutil.copy2(file_path, temp_path)
            
            # 파일 전송
            directory = os.path.dirname(temp_path)
            file_name = os.path.basename(temp_path)
            
            def after_response(response):
                """응답 전송 후 파일 삭제"""
                try:
                    # 임시 파일 삭제
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    
                    # 원본 파일 삭제 (원자적)
                    delete_file_atomic(file_path)
                except Exception as e:
                    logger.error(f"파일 삭제 오류: {e}")
            
            # 응답 생성
            response = send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='image/jpeg'
            )
            
            # 응답 후 삭제 (하지만 Flask의 after_request는 클라이언트 응답 후 실행)
            # 더 안전한 방법: 다운로드 완료 후 별도 스레드로 삭제
            import threading
            def delayed_delete():
                import time
                time.sleep(1)  # 다운로드 시작 대기
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    delete_file_atomic(file_path)
                except Exception as e:
                    logger.error(f"지연 삭제 오류: {e}")
            
            thread = threading.Thread(target=delayed_delete, daemon=True)
            thread.start()
            
            logger.info(f"파일 다운로드 시작: session_id={session_id[:8]}..., filename={filename[:8]}...")
            return response
            
        except Exception as e:
            logger.error(f"파일 다운로드 오류: {e}", exc_info=True)
            # 오류 발생 시에도 원본 파일 삭제 시도
            delete_file_atomic(file_path)
            return APIResponse.error("파일 다운로드 중 오류가 발생했습니다", code=500)
            
    except Exception as e:
        logger.error(f"다운로드 처리 오류: {e}", exc_info=True)
        return APIResponse.error("파일 다운로드 중 오류가 발생했습니다", code=500)


@secure_upload_bp.route('/cleanup', methods=['POST'])
@jwt_required()
def cleanup_session():
    """
    세션 파일 정리
    보안: 본인 세션만 삭제 가능 (IDOR 방지)
    """
    try:
        user_id = str(get_jwt_identity())
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        # 보안: 세션 ID가 없으면 본인 세션만 정리
        if not session_id:
            # 사용자의 모든 세션 찾기
            user_sessions = [sid for sid, owner in _session_owners.items() if owner == user_id]
            deleted_count = 0
            for sid in user_sessions:
                deleted_count += delete_session(sid)
                _session_owners.pop(sid, None)
            
            logger.info(f"사용자 세션 정리 완료: user_id={user_id}, sessions={len(user_sessions)}, files={deleted_count}")
            return APIResponse.success(
                {"deleted_sessions": len(user_sessions), "deleted_files": deleted_count},
                "세션 정리 완료"
            )
        
        # 보안: 세션 소유권 검증 (IDOR 방지)
        if not verify_session_ownership(session_id, user_id):
            logger.warning(f"세션 소유권 검증 실패: user_id={user_id}, session_id={session_id[:8]}...")
            return APIResponse.error("해당 세션에 접근할 권한이 없습니다", code=403)
        
        # 세션 삭제
        deleted_count = delete_session(session_id)
        _session_owners.pop(session_id, None)
        
        logger.info(f"세션 정리 완료: session_id={session_id[:8]}..., files={deleted_count}")
        return APIResponse.success(
            {"deleted_files": deleted_count},
            "세션 정리 완료"
        )
        
    except Exception as e:
        logger.error(f"세션 정리 오류: {e}", exc_info=True)
        return APIResponse.error("세션 정리 중 오류가 발생했습니다", code=500)


@secure_upload_bp.route('/cleanup/all', methods=['POST'])
@jwt_required()
@admin_required
def cleanup_all_sessions():
    """
    모든 세션 정리 (관리자 전용)
    보안: 관리자 권한만 허용
    """
    try:
        import glob
        from app.utils.secure_storage import STORAGE_ROOT
        
        total_deleted = 0
        session_count = 0
        
        # 모든 세션 디렉토리 스캔
        for session_dir in glob.glob(os.path.join(STORAGE_ROOT, '*')):
            if os.path.isdir(session_dir):
                session_id = os.path.basename(session_dir)
                deleted = delete_session(session_id)
                if deleted > 0:
                    total_deleted += deleted
                    session_count += 1
                    _session_owners.pop(session_id, None)
        
        logger.info(f"전체 세션 정리 완료: sessions={session_count}, files={total_deleted}")
        return APIResponse.success(
            {"deleted_sessions": session_count, "deleted_files": total_deleted},
            "전체 세션 정리 완료"
        )
        
    except Exception as e:
        logger.error(f"전체 세션 정리 오류: {e}", exc_info=True)
        return APIResponse.error("세션 정리 중 오류가 발생했습니다", code=500)


@secure_upload_bp.route('/sessions/<session_id>/files', methods=['GET'])
@jwt_required()
def list_files(session_id: str):
    """
    세션의 파일 목록 조회
    보안: 본인 세션만 조회 가능 (IDOR 방지)
    """
    try:
        user_id = str(get_jwt_identity())
        
        # 보안: 세션 소유권 검증
        if not verify_session_ownership(session_id, user_id):
            return APIResponse.error("해당 세션에 접근할 권한이 없습니다", code=403)
        
        files = list_session_files(session_id)
        
        return APIResponse.success({"files": files}, "파일 목록 조회 성공")
        
    except Exception as e:
        logger.error(f"파일 목록 조회 오류: {e}", exc_info=True)
        return APIResponse.error("파일 목록 조회 중 오류가 발생했습니다", code=500)

