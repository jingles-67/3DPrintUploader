"""QR code generation utilities."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Optional

import qrcode
from PIL import Image, ImageTk

logger = logging.getLogger("3D Print Uploader")


def generate_qr_image(
    data: str,
    size: int = 200,
    fill_color: str = "black",
    back_color: str = "white",
) -> Image.Image:
    """
    Generate a QR code PIL Image for the given data string.

    Args:
        data: Text or URL to encode.
        size: Output image width/height in pixels.
        fill_color: QR module color.
        back_color: Background color.

    Returns:
        PIL Image object.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGB")
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    logger.debug("Generated QR code (%dpx) for: %s", size, data[:60])
    return img


def qr_to_photoimage(
    data: str,
    size: int = 200,
    fill_color: str = "black",
    back_color: str = "white",
) -> Optional[ImageTk.PhotoImage]:
    """
    Generate a Tkinter PhotoImage QR code.

    Returns None if generation fails.
    """
    try:
        pil_img = generate_qr_image(data, size, fill_color, back_color)
        return ImageTk.PhotoImage(pil_img)
    except Exception as exc:
        logger.error("QR code generation failed: %s", exc)
        return None


def save_qr_code(data: str, output_path: str, size: int = 512) -> bool:
    """Save a QR code image to disk. Returns True on success."""
    try:
        img = generate_qr_image(data, size=size)
        img.save(output_path)
        logger.info("QR code saved to %s", output_path)
        return True
    except Exception as exc:
        logger.error("Failed to save QR code: %s", exc)
        return False


def qr_png_bytes(data: str, size: int = 512) -> Optional[bytes]:
    """Return QR code as PNG bytes, or None on failure."""
    try:
        img = generate_qr_image(data, size=size)
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    except Exception as exc:
        logger.error("QR PNG export failed: %s", exc)
        return None
