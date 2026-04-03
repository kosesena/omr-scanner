"""
OCR Engine for character box reading.
Uses Tesseract OCR for handwriting recognition.
Box positions computed from form_generator.py layout.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False
    logger.warning("pytesseract not installed — OCR will use fallback")

# Form layout constants (must match form_generator.py AND omr_engine.py)
PAGE_W_PT = 595.28
PAGE_H_PT = 841.89
MM = 2.8346457
MARGIN_PT = 14 * MM
MARKER_MARGIN_PT = 6 * MM
MARKER_SIZE_PT = 9 * MM

WARP_W = 1000
WARP_H = 1414
WARP_MARGIN = 30

_marker_half = MARKER_SIZE_PT / 2
MARKERS_RL = {
    0: (MARKER_MARGIN_PT + _marker_half,
        PAGE_H_PT - MARKER_MARGIN_PT - _marker_half),
    1: (PAGE_W_PT - MARKER_MARGIN_PT - _marker_half,
        PAGE_H_PT - MARKER_MARGIN_PT - _marker_half),
    2: (MARKER_MARGIN_PT + _marker_half,
        MARKER_MARGIN_PT + _marker_half),
    3: (PAGE_W_PT - MARKER_MARGIN_PT - _marker_half,
        MARKER_MARGIN_PT + _marker_half),
}


def _rl_to_img(x_rl: float, y_rl: float) -> tuple:
    m = WARP_MARGIN
    x_frac = (x_rl - MARKERS_RL[0][0]) / (MARKERS_RL[1][0] - MARKERS_RL[0][0])
    x_img = m + x_frac * (WARP_W - 2 * m)
    y_frac = (MARKERS_RL[0][1] - y_rl) / (MARKERS_RL[0][1] - MARKERS_RL[2][1])
    y_img = m + y_frac * (WARP_H - 2 * m)
    return x_img, y_img


def _compute_char_box_positions():
    """Compute exact pixel positions of character boxes in warped image."""
    title_y = PAGE_H_PT - MARKER_MARGIN_PT - MARKER_SIZE_PT - 5 * MM
    box_y_start = title_y - 14 * MM
    box_size = 5.5 * MM
    label_w = 24 * MM
    row_step = box_size + 3 * MM

    fields = {}
    field_defs = [
        ("name", 0, 20),
        ("surname", 1, 20),
        ("student_no", 2, 9),
    ]

    for field_name, row_idx, num_boxes in field_defs:
        y_rl = box_y_start - row_idx * row_step
        bx_start = MARGIN_PT + label_w

        boxes = []
        for i in range(num_boxes):
            x_left_rl = bx_start + i * box_size
            x_right_rl = x_left_rl + box_size
            y_bottom_rl = y_rl
            y_top_rl = y_rl + box_size

            x1_img, y1_img = _rl_to_img(x_left_rl, y_top_rl)
            x2_img, y2_img = _rl_to_img(x_right_rl, y_bottom_rl)
            boxes.append((int(x1_img), int(y1_img), int(x2_img), int(y2_img)))

        fields[field_name] = boxes

    return fields


def _compute_field_region(field_name: str, boxes: list) -> tuple:
    """Get the bounding region for an entire field (all boxes combined)."""
    if not boxes:
        return (0, 0, 0, 0)
    x1 = boxes[0][0]
    y1 = boxes[0][1]
    x2 = boxes[-1][2]
    y2 = boxes[0][3]
    return (x1, y1, x2, y2)


CHAR_BOX_POSITIONS = _compute_char_box_positions()


@dataclass
class CharacterResult:
    character: str = ""
    confidence: float = 0.0
    bbox: tuple = (0, 0, 0, 0)


@dataclass
class FieldResult:
    text: str = ""
    characters: list = field(default_factory=list)
    avg_confidence: float = 0.0
    needs_review: bool = False
    char_confidences: list = field(default_factory=list)


class OCREngine:
    """Handwriting recognition using Tesseract OCR."""

    def __init__(self):
        pass

    def _extract_field_image(self, warped_gray: np.ndarray,
                              field_name: str) -> Optional[np.ndarray]:
        """Extract the entire field region as one image for Tesseract."""
        if field_name not in CHAR_BOX_POSITIONS:
            return None

        boxes = CHAR_BOX_POSITIONS[field_name]
        x1, y1, x2, y2 = _compute_field_region(field_name, boxes)

        h, w = warped_gray.shape[:2]
        # Add small vertical padding
        pad = 2
        y1 = max(0, y1 - pad)
        y2 = min(h, y2 + pad)
        x1 = max(0, x1)
        x2 = min(w, x2)

        if x2 <= x1 or y2 <= y1:
            return None

        return warped_gray[y1:y2, x1:x2]

    def _preprocess_for_ocr(self, img: np.ndarray) -> np.ndarray:
        """Preprocess field image for better Tesseract recognition."""
        if img is None or img.size == 0:
            return img

        # Upscale for better recognition (Tesseract works better with larger images)
        scale = max(3, 100 // max(img.shape[0], 1))
        upscaled = cv2.resize(img, None, fx=scale, fy=scale,
                               interpolation=cv2.INTER_CUBIC)

        # Binarize: Otsu threshold (works well for handwriting on white background)
        _, binary = cv2.threshold(upscaled, 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Slight denoise
        binary = cv2.medianBlur(binary, 3)

        return binary

    def _tesseract_read(self, img: np.ndarray, char_type: str) -> tuple:
        """Run Tesseract OCR on preprocessed image. Returns (text, confidence)."""
        if not HAS_TESSERACT or img is None or img.size == 0:
            return ("", 0.0)

        # Tesseract config based on field type
        if char_type == "numeric":
            config = "--psm 7 -c tessedit_char_whitelist=0123456789"
        else:
            # Turkish uppercase letters + space
            config = "--psm 7 -c tessedit_char_whitelist=ABCÇDEFGĞHIİJKLMNOÖPQRSŞTUÜVWXYZ "

        try:
            # Get detailed data
            data = pytesseract.image_to_data(
                img, lang="tur" if char_type != "numeric" else "eng",
                config=config, output_type=pytesseract.Output.DICT
            )

            # Combine text from all detected words
            texts = []
            confidences = []
            for i, text in enumerate(data["text"]):
                text = text.strip()
                if text:
                    texts.append(text)
                    conf = int(data["conf"][i])
                    if conf > 0:
                        confidences.append(conf / 100.0)

            result_text = " ".join(texts).strip()
            avg_conf = sum(confidences) / max(len(confidences), 1)

            return (result_text, avg_conf)

        except Exception as e:
            logger.warning(f"Tesseract error: {e}")
            return ("", 0.0)

    def _fallback_read(self, warped_gray: np.ndarray,
                        field_name: str) -> tuple:
        """Fallback: count non-empty boxes and return placeholder."""
        boxes = CHAR_BOX_POSITIONS.get(field_name, [])
        h, w = warped_gray.shape[:2]
        chars = []

        for (x1, y1, x2, y2) in boxes:
            x1c = max(0, min(x1, w - 1))
            x2c = max(0, min(x2, w))
            y1c = max(0, min(y1, h - 1))
            y2c = max(0, min(y2, h))

            if x2c <= x1c or y2c <= y1c:
                break

            cell = warped_gray[y1c:y2c, x1c:x2c]
            # Pad to get inner region
            pad = max(2, int(min(cell.shape) * 0.15))
            if cell.shape[0] > 2 * pad and cell.shape[1] > 2 * pad:
                inner = cell[pad:-pad, pad:-pad]
            else:
                inner = cell

            # Check if empty
            mean_val = float(np.mean(inner))
            dark_ratio = float(np.sum(inner < 120)) / max(inner.size, 1)

            if mean_val > 190 or dark_ratio < 0.04:
                # Trailing empty → stop
                remaining_empty = True
                for bx in boxes[boxes.index((x1, y1, x2, y2)) + 1:]:
                    bx1, by1, bx2, by2 = bx
                    c = warped_gray[max(0, by1):min(h, by2), max(0, bx1):min(w, bx2)]
                    if float(np.mean(c)) < 190:
                        remaining_empty = False
                        break
                if remaining_empty:
                    break
                chars.append(" ")
            else:
                chars.append("?")

        text = "".join(chars).strip()
        return (text, 0.3)

    def read_field(self, warped_gray: np.ndarray,
                   field_name: str) -> FieldResult:
        """Read a field using Tesseract OCR with fallback."""
        char_type = "numeric" if field_name == "student_no" else "alpha"

        # Extract and preprocess field image
        field_img = self._extract_field_image(warped_gray, field_name)
        processed = self._preprocess_for_ocr(field_img)

        # Try Tesseract
        text, confidence = self._tesseract_read(processed, char_type)

        # If Tesseract failed, use fallback
        if not text:
            text, confidence = self._fallback_read(warped_gray, field_name)

        needs_review = confidence < 0.7 or not text

        return FieldResult(
            text=text,
            characters=[],
            avg_confidence=confidence,
            needs_review=needs_review,
            char_confidences=[confidence] * max(len(text), 1),
        )
