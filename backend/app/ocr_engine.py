"""
OCR Engine for character box reading.
Reads handwritten characters from boxed regions on OMR forms.

Phase 1: Template matching + contour analysis
Phase 2: CNN model (ONNX) - to be added later
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Character box positions as ratios of the warped image
# These must match the form_generator layout
CHAR_BOX_CONFIG = {
    "name": {
        "top": 0.072,
        "left": 0.065,
        "label_width_ratio": 0.04,
        "num_boxes": 20,
        "box_width": 0.031,
        "box_height": 0.025,
        "type": "alpha",
    },
    "surname": {
        "top": 0.100,
        "left": 0.065,
        "label_width_ratio": 0.04,
        "num_boxes": 20,
        "box_width": 0.031,
        "box_height": 0.025,
        "type": "alpha",
    },
    "student_no": {
        "top": 0.128,
        "left": 0.065,
        "label_width_ratio": 0.04,
        "num_boxes": 9,
        "box_width": 0.031,
        "box_height": 0.025,
        "type": "numeric",
    },
}

# Confidence threshold for review
REVIEW_THRESHOLD = 0.6


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
        self.empty_threshold = 0.03  # below this = empty box
        self.digit_templates = self._create_digit_templates()

    def _create_digit_templates(self) -> dict:
        """Create simple rendered templates for digits 0-9."""
        templates = {}
        for digit in range(10):
            img = np.zeros((40, 30), dtype=np.uint8)
            cv2.putText(img, str(digit), (4, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, 255, 2)
            templates[str(digit)] = img
        return templates

    def _create_alpha_templates(self) -> dict:
        """Create rendered templates for A-Z + Turkish chars."""
        templates = {}
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        for ch in chars:
            img = np.zeros((40, 30), dtype=np.uint8)
            cv2.putText(img, ch, (2, 32),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, 255, 2)
            templates[ch] = img
        return templates

    def extract_box_images(self, warped_gray: np.ndarray,
                           field_config: dict) -> list[np.ndarray]:
        """Extract individual character images from box regions."""
        h, w = warped_gray.shape[:2]

        top = int(h * field_config["top"])
        left = int(w * (field_config["left"] + field_config["label_width_ratio"]))
        box_w = int(w * field_config["box_width"])
        box_h = int(h * field_config["box_height"])
        num_boxes = field_config["num_boxes"]

        boxes = []
        for i in range(num_boxes):
            x1 = left + i * box_w
            y1 = top
            x2 = x1 + box_w
            y2 = y1 + box_h

            # Clamp to image bounds
            x1 = max(0, min(x1, w - 1))
            x2 = max(0, min(x2, w))
            y1 = max(0, min(y1, h - 1))
            y2 = max(0, min(y2, h))

            if x2 <= x1 or y2 <= y1:
                boxes.append(np.zeros((box_h, box_w), dtype=np.uint8))
                continue

            cell = warped_gray[y1:y2, x1:x2]

            # Remove box borders (inner region)
            pad = max(2, int(min(cell.shape) * 0.12))
            inner = cell[pad:-pad, pad:-pad] if cell.shape[0] > 2 * pad and cell.shape[1] > 2 * pad else cell

            boxes.append(inner)

        return boxes

    def is_empty_box(self, box_img: np.ndarray) -> bool:
        """Check if a box is empty (no writing)."""
        if box_img.size == 0:
            return True

        # Adaptive threshold
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

        # Preprocess
        binary = cv2.adaptiveThreshold(
            box_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 5
        )

        # Resize to template size
        resized = cv2.resize(binary, (30, 40))

        best_match = ""
        best_score = 0.0

        for digit, template in self.digit_templates.items():
            # Normalized cross-correlation
            result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
            score = float(np.max(result))
            if score > best_score:
                best_score = score
                best_match = digit

        # Also try contour-based features for digits
        contour_result = self._contour_digit_recognition(binary)
        if contour_result and contour_result[1] > best_score:
            best_match, best_score = contour_result

        # Normalize confidence to 0-1
        confidence = max(0.0, min(1.0, (best_score + 0.5) / 1.5))

        return CharacterResult(best_match, confidence)

    def _contour_digit_recognition(self, binary: np.ndarray) -> Optional[tuple]:
        """Simple contour-based digit recognition."""
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        # Get the largest contour
        cnt = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(cnt)
        if area < 20:
            return None

        # Bounding rect aspect ratio
        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect = bw / max(bh, 1)

        # Count holes (internal contours)
        contours_all, hierarchy = cv2.findContours(
            binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        holes = 0
        if hierarchy is not None:
            for i, h in enumerate(hierarchy[0]):
                if h[3] >= 0:  # has parent = is a hole
                    holes += 1

        # Simple rules (not perfect, but helps)
        # 0: wide, 1 hole; 1: narrow; 8: 2 holes; etc.
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

        # For alpha, use template matching (basic version)
        if box_img.size == 0 or self.is_empty_box(box_img):
            return CharacterResult("", 0.0)

        templates = self._create_alpha_templates()

        binary = cv2.adaptiveThreshold(
            box_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 11, 5
        )
        resized = cv2.resize(binary, (30, 40))

        best_match = ""
        best_score = 0.0

        for char, template in templates.items():
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
        if field_name not in CHAR_BOX_CONFIG:
            return FieldResult(text="", needs_review=True)

        config = CHAR_BOX_CONFIG[field_name]
        boxes = self.extract_box_images(warped_gray, config)

        characters = []
        char_confidences = []
        text = ""
        needs_review = False

        for i, box_img in enumerate(boxes):
            if self.is_empty_box(box_img):
                # Stop at first empty box (trailing spaces)
                break

            result = self.recognize_character(box_img, config["type"])
            characters.append(result)
            char_confidences.append(result.confidence)
            text += result.character

            if result.confidence < REVIEW_THRESHOLD:
                needs_review = True

        avg_conf = sum(char_confidences) / max(len(char_confidences), 1)

        return FieldResult(
            text=text,
            characters=characters,
            avg_confidence=avg_conf,
            needs_review=needs_review,
            char_confidences=char_confidences,
        )
