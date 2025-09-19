import os
from app.utils.image_sanitize import sanitize_image

def sanitize_and_replace(file_path: str, keep_icc: bool = True, target_format: str | None = None):
    """
    파일을 sanitize 후 원본 삭제 + 클린 파일 저장
    """
    with open(file_path, "rb") as f:
        raw = f.read()

    data, ext, report = sanitize_image(raw, keep_icc=keep_icc, target_format=target_format)

    dir_name, base_name = os.path.split(file_path)
    name, _ = os.path.splitext(base_name)
    new_path = os.path.join(dir_name, f"{name}_cleaned.{ext}")

    with open(new_path, "wb") as f:
        f.write(data)

    os.remove(file_path)
    return {"new_path": new_path, "report": report}
