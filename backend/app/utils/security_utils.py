"""
보안 유틸리티 모듈
시큐어 코딩 가이드 준수
"""

import os
import re
import logging
from pathlib import Path
from typing import Tuple, Optional, List
from werkzeug.datastructures import FileStorage

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """보안 관련 예외"""
    pass


# 허용된 이미지 확장자 (화이트리스트)
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif'}

# 허용된 비디오 확장자
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}

# 최대 파일 크기 제한
MAX_IMAGE_SIZE = 20 * 1024 * 1024  # 20MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB

# 최대 텍스트 길이
MAX_TEXT_LENGTH = 3000  # 3,000자

# 안전하지 않은 파일명 문자 패턴
UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def validate_image_file(file: FileStorage) -> Tuple[bool, Optional[str]]:
    """
    이미지 파일 검증 (보안)
    
    시큐어 코딩 가이드 준수:
    - 파일 확장자 화이트리스트 검증
    - 파일 크기 제한 (DoS 공격 방지)
    - 경로 조작 방지 (Path 사용)
    - 파일명 검증
    
    Args:
        file: 업로드된 파일
        
    Returns:
        (유효성, 오류 메시지)
    """
    if not file or not file.filename:
        return False, "파일이 제공되지 않았습니다"
    
    # 파일명 검증 (경로 조작 방지)
    filename = Path(file.filename).name  # 경로 분리, 파일명만 추출
    
    # 안전하지 않은 문자 검사
    if UNSAFE_FILENAME_CHARS.search(filename):
        return False, "파일명에 허용되지 않은 문자가 포함되어 있습니다"
    
    # 파일 확장자 검증 (화이트리스트)
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, f"지원하지 않는 이미지 형식입니다. 허용된 형식: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
    
    # 파일 크기 검증 (DoS 공격 방지)
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # 파일 포인터 초기화
    
    if file_size == 0:
        return False, "빈 파일입니다"
    
    if file_size > MAX_IMAGE_SIZE:
        return False, f"파일 크기가 너무 큽니다. 최대 크기: {MAX_IMAGE_SIZE / (1024*1024):.0f}MB"
    
    return True, None


def validate_video_file(file: FileStorage) -> Tuple[bool, Optional[str]]:
    """
    비디오 파일 검증 (보안)
    
    Args:
        file: 업로드된 파일
        
    Returns:
        (유효성, 오류 메시지)
    """
    if not file or not file.filename:
        return False, "파일이 제공되지 않았습니다"
    
    # 파일명 검증
    filename = Path(file.filename).name
    
    if UNSAFE_FILENAME_CHARS.search(filename):
        return False, "파일명에 허용되지 않은 문자가 포함되어 있습니다"
    
    # 파일 확장자 검증
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_VIDEO_EXTENSIONS:
        return False, f"지원하지 않는 비디오 형식입니다. 허용된 형식: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
    
    # 파일 크기 검증
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    
    if file_size == 0:
        return False, "빈 파일입니다"
    
    if file_size > MAX_VIDEO_SIZE:
        return False, f"파일 크기가 너무 큽니다. 최대 크기: {MAX_VIDEO_SIZE / (1024*1024):.0f}MB"
    
    return True, None


def validate_text_input(text: str, max_length: int = MAX_TEXT_LENGTH) -> Tuple[bool, Optional[str]]:
    """
    텍스트 입력 검증
    
    Args:
        text: 검증할 텍스트
        max_length: 최대 길이
        
    Returns:
        (유효성, 오류 메시지)
    """
    if not isinstance(text, str):
        return False, "텍스트는 문자열이어야 합니다"
    
    if len(text) > max_length:
        return False, f"텍스트가 너무 깁니다 (최대 {max_length:,}자)"
    
    # 제어 문자 검사 (일부 제어 문자는 허용)
    # NULL 문자는 허용하지 않음
    if '\x00' in text:
        return False, "텍스트에 허용되지 않은 문자가 포함되어 있습니다"
    
    return True, None


def sanitize_filename(filename: str) -> str:
    """
    파일명 정제 (경로 조작 방지)
    
    Args:
        filename: 원본 파일명
        
    Returns:
        정제된 파일명
    """
    # 경로 분리하여 파일명만 추출
    safe_name = Path(filename).name
    
    # 안전하지 않은 문자 제거
    safe_name = UNSAFE_FILENAME_CHARS.sub('_', safe_name)
    
    # 빈 파일명 방지
    if not safe_name or safe_name == '.' or safe_name == '..':
        safe_name = 'file'
    
    # 길이 제한 (파일 시스템 제한 고려)
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:255-len(ext)] + ext
    
    return safe_name


def validate_path(base_dir: str, filepath: str) -> Tuple[bool, Optional[str]]:
    """
    파일 경로 검증 (경로 조작 방지)
    
    Args:
        base_dir: 기본 디렉토리
        filepath: 검증할 경로
        
    Returns:
        (유효성, 오류 메시지)
    """
    try:
        # 절대 경로로 변환
        base_abs = os.path.abspath(base_dir)
        path_abs = os.path.abspath(os.path.join(base_dir, filepath))
        
        # 경로 조작 방지: base_dir 밖으로 나가는지 확인
        if not path_abs.startswith(base_abs):
            return False, "경로 조작 시도가 감지되었습니다"
        
        return True, None
    except Exception as e:
        logger.error(f"경로 검증 중 오류: {e}")
        return False, "경로 검증 실패"


def mask_sensitive_data_in_log(text: str) -> str:
    """
    로그에 기록할 텍스트에서 민감 정보 마스킹
    
    Args:
        text: 원본 텍스트
        
    Returns:
        마스킹된 텍스트
    """
    if not text:
        return text
    
    # 전화번호 마스킹
    text = re.sub(r'\d{3}-\d{4}-\d{4}', '***-****-****', text)
    text = re.sub(r'\d{3}-\d{3}-\d{4}', '***-***-****', text)
    
    # 이메일 마스킹 (도메인 제외)
    text = re.sub(r'([a-zA-Z0-9._%+-]+)@', '***@', text)
    
    # 주민등록번호 마스킹
    text = re.sub(r'\d{6}-\d{7}', '******-*******', text)
    
    # 계좌번호 마스킹
    text = re.sub(r'\d{10,16}', lambda m: '*' * len(m.group()) if len(m.group()) >= 10 else m.group(), text)
    
    return text


def validate_file_list(files: List[FileStorage], max_files: int = 5) -> Tuple[bool, Optional[str]]:
    """
    파일 리스트 검증
    
    Args:
        files: 파일 리스트
        max_files: 최대 파일 수
        
    Returns:
        (유효성, 오류 메시지)
    """
    if not files:
        return False, "파일이 제공되지 않았습니다"
    
    if len(files) > max_files:
        return False, f"파일 수가 너무 많습니다 (최대 {max_files}개)"
    
    # 각 파일 검증
    for file in files:
        if not file or not file.filename:
            continue  # 빈 파일은 건너뛰기
        
        is_valid, error = validate_image_file(file)
        if not is_valid:
            return False, error
    
    return True, None


def get_safe_file_path(base_dir: str, filename: str, prefix: str = "file") -> str:
    """
    안전한 파일 경로 생성
    
    Args:
        base_dir: 기본 디렉토리
        filename: 원본 파일명
        prefix: 파일명 접두사
        
    Returns:
        안전한 파일 경로
    """
    # 파일명 정제
    safe_name = sanitize_filename(filename)
    
    # 타임스탬프와 UUID 추가하여 중복 방지
    from datetime import datetime
    import uuid
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:8]
    
    # 확장자 추출
    ext = Path(safe_name).suffix or '.bin'
    
    # 안전한 파일명 생성
    safe_filename = f"{prefix}_{timestamp}_{unique_id}{ext}"
    
    # 경로 검증
    is_valid, error = validate_path(base_dir, safe_filename)
    if not is_valid:
        raise SecurityError(f"안전하지 않은 파일 경로: {error}")
    
    return os.path.join(base_dir, safe_filename)

