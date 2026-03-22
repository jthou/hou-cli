"""cover_image_fit 单测：时间 2026-03-13；理由：封面上传自动压缩需可回归；方法：PIL 造大图断言输出 ≤ 目标字节。"""
from __future__ import annotations

import io
from typing import Tuple

import pytest
from PIL import Image

from backend.services.wechat_mp_service.cover_image_fit import (
    _TARGET_MAX_BYTES,
    fit_wechat_cover_image,
)


def _random_rgb_image(size: Tuple[int, int]) -> bytes:
    import random

    img = Image.new("RGB", size)
    pixels = img.load()
    for y in range(size[1]):
        for x in range(size[0]):
            pixels[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=3)
    return buf.getvalue()


def test_small_image_unchanged():
    img = Image.new("RGB", (32, 32), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    raw = buf.getvalue()
    out, name = fit_wechat_cover_image(raw, "x.jpg")
    assert out == raw
    assert name == "x.jpg"


def test_large_random_png_compressed_under_cap():
    raw = _random_rgb_image((1200, 1200))
    assert len(raw) > _TARGET_MAX_BYTES, "fixture must exceed cap"
    out, name = fit_wechat_cover_image(raw, "big.png")
    assert len(out) <= _TARGET_MAX_BYTES
    assert name == "cover.jpg"
    Image.open(io.BytesIO(out)).verify()


def test_webp_sized_under_cap_still_valid():
    img = Image.new("RGB", (64, 64), color=(10, 20, 30))
    buf = io.BytesIO()
    try:
        img.save(buf, format="WEBP", quality=80)
    except Exception:
        pytest.skip("Pillow WebP encoder unavailable")
    raw = buf.getvalue()
    if len(raw) > _TARGET_MAX_BYTES:
        pytest.skip("tiny webp unexpectedly huge")
    out, name = fit_wechat_cover_image(raw, "a.webp")
    assert out == raw
