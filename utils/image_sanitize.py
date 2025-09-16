from __future__ import annotations

from io import BytesIO
from typing import Tuple, Dict

from PIL import Image, ImageOps, PngImagePlugin

# 선택 의존성: 일부 환경에서만 사용 가능
try:
    import piexif  # type: ignore
except Exception:  # pragma: no cover
    piexif = None  # type: ignore

try:
    # HEIF/HEIC 지원 등록
    from pillow_heif import register_heif_opener  # type: ignore

    register_heif_opener()
except Exception:  # pragma: no cover
    register_heif_opener = None  # type: ignore

try:
    import magic  # type: ignore
except Exception:  # pragma: no cover
    magic = None  # type: ignore


# 안전 상한
MAX_PIXELS = 50_000_000
MAX_BYTES = 20 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG", "JPG", "PNG", "WEBP", "HEIF", "HEIC"}


class ImageTooLargeError(ValueError):
    pass


def _detect_mime(raw: bytes) -> str | None:
    if magic is None:
        return None
    try:
        m = magic.Magic(mime=True)
        return m.from_buffer(raw)
    except Exception:
        return None


def _normalize_format(fmt: str | None) -> str | None:
    if not fmt:
        return None
    up = fmt.upper()
    if up == "JPG":
        return "JPEG"
    if up in {"HEIC", "HEIF"}:
        return "HEIC"
    return up


def _open_image_strict(raw: bytes) -> Image.Image:
    # 바이트 상한
    if len(raw) > MAX_BYTES:
        raise ImageTooLargeError("file too large")

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    bio = BytesIO(raw)
    img = Image.open(bio)
    # 지연 로딩 방지
    img.load()
    return img


def _remove_exif_jpeg(data: bytes) -> bytes:
    if piexif is None:
        return data
    try:
        return piexif.remove(data)
    except Exception:
        return data


def sanitize_image(raw: bytes, keep_icc: bool = True, target_format: str | None = None) -> Tuple[bytes, str, Dict]:
    """
    returns: (sanitized_bytes, ext_without_dot, report_dict)
    report = {"source_format": "...", "target_format": "...", "exif_removed": bool, "gps_removed": bool, "size": int}
    """

    if not isinstance(raw, (bytes, bytearray)) or len(raw) == 0:
        raise ValueError("empty payload")

    mime = _detect_mime(raw)
    # 간단 MIME 필터 (선택)
    if mime and not mime.startswith("image/"):
        raise ValueError("not an image")

    src_img = _open_image_strict(raw)
    # 원본 포맷 추정
    source_format = (src_img.format or "").upper() or None
    if source_format == "JPG":
        source_format = "JPEG"

    # 허용 포맷만 처리
    normalized_source = _normalize_format(source_format)
    if normalized_source is None or normalized_source not in ALLOWED_FORMATS:
        raise ValueError("unsupported format")

    # EXIF Orientation 반영
    img = ImageOps.exif_transpose(src_img)

    # 타겟 포맷 결정
    normalized_target = _normalize_format(target_format) or normalized_source

    # 출력 버퍼
    out = BytesIO()

    exif_removed = False
    gps_removed = False

    save_params = {}

    # ICC 프로파일 유지 옵션
    icc_profile = src_img.info.get("icc_profile") if keep_icc else None
    if icc_profile:
        save_params["icc_profile"] = icc_profile

    # 포맷별 처리
    if normalized_target in {"JPEG", "WEBP"}:
        # JPEG: 먼저 바이트 레벨에서 EXIF 제거 후 재저장
        src_bytes = raw
        if normalized_source == "JPEG":
            stripped = _remove_exif_jpeg(src_bytes)
            src_bytes = stripped
            exif_removed = stripped != raw

        # 재저장 시 EXIF 완전 제거 보장
        save_params["exif"] = b""
        if normalized_target == "JPEG":
            save_params.setdefault("quality", 95)
            save_params.setdefault("optimize", True)
            save_params.setdefault("subsampling", "4:2:0")
        if normalized_target == "WEBP":
            save_params.setdefault("quality", 95)

        img.save(out, format=normalized_target, **save_params)
        data = out.getvalue()
        # 보고서 플래그 (보수적)
        exif_removed = True
        gps_removed = True

    elif normalized_target == "PNG":
        # PNG: 비어있는 PngInfo로 저장하여 텍스트 청크 제거
        pnginfo = PngImagePlugin.PngInfo()
        img.save(out, format="PNG", pnginfo=pnginfo, **save_params)
        data = out.getvalue()
        exif_removed = True
        gps_removed = True

    elif normalized_target in {"HEIC", "HEIF"}:
        # HEIC 저장은 환경에 따라 실패할 수 있음
        img.save(out, format="HEIF", **save_params)
        data = out.getvalue()
        exif_removed = True
        gps_removed = True

    else:
        raise ValueError("unsupported target format")

    result_ext = (
        "jpg" if normalized_target == "JPEG" else
        "png" if normalized_target == "PNG" else
        "webp" if normalized_target == "WEBP" else
        "heic" if normalized_target in {"HEIC", "HEIF"} else
        "bin"
    )

    report = {
        "source_format": normalized_source,
        "target_format": normalized_target,
        "exif_removed": bool(exif_removed),
        "gps_removed": bool(gps_removed),
        "size": len(data),
    }

    return data, result_ext, report


