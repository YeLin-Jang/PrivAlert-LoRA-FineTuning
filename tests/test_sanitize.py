import io
import os
import pytest
from PIL import Image, PngImagePlugin

from utils.image_sanitize import sanitize_image, MAX_BYTES, MAX_PIXELS


def _make_png_with_text(text_key: str = "Comment", text_val: str = "hello") -> bytes:
    img = Image.new("RGB", (32, 32), color=(123, 222, 111))
    meta = PngImagePlugin.PngInfo()
    meta.add_text(text_key, text_val)
    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=meta)
    return buf.getvalue()


def test_png_text_chunks_removed():
    raw = _make_png_with_text()
    out, ext, report = sanitize_image(raw, keep_icc=True, target_format="png")
    assert ext == "png"
    # 재로딩하여 텍스트 청크가 제거되었는지 확인
    img = Image.open(io.BytesIO(out))
    assert not any(k for k in img.info.keys() if k in {"parameters", "Comment", "Description"})
    assert report["exif_removed"] is True


@pytest.mark.skip(reason="Embedding real GPS EXIF requires piexif crafting; smoke test only")
def test_jpeg_exif_removed_smoke():
    img = Image.new("RGB", (32, 32), color=(20, 30, 40))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    raw = buf.getvalue()
    out, ext, report = sanitize_image(raw, keep_icc=False, target_format="jpeg")
    assert ext == "jpg"
    assert report["exif_removed"] is True


def test_limits_enforced_by_small_values(monkeypatch):
    # 픽셀 상한을 작게 내려 테스트
    from utils import image_sanitize as mod

    monkeypatch.setattr(mod, "MAX_PIXELS", 1000)
    big = Image.new("RGB", (200, 200))  # 40,000px
    buf = io.BytesIO()
    big.save(buf, format="PNG")
    raw = buf.getvalue()

    with pytest.raises(Exception):
        mod.sanitize_image(raw)


