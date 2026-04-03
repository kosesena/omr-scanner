"""
OCR Engine for character box reading.
Reads handwritten characters from boxed regions on OMR forms.

Positions are computed directly from form_generator.py layout parameters,
ensuring exact alignment with the printed form.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

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

REVIEW_THRESHOLD = 0.6


def _rl_to_img(x_rl: float, y_rl: float) -> tuple:
    """Convert ReportLab coordinate to warped image pixel."""
    m = WARP_MARGIN
    x_frac = (x_rl - MARKERS_RL[0][0]) / (MARKERS_RL[1][0] - MARKERS_RL[0][0])
    x_img = m + x_frac * (WARP_W - 2 * m)
    y_frac = (MARKERS_RL[0][1] - y_rl) / (MARKERS_RL[0][1] - MARKERS_RL[2][1])
    y_img = m + y_frac * (WARP_H - 2 * m)
    return x_img, y_img


def _compute_char_box_positions():
    """
    Compute exact pixel positions of character boxes in the warped image,
    replicating form_generator.py layout.

    Returns dict: {field_name: [(x1, y1, x2, y2), ...]} in warped image pixels
    """
    title_y = PAGE_H_PT - MARKER_MARGIN_PT - MARKER_SIZE_PT - 5 * MM
    box_y_start = title_y - 14 * MM
    box_size = 5.5 * MM
    label_w = 24 * MM
    row_step = box_size + 3 * MM

    fields = {}

    # Three rows: AD, SOYAD, NO
    field_defs = [
        ("name", 0, 20),
        ("surname", 1, 20),
        ("student_no", 2, 9),
    ]

    for field_name, row_idx, num_boxes in field_defs:
        y_rl = box_y_start - row_idx * row_step  # RL y of box bottom-left
        bx_start = MARGIN_PT + label_w

        boxes = []
        for i in range(num_boxes):
            # Box corners in RL coords
            x_left_rl = bx_start + i * box_size
            x_right_rl = x_left_rl + box_size
            y_bottom_rl = y_rl
            y_top_rl = y_rl + box_size

            # Convert to warped image pixels
            x1_img, y1_img = _rl_to_img(x_left_rl, y_top_rl)   # top-left in image
            x2_img, y2_img = _rl_to_img(x_right_rl, y_bottom_rl)  # bottom-right in image

            boxes.append((int(x1_img), int(y1_img), int(x2_img), int(y2_img)))

        fields[field_name] = boxes

    return fields


# Pre-compute positions at module load
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
    """Handwriting recognition engine for character boxes."""

    def __init__(self):
        self.empty_threshold = 0.03
        self.digit_templates = self._create_digit_templates()
        self.alpha_templates = self._create_alpha_templates()

    def _create_digit_templates(self) -> dict:
        """Create rendered templates for digits 0-9."""
        templates = {}
        for digit in range(10):
            img = np.zeros((40, 30), dtype=np.uint8)
            cv2.putText(img, str(digit), (4, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 2)
            templates[str(digit)] = img
        return templates

    def _create_alpha_templates(self) -> dict:
        """Create rendered templates for A-Z + digits."""
        templates = {}
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        for ch in chars:
            img = np.zeros((40, 30), dtype=np.uint8)
            cv2.putText(img, ch, (2, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, 255, 2)
            templates[ch] = img
        return templates

    def extract_box_images(self, warped_gray: np.ndarray,
                           field_name: str) -> list[np.ndarray]:
        """Extract individual character images using exact computed positions."""
        h, w = warped_gray.shape[:2]

        if field_name not in CHAR_BOX_POSITIONS:
            return []

        boxes = []
        for (x1, y1, x2, y2) in CHAR_BOX_POSITIONS[field_name]:
            # Clamp to image bounds
            x1c = max(0, min(x1, w - 1))
            x2c = max(0, min(x2, w))
            y1c = max(0, min(y1, h - 1))
            y2c = max(0, min(y2, h))

            if x2c <= x1c or y2c <= y1c:
                boxes.append(np.zeros((20, 20), dtype=np.uint8))
                continue

            cell = warped_gray[y1c:y2c, x1c:x2c]

            # Remove box borders (inner region ~15% padding)
            pad_y = max(2, int(cell.shape[0] * 0.15))
            pad_x = max(2, int(cell.shape[1] * 0.15))
            if cell.shape[0] > 2 * pad_y and cell.shape[1] > 2 * pad_x:
                inner = cell[pad_y:-pad_y, pad_x:-pad_x]
            else:
                inner = cell

            boxes.append(inner)

        return boxes

    def is_empty_box(self, box_img: np.ndarray) -> bool:
        """Check if a box is empty (no writing)."""
        if box_img.size == 0:
            return True

        binary = cv2.adaptiveThreshold(
            box_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 5
        )
        fill_ratio = np.sum(binary > 0) / binary.size
        return fill_ratio < self.empty_threshold

    def recognize_digit(self, box_img: np.ndarray) -> CharacterResult:
        """Recognize a single digit using template matching."""
        if box_img.size == 0 or self.is_empty_box(box_img):
            return CharacterResult("", 0.0)

        binary = cv2.adaptiveThreshold(
            box_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 5
        )
        resized = cv2.resize(binary, (30, 40))

        best_match = ""
        best_score = 0.0

        for digit, template in self.digit_templates.items():
            result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
            score = float(np.max(result))
            if score > best_score:
                best_score = score
                best_match = digit

        # Contour-based fallback
        contour_result = self._contour_digit_recognition(binary)
        if contour_result and contour_result[1] > best_score:
            best_match, best_score = contour_result

        confidence = max(0.0, min(1.0, (best_score + 0.5) / 1.5))
        return CharacterResult(best_match, confidence)

    def _contour_digit_recognition(self, binary: np.ndarray) -> Optional[tuple]:
        """Simple contour-based digit recognition."""
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        cnt = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(cnt)
        if area < 20:
            return None

        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect = bw / max(bh, 1)

        contours_all, hierarchy = cv2.findContours(
            binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        holes = 0
        if hierarchy is not None:
            for i, h_val in enumerate(hierarchy[0]):
                if h_val[3] >= 0:
                    holes += 1

        if holes >= 2:
            return ("8", 0.5)
        elif holes == 1:
            if aspect > 0.5:
                return ("0", 0.4)
            else:
                return ("4", 0.35)
        elif aspect < 0.35:
            return ("1", 0.45)

        return None

    def recognize_character(self, box_img: np.ndarray,
                            char_type: str = "alpha") -> CharacterResult:
        """Recognize a character from a box image."""
        if char_type == "numeric":
            return self.recognize_digit(box_img)

        if box_img.size == 0 or self.is_empty_box(box_img):
            return CharacterResult("", 0.0)

        binary = cv2.adaptiveThreshold(
            box_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 5
        )
        resized = cv2.resize(binary, (30, 40))

        best_match = ""
        best_score = 0.0

        for char, template in self.alpha_templates.items():
            result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
            score = float(np.max(result))
            if score > best_score:
                best_score = score
                best_match = char

        confidence = max(0.0, min(1.0, (best_score + 0.5) / 1.5))
        return CharacterResult(best_match, confidence)

    def read_field(self, warped_gray: np.ndarray,
                   field_name: str) -> FieldResult:
        """Read an entire field (name, surname, or student_no)."""
        field_type_map = {
            "name": "alpha",
            "surname": "alpha",
            "student_no": "numeric",
        }

        char_type = field_type_map.get(field_name, "alpha")
        boxes = self.extract_box_images(warped_gray, field_name)

        characters = []
        char_confidences = []
        text = ""
        needs_review = False

        for i, box_img in enumerate(boxes):
            if self.is_empty_box(box_img):
                # Check if remaining boxes are also empty (trailing)
                remaining = boxes[i:]
                all_empty = all(self.is_empty_box(b) for b in remaining)
                if all_empty:
                    break
                # Not trailing - could be a space
                text += " "
                char_confidences.append(1.0)
                continue

            result = self.recognize_character(box_img, char_type)
            characters.append(result)
            char_confidences.append(result.confidence)
            text += result.character

            if result.confidence < REVIEW_THRESHOLD:
                needs_review = True

        avg_conf = sum(char_confidences) / max(len(char_confidences), 1)

        return FieldResult(
            text=text.strip(),
            characters=characters,
            avg_confidence=avg_conf,
            needs_review=needs_review,
            char_confidences=char_confidences,
        )
