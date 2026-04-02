"""
QR Code reader for OMR forms.
Reads exam metadata embedded in QR codes on the form.
"""

import json
import numpy as np
import cv2
from typing import Optional

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
    from pyzbar.pyzbar import ZBarSymbol
    HAS_PYZBAR = True
except ImportError:
    HAS_PYZBAR = False


def read_qr_from_image(image: np.ndarray) -> Optional[dict]:
    """
    Detect and decode QR code from form image.
    Returns parsed JSON dict or None.
    """
    if not HAS_PYZBAR:
        return None

    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image

    # Try original image
    result = _try_decode(gray)
    if result:
        return result

    # Try with enhanced contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    result = _try_decode(enhanced)
    if result:
        return result

    # Try with binary threshold
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    result = _try_decode(binary)
    if result:
        return result

    return None


def _try_decode(image: np.ndarray) -> Optional[dict]:
    """Try to decode QR from an image."""
    try:
        decoded = pyzbar_decode(image, symbols=[ZBarSymbol.QRCODE])
        for obj in decoded:
            try:
                data = json.loads(obj.data.decode("utf-8"))
                if isinstance(data, dict) and "exam_id" in data:
                    return data
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    except Exception:
        pass
    return None
