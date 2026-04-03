"""
OCR Engine for character box reading.
Uses Tesseract OCR for handwriting recognition.
Each character box is read individually (--psm 10 = single char mode).
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
    """Handwriting recognition — reads each character box individually."""

    def __init__(self):
        pass

    def _extract_single_box(self, warped_gray: np.ndarray,
                             box: tuple) -> Optional[np.ndarray]:
        """Extract a single character box, cropping out borders."""
        x1, y1, x2, y2 = box
        h, w = warped_gray.shape[:2]

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        if x2 <= x1 or y2 <= y1:
            return None

        cell = warped_gray[y1:y2, x1:x2]

        # Crop inner ~70% to remove box border lines
        ch, cw = cell.shape[:2]
        pad_x = max(2, int(cw * 0.15))
        pad_y = max(2, int(ch * 0.15))
        inner = cell[pad_y:ch - pad_y, pad_x:cw - pad_x]

        if inner.size == 0:
            return None

        return inner

    def _is_box_empty(self, inner: np.ndarray) -> bool:
        """Check if a box is empty (no handwriting)."""
        if inner is None or inner.size == 0:
            return True

        mean_val = float(np.mean(inner))
        # Dark pixel ratio (pixels darker than 140)
        dark_ratio = float(np.sum(inner < 140)) / max(inner.size, 1)

        # Empty box: mostly white, very few dark pixels
        if mean_val > 180 and dark_ratio < 0.08:
            return True

        return False

    def _preprocess_single_char(self, img: np.ndarray) -> np.ndarray:
        """Preprocess a single character box for Tesseract."""
        if img is None or img.size == 0:
            return img

        # Upscale significantly — Tesseract needs at least ~30px tall characters
        target_h = 80
        scale = max(target_h / max(img.shape[0], 1), 2)
        upscaled = cv2.resize(img, None, fx=scale, fy=scale,
                               interpolation=cv2.INTER_CUBIC)

        # Binarize with Otsu
        _, binary = cv2.threshold(upscaled, 0, 255,
                                   cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Add white border (Tesseract needs some padding around chars)
        border = 15
        padded = cv2.copyMakeBorder(binary, border, border, border, border,
                                     cv2.BORDER_CONSTANT, value=255)

        return padded

    def _tesseract_single_char(self, img: np.ndarray, char_type: str) -> tuple:
        """Run Tesseract on a single character. Returns (char, confidence)."""
        if not HAS_TESSERACT or img is None or img.size == 0:
            return ("", 0.0)

        # PSM 10 = single character mode
        if char_type == "numeric":
            config = "--psm 10 -c tessedit_char_whitelist=0123456789"
        else:
            config = "--psm 10 -c tessedit_char_whitelist=ABCCDEFGGHIIJKLMNOOPQRSSTUUVWXYZÇĞİÖŞÜ"

        try:
            data = pytesseract.image_to_data(
                img, lang="tur" if char_type != "numeric" else "eng",
                config=config, output_type=pytesseract.Output.DICT
            )

            best_text = ""
            best_conf = 0.0

            for i, text in enumerate(data["text"]):
                text = text.strip()
                if text:
                    conf = int(data["conf"][i])
                    if conf > best_conf:
                        best_text = text
                        best_conf = conf

            # Normalize: take only first character
            if best_text:
                best_text = best_text[0].upper()

            return (best_text, best_conf / 100.0 if best_conf > 0 else 0.0)

        except Exception as e:
            logger.warning(f"Tesseract error: {e}")
            return ("", 0.0)

    def read_field(self, warped_gray: np.ndarray,
                   field_name: str) -> FieldResult:
        """Read a field by reading each character box individually."""
        char_type = "numeric" if field_name == "student_no" else "alpha"
        boxes = CHAR_BOX_POSITIONS.get(field_name, [])

        characters = []
        confidences = []
        trailing_empty = 0

        for box in boxes:
            inner = self._extract_single_box(warped_gray, box)

            if self._is_box_empty(inner):
                # Check if all remaining boxes are also empty → stop
                remaining_idx = boxes.index(box)
                all_remaining_empty = True
                for rem_box in boxes[remaining_idx + 1:]:
                    rem_inner = self._extract_single_box(warped_gray, rem_box)
                    if not self._is_box_empty(rem_inner):
                        all_remaining_empty = False
                        break

                if all_remaining_empty:
                    break  # End of text

                # Gap in the middle (e.g., "SENA NUR" has space)
                characters.append(" ")
                confidences.append(1.0)
                continue

            # Non-empty box → OCR
            processed = self._preprocess_single_char(inner)

            if HAS_TESSERACT:
                char, conf = self._tesseract_single_char(processed, char_type)
            else:
                char, conf = ("?", 0.3)

            if char:
                characters.append(char)
                confidences.append(conf)
            else:
                characters.append("?")
                confidences.append(0.0)

        text = "".join(characters).strip()
        avg_conf = sum(confidences) / max(len(confidences), 1)
        needs_review = avg_conf < 0.5 or not text or "?" in text

        logger.info(f"OCR {field_name}: '{text}' (conf={avg_conf:.2f}, "
                     f"chars={len(characters)})")

        return FieldResult(
            text=text,
            characters=characters,
            avg_confidence=avg_conf,
            needs_review=needs_review,
            char_confidences=confidences,
        )
