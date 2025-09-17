import os
from datetime import datetime
import uuid

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def timestamped_filename(prefix: str, ext: str = ".jpg") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]
    return f"{prefix}_{ts}_{uid}{ext}"

def save_path_with_timestamp(base_dir: str, prefix: str, ext: str = ".jpg") -> str:
    """
    저장 절대경로를 만들어 반환 (디렉토리 생성 포함)
    반환값은 서버 내부 경로 (예: app/static/results/face_20250917_120000_ab12cd.jpg)
    """
    ensure_dir(base_dir)
    return os.path.join(base_dir, timestamped_filename(prefix, ext))

def to_public_url(static_relative_path: str) -> str:
    """
    /static/... 상대 경로로 변환 (routes에서 host_url 붙여 절대 URL로 변경하면 됨)
    """
    if not static_relative_path.startswith("/"):
        static_relative_path = "/" + static_relative_path
    return static_relative_path
