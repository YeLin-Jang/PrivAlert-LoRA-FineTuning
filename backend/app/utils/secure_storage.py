"""
안전한 파일 저장 유틸리티
보안: Path Traversal, IDOR, 예측 가능한 세션 ID 방지
"""
import os
import secrets
import hashlib
import shutil
from pathlib import Path
from typing import Tuple, Optional, Dict
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 허용된 파일 확장자 (화이트리스트)
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}

# 최대 파일 크기 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# 파일 저장 루트 디렉토리
STORAGE_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "sessions")


def ensure_storage_root():
    """저장소 루트 디렉토리 생성 및 권한 설정"""
    os.makedirs(STORAGE_ROOT, mode=0o700, exist_ok=True)
    # 보안: 디렉토리 권한 최소화
    os.chmod(STORAGE_ROOT, 0o700)


def generate_session_id() -> str:
    """
    서버 생성 세션 ID (예측 불가능한 난수)
    보안: UUID4나 secrets.token_hex 사용으로 예측 불가능
    """
    return secrets.token_hex(16)  # 32자 hex 문자열


def generate_safe_filename(original_filename: str, session_id: str) -> Tuple[str, str]:
    """
    안전한 파일명 생성
    보안: 원본 파일명 사용 금지, 해시 기반 무작위 파일명 생성
    
    Args:
        original_filename: 원본 파일명
        session_id: 세션 ID
    
    Returns:
        (safe_filename, extension)
    """
    # 확장자 추출 및 검증
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"허용되지 않은 파일 확장자: {ext}")
    
    # 보안: 무작위 토큰 + 원본 파일명 해시로 안전한 파일명 생성
    # 공격자가 파일명을 예측할 수 없도록 함
    random_token = secrets.token_bytes(16)
    name_hash = hashlib.sha256(random_token + original_filename.encode('utf-8')).hexdigest()
    safe_filename = f"{name_hash[:32]}{ext}"
    
    return safe_filename, ext


def validate_path(path: str, base_dir: str) -> Tuple[bool, Optional[str]]:
    """
    경로 검증 (Path Traversal 방지)
    보안: os.path.realpath와 os.path.commonpath로 경로 조작 방지
    
    Args:
        path: 검증할 경로
        base_dir: 기준 디렉토리
    
    Returns:
        (is_valid, error_message)
    """
    try:
        # 보안: 상대 경로를 절대 경로로 변환하여 조작 방지
        real_path = os.path.realpath(path)
        real_base = os.path.realpath(base_dir)
        
        # 보안: 경로가 base_dir 내부에 있는지 확인
        # commonpath는 두 경로의 공통 상위 경로를 반환
        # 공통 경로가 base_dir과 일치하면 안전
        common = os.path.commonpath([real_path, real_base])
        if common != real_base:
            logger.warning(f"Path Traversal 시도 감지: {path}")
            return False, "경로 조작 시도가 감지되었습니다"
        
        return True, None
    except (ValueError, OSError) as e:
        logger.error(f"경로 검증 오류: {e}")
        return False, "경로 검증 실패"


def get_session_dir(session_id: str) -> str:
    """
    세션 디렉토리 경로 반환 (생성 및 검증)
    보안: 경로 검증 및 권한 설정
    """
    ensure_storage_root()
    
    session_dir = os.path.join(STORAGE_ROOT, session_id)
    
    # 보안: 경로 검증
    is_valid, error = validate_path(session_dir, STORAGE_ROOT)
    if not is_valid:
        raise ValueError(error or "안전하지 않은 세션 경로")
    
    # 세션 디렉토리 생성 및 권한 설정
    os.makedirs(session_dir, mode=0o700, exist_ok=True)
    os.chmod(session_dir, 0o700)
    
    return session_dir


def save_file(file_content: bytes, session_id: str, original_filename: str) -> Dict[str, str]:
    """
    파일 저장 (EXIF 제거 포함)
    보안: 안전한 파일명, 권한 설정, 경로 검증
    
    Args:
        file_content: 파일 내용 (바이트)
        session_id: 세션 ID
        original_filename: 원본 파일명
    
    Returns:
        {"session_id": "...", "filename": "...", "path": "..."}
    """
    # 보안: 파일 크기 검증
    if len(file_content) > MAX_FILE_SIZE:
        raise ValueError(f"파일 크기가 최대 허용 크기({MAX_FILE_SIZE} bytes)를 초과합니다")
    
    # 안전한 파일명 생성
    safe_filename, ext = generate_safe_filename(original_filename, session_id)
    
    # 세션 디렉토리 가져오기
    session_dir = get_session_dir(session_id)
    
    # 파일 경로 생성 및 검증
    file_path = os.path.join(session_dir, safe_filename)
    is_valid, error = validate_path(file_path, STORAGE_ROOT)
    if not is_valid:
        raise ValueError(error or "안전하지 않은 파일 경로")
    
    # 보안: EXIF 제거 및 파일 저장
    from app.utils.image_sanitize import sanitize_image
    try:
        sanitized_data, _, _ = sanitize_image(file_content, keep_icc=False, target_format=None)
        file_content = sanitized_data
    except Exception as e:
        logger.warning(f"EXIF 제거 실패, 원본 저장: {e}")
        # EXIF 제거 실패해도 파일은 저장 (하지만 경고)
    
    # 파일 저장
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    # 보안: 파일 권한 최소화 (소유자만 읽기/쓰기)
    os.chmod(file_path, 0o600)
    
    logger.info(f"파일 저장 완료: session_id={session_id[:8]}..., filename={safe_filename[:8]}...")
    
    return {
        "session_id": session_id,
        "filename": safe_filename,
        "path": file_path
    }


def get_file_path(session_id: str, filename: str) -> Optional[str]:
    """
    파일 경로 반환 (경로 검증 포함)
    보안: Path Traversal 방지, 세션 ID 검증
    """
    # 보안: 세션 ID 형식 검증 (32자 hex)
    if not session_id or len(session_id) != 32 or not all(c in '0123456789abcdef' for c in session_id):
        raise ValueError("유효하지 않은 세션 ID")
    
    # 보안: 파일명 검증 (확장자 포함)
    if not filename or not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise ValueError("유효하지 않은 파일명")
    
    # 세션 디렉토리 경로
    session_dir = get_session_dir(session_id)
    file_path = os.path.join(session_dir, filename)
    
    # 보안: 경로 검증
    is_valid, error = validate_path(file_path, STORAGE_ROOT)
    if not is_valid:
        raise ValueError(error or "경로 조작 시도")
    
    # 파일 존재 확인
    if not os.path.exists(file_path):
        return None
    
    return file_path


def delete_file_atomic(file_path: str) -> bool:
    """
    원자적 파일 삭제 (race condition 방지)
    보안: 파일 이동 -> 삭제 패턴으로 race condition 방지
    
    Args:
        file_path: 삭제할 파일 경로
    
    Returns:
        삭제 성공 여부
    """
    try:
        # 보안: 경로 검증
        is_valid, error = validate_path(file_path, STORAGE_ROOT)
        if not is_valid:
            logger.warning(f"안전하지 않은 파일 경로 삭제 시도: {error}")
            return False
        
        if not os.path.exists(file_path):
            return True  # 이미 삭제됨
        
        # 보안: 원자적 삭제 패턴
        # 1. 임시 이름으로 변경 (다운로드 중인 파일과 충돌 방지)
        temp_path = file_path + ".deleting"
        try:
            os.rename(file_path, temp_path)
        except OSError:
            # 파일이 사용 중일 수 있음 (다운로드 중)
            return False
        
        # 2. 실제 삭제
        try:
            os.remove(temp_path)
            logger.info(f"파일 삭제 완료: {os.path.basename(file_path)[:8]}...")
            return True
        except OSError as e:
            logger.error(f"파일 삭제 실패: {e}")
            # 임시 파일 복구 시도
            try:
                os.rename(temp_path, file_path)
            except:
                pass
            return False
            
    except Exception as e:
        logger.error(f"파일 삭제 오류: {e}")
        return False


def delete_session(session_id: str) -> int:
    """
    세션 디렉토리 전체 삭제
    보안: 경로 검증 후 삭제
    
    Returns:
        삭제된 파일 개수
    """
    try:
        session_dir = get_session_dir(session_id)
        
        # 보안: 경로 검증 (이중 확인)
        is_valid, error = validate_path(session_dir, STORAGE_ROOT)
        if not is_valid:
            logger.warning(f"안전하지 않은 세션 경로 삭제 시도: {error}")
            return 0
        
        if not os.path.exists(session_dir):
            return 0
        
        # 파일 개수 계산
        file_count = len([f for f in os.listdir(session_dir) if os.path.isfile(os.path.join(session_dir, f))])
        
        # 세션 디렉토리 삭제
        shutil.rmtree(session_dir)
        
        logger.info(f"세션 삭제 완료: session_id={session_id[:8]}..., files={file_count}")
        return file_count
        
    except Exception as e:
        logger.error(f"세션 삭제 오류: {e}")
        return 0


def list_session_files(session_id: str) -> list:
    """
    세션의 파일 목록 반환
    보안: 경로 검증, 민감 정보 제외
    """
    try:
        session_dir = get_session_dir(session_id)
        is_valid, error = validate_path(session_dir, STORAGE_ROOT)
        if not is_valid:
            return []
        
        if not os.path.exists(session_dir):
            return []
        
        files = []
        for filename in os.listdir(session_dir):
            file_path = os.path.join(session_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
                })
        
        return files
    except Exception as e:
        logger.error(f"파일 목록 조회 오류: {e}")
        return []

