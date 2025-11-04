import os
from datetime import datetime
import uuid
import json
from pathlib import Path

def ensure_dir(path: str) -> None:
    """디렉토리가 없으면 생성 (보안: 경로 검증)"""
    # 경로 조작 방지
    abs_path = os.path.abspath(path)
    if not abs_path.startswith(os.path.abspath(os.getcwd())):
        raise ValueError("안전하지 않은 디렉토리 경로입니다")
    os.makedirs(path, exist_ok=True)

def timestamped_filename(prefix: str, ext: str = ".jpg") -> str:
    """타임스탬프+랜덤 uuid 기반 파일명 (보안: 안전한 파일명)"""
    # 파일명 접두사 검증 (안전하지 않은 문자 제거)
    safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-'))[:20]
    if not safe_prefix:
        safe_prefix = "file"
    
    # 확장자 검증
    safe_ext = Path(ext).suffix or ".jpg"
    if not safe_ext.startswith('.'):
        safe_ext = '.' + safe_ext
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]  # 더 긴 UUID로 충돌 방지
    return f"{safe_prefix}_{ts}_{uid}{safe_ext}"

def save_path_with_timestamp(base_dir: str, prefix: str, ext: str = ".jpg") -> str:
    """저장 절대경로 반환 (보안: 경로 검증)"""
    ensure_dir(base_dir)
    filename = timestamped_filename(prefix, ext)
    # 경로 조작 방지
    safe_path = os.path.join(base_dir, filename)
    abs_path = os.path.abspath(safe_path)
    base_abs = os.path.abspath(base_dir)
    if not abs_path.startswith(base_abs):
        raise ValueError("경로 조작 시도가 감지되었습니다")
    return abs_path

def to_public_url(data_relative_path: str) -> str:
    """/data/... 형태 웹 경로 반환"""
    data_relative_path = data_relative_path.replace("\\", "/")
    if not data_relative_path.startswith("/"):
        data_relative_path = "/" + data_relative_path
    return data_relative_path

def save_json_with_timestamp(base_dir: str, data: dict, prefix: str = "result", ext: str = ".json") -> dict:
    """JSON 저장 + 경로/URL 반환"""
    ensure_dir(base_dir)
    abs_path = os.path.join(base_dir, timestamped_filename(prefix, ext))
    with open(abs_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    url = None
    norm = abs_path.replace("\\", "/")
    if "/data/results/" in norm:
        # data/results 디렉토리 내 파일인 경우 URL 생성
        # BASE_DATA_DIR은 backend/data/results이므로, URL은 /data/results/... 형태
        rel_path = norm.split("/data/results/", 1)[-1]
        url = to_public_url("data/results/" + rel_path)
    return {"path": abs_path, "url": url}
