"""公众号封面图体积适配：永久素材接口要求 ≤2MB，超限则自动缩放 + JPEG 重压缩。

时间：2026-03-13；理由：用户上传手机/相机原图常超 2MB 导致 WeChatMPClientError；方法：PIL 限制长边并迭代 quality，
输出略低于 2MB 留出 multipart 余量。不改变微信官方上限，仅服务端/管线内自救。

对齐：backend/services/wechat_mp_service/client.py upload_image_permanent 仍保留最终字节校验。
"""
from __future__ import annotations

import io
import logging
from typing import Optional, Tuple

from PIL import Image

logger = logging.getLogger(__name__)

# 微信文档：永久图片素材 ≤2MB
_MAX_WECHAT_COVER_BYTES = 2 * 1024 * 1024
# 留出编码与 multipart 边界余量，避免「刚好 2MB」仍被拒
_TARGET_MAX_BYTES = _MAX_WECHAT_COVER_BYTES - 96 * 1024

# 长边像素候选（从大到小）
_MAX_SIDE_CANDIDATES = (2048, 1600, 1280, 1024, 900, 800, 640, 512)
_JPEG_QUALITIES = (90, 85, 82, 78, 74, 70, 66, 62, 58, 55, 52, 48)


def _flatten_rgba_for_jpeg(img: Image.Image) -> Image.Image:
    if img.mode == "LA":
        img = img.convert("RGBA")
    if img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        return bg
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _resize_max_side(img: Image.Image, max_side: int) -> Image.Image:
    w, h = img.size
    m = max(w, h)
    if m <= max_side:
        return img
    scale = max_side / float(m)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    return img.resize((nw, nh), Image.Resampling.LANCZOS)


def _encode_jpeg(img: Image.Image, quality: int) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def fit_wechat_cover_image(content: bytes, original_filename: str = "cover.jpg") -> Tuple[bytes, str]:
    """
    若 content 已超过目标上限，则解码为位图后压缩为 JPEG，直至 ≤ _TARGET_MAX_BYTES。
    已在限制内则原样返回（文件名不变）。

    Returns:
        (bytes, filename)  filename 在发生重编码时为 cover.jpg
    """
    if not content:
        raise ValueError("图片内容为空")

    if len(content) <= _TARGET_MAX_BYTES:
        return content, (original_filename or "cover.jpg")

    try:
        img = Image.open(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"无法解析图片: {e}") from e

    # 动图仅取首帧
    if getattr(img, "n_frames", 1) > 1:
        img.seek(0)

    if img.mode == "P":
        img = img.convert("RGBA" if "transparency" in img.info else "RGB")
    if img.mode in ("RGBA", "LA"):
        img = _flatten_rgba_for_jpeg(img)
    elif img.mode != "RGB":
        img = img.convert("RGB")

    last_error: Optional[str] = None
    for max_side in _MAX_SIDE_CANDIDATES:
        scaled = _resize_max_side(img, max_side)
        for q in _JPEG_QUALITIES:
            try:
                out = _encode_jpeg(scaled, q)
            except Exception as e:
                last_error = str(e)
                continue
            if len(out) <= _TARGET_MAX_BYTES:
                logger.info(
                    "封面图已自动压缩: 原始 %s 字节 → %s 字节 (长边≤%s, JPEG q=%s)",
                    len(content),
                    len(out),
                    max_side,
                    q,
                )
                return out, "cover.jpg"

    raise ValueError(
        last_error
        or "无法在保持可辨识度的前提下将封面压到 2MB 以下，请换一张更小或更简单的图片"
    )
