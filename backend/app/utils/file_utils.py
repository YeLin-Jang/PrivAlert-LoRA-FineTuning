import os
from datetime import datetime
import uuid
import json

def ensure_dir(path: str) -> None:
    """디렉토리가 없으면 생성"""
    os.makedirs(path, exist_ok=True)

def timestamped_filename(prefix: str, ext: str = ".jpg") -> str:
    """타임스탬프+랜덤 uuid 기반 파일명"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]
    return f"{prefix}_{ts}_{uid}{ext}"

def save_path_with_timestamp(base_dir: str, prefix: str, ext: str = ".jpg") -> str:
    """저장 절대경로 반환"""
    ensure_dir(base_dir)
    return os.path.join(base_dir, timestamped_filename(prefix, ext))

def to_public_url(static_relative_path: str) -> str:
    """/static/... 형태 웹 경로 반환"""
    static_relative_path = static_relative_path.replace("\\", "/")
    if not static_relative_path.startswith("/"):
        static_relative_path = "/" + static_relative_path
    return static_relative_path

def save_json_with_timestamp(base_dir: str, data: dict, prefix: str = "result", ext: str = ".json") -> dict:
    """JSON 저장 + 경로/URL 반환"""
    ensure_dir(base_dir)
    abs_path = os.path.join(base_dir, timestamped_filename(prefix, ext))
    with open(abs_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    url = None
    norm = abs_path.replace("\\", "/")
    if "/static/" in norm or norm.endswith("/static"):
        rel_path = norm.split("/static", 1)[-1]
        url = to_public_url("static" + rel_path)
    return {"path": abs_path, "url": url}
