"""
OCR Engine for character box reading.

Strategy:
- Student number: read each digit box with Tesseract (--psm 10, digits only)
  with aggressive preprocessing (large upscale, normalize, adaptive threshold).
- Name/Surname: detect filled box pattern (which boxes have ink) and
  match against the class roster. Tesseract is too unreliable for
  handwritten letters at this resolution (~27px boxes from phone camera).

Box positions computed from form_generator.py layout.
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List
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
    box_pattern: list = field(default_factory=list)  # True/False per box


class OCREngine:
    """
    Hybrid OCR: digit recognition + roster matching for names.
    """

    def __init__(self):
        self._roster_students = []  # Set externally for matching
        self._last_student_no = ""  # Set after reading student_no, used for name matching

    def set_roster(self, students: list):
        """Set the roster for name/surname matching.
        students: list of dicts with 'name', 'surname', 'student_number'"""
        self._roster_students = students or []
        logger.info(f"OCR roster set: {len(self._roster_students)} students")

    # ---- Box extraction and analysis ----

    def _extract_box(self, warped_gray: np.ndarray, box: tuple) -> Optional[np.ndarray]:
        """Extract a single character box region."""
        x1, y1, x2, y2 = box
        h, w = warped_gray.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 <= x1 or y2 <= y1:
            return None
        return warped_gray[y1:y2, x1:x2]

    def _get_inner(self, cell: np.ndarray, margin_frac: float = 0.18) -> Optional[np.ndarray]:
        """Crop inner portion of a box, removing border lines."""
        if cell is None or cell.size == 0:
            return None
        ch, cw = cell.shape[:2]
        px = max(2, int(cw * margin_frac))
        py = max(2, int(ch * margin_frac))
        inner = cell[py:ch - py, px:cw - px]
        return inner if inner.size > 0 else None

    def _box_ink_score(self, inner: np.ndarray) -> float:
        """
        Compute the mean intensity of the inner region.
        Lower = more ink. We use mean intensity directly for comparison.
        """
        if inner is None or inner.size == 0:
            return 255.0  # white = empty

        return float(np.mean(inner))

    def _detect_filled_boxes(self, warped_gray: np.ndarray,
                              field_name: str) -> list:
        """
        Detect which boxes are filled using Otsu-like gap finding.

        Strategy: measure mean intensity per box. Empty boxes are bright
        (~190-230), filled boxes are dark (~80-160). Find the natural gap.

        Special case for student_no: all 9 boxes may be filled, so there's
        no empty reference. Use absolute threshold instead.
        """
        boxes = CHAR_BOX_POSITIONS.get(field_name, [])

        # Use aggressive crop: 30% margin to fully remove borders
        scores = []
        for i, box in enumerate(boxes):
            cell = self._extract_box(warped_gray, box)
            inner = self._get_inner(cell, margin_frac=0.30)
            score = self._box_ink_score(inner)
            scores.append(score)

        if not scores:
            return []

        sorted_scores = sorted(scores)

        # Find natural gap (largest intensity jump between consecutive sorted scores)
        max_gap = 0
        gap_threshold = 180
        for i in range(len(sorted_scores) - 1):
            gap = sorted_scores[i + 1] - sorted_scores[i]
            if gap > max_gap:
                max_gap = gap
                gap_threshold = (sorted_scores[i] + sorted_scores[i + 1]) / 2

        if max_gap > 20:
            # Clear gap between filled and empty groups — use it
            threshold = gap_threshold
        else:
            # No clear gap — either ALL filled or ALL empty
            # Use absolute threshold: anything below 185 is "filled"
            # (typical empty box ~195-230, filled ~80-170)
            lightest = sorted_scores[-1]
            if lightest < 185:
                # All boxes are relatively dark → probably all filled (like student_no)
                threshold = 250  # mark all as filled
            else:
                # All boxes are bright → probably all empty
                threshold = lightest - 25

        results = []
        for i, score in enumerate(scores):
            is_filled = score < threshold
            results.append((i, is_filled, score))

        filled_indices = [i for i, f, _ in results if f]
        logger.info(f"OCR {field_name}: intensities={[int(s) for s in scores]} "
                     f"max_gap={max_gap:.0f} threshold={threshold:.0f} "
                     f"filled={filled_indices}")

        return results

    # ---- Digit recognition with Tesseract ----

    def _preprocess_digit(self, cell: np.ndarray) -> Optional[np.ndarray]:
        """Aggressively preprocess a digit box for Tesseract."""
        if cell is None or cell.size == 0:
            return None

        # Get inner region (remove box borders)
        inner = self._get_inner(cell, margin_frac=0.20)
        if inner is None:
            return None

        # Step 1: Upscale to ~120px tall
        target_h = 120
        scale = max(target_h / max(inner.shape[0], 1), 3)
        big = cv2.resize(inner, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

        # Step 2: Normalize contrast (stretch to full 0-255 range)
        min_v, max_v = float(np.min(big)), float(np.max(big))
        if max_v - min_v > 20:
            normalized = ((big.astype(float) - min_v) / (max_v - min_v) * 255).astype(np.uint8)
        else:
            normalized = big

        # Step 3: Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(normalized, (3, 3), 0)

        # Step 4: Adaptive threshold (handles uneven lighting better than Otsu)
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 21, 8
        )

        # Step 5: Morphological close — fill small gaps in strokes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # Step 6: Add generous white border
        border = 20
        padded = cv2.copyMakeBorder(binary, border, border, border, border,
                                     cv2.BORDER_CONSTANT, value=255)

        return padded

    def _read_digit(self, cell: np.ndarray) -> tuple:
        """Read a single digit from a box. Returns (digit_str, confidence)."""
        if not HAS_TESSERACT:
            return ("?", 0.0)

        processed = self._preprocess_digit(cell)
        if processed is None:
            return ("?", 0.0)

        config = "--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789"
        try:
            # Try image_to_string first (simpler, often works for digits)
            text = pytesseract.image_to_string(
                processed, lang="eng", config=config
            ).strip()

            if text and text[0].isdigit():
                # Also get confidence
                data = pytesseract.image_to_data(
                    processed, lang="eng", config=config,
                    output_type=pytesseract.Output.DICT
                )
                conf = 0.0
                for i, t in enumerate(data["text"]):
                    if t.strip():
                        c = int(data["conf"][i])
                        if c > conf:
                            conf = c
                return (text[0], conf / 100.0)

            return ("?", 0.0)
        except Exception as e:
            logger.warning(f"Tesseract digit error: {e}")
            return ("?", 0.0)

    # ---- Name/Surname recognition via roster matching ----

    def _build_box_pattern(self, filled_boxes: list) -> tuple:
        """
        Build a text pattern from filled boxes.
        Returns (pattern_str, char_count, word_lengths).
        Example: "SENA NUR" → filled=[0,1,2,3, 5,6,7] → lengths=[4, 3]
        """
        # Find last filled box
        last_filled = -1
        for idx, is_filled, score in filled_boxes:
            if is_filled:
                last_filled = idx

        if last_filled < 0:
            return ("", 0, [])

        # Build pattern up to last filled
        pattern = []
        for idx, is_filled, score in filled_boxes:
            if idx > last_filled:
                break
            pattern.append("X" if is_filled else " ")

        pattern_str = "".join(pattern)

        # Extract word lengths
        words = pattern_str.split()
        word_lengths = [len(w) for w in words if w]
        char_count = sum(word_lengths)

        return (pattern_str, char_count, word_lengths)

    def _match_roster_name(self, field_name: str, pattern_str: str,
                            char_count: int, word_lengths: list,
                            student_no: str = "") -> tuple:
        """
        Match detected box pattern against roster.
        Returns (best_match_text, confidence).
        """
        if not self._roster_students:
            return ("", 0.0)

        candidates = []
        for student in self._roster_students:
            if field_name == "name":
                text = student.get("name", "").strip().upper()
            elif field_name == "surname":
                text = student.get("surname", "").strip().upper()
            else:
                continue

            if not text:
                continue

            # If we know student_no, only consider matching students
            if student_no and student_no != "?":
                sno = student.get("student_number", "")
                if sno and student_no not in sno and sno not in student_no:
                    continue

            # Compare word structure
            text_words = text.split()
            text_lengths = [len(w) for w in text_words]
            text_total = sum(text_lengths)

            score = 0.0

            # Total character count match
            if text_total == char_count:
                score += 0.5
            elif abs(text_total - char_count) <= 1:
                score += 0.2

            # Word count match
            if len(text_lengths) == len(word_lengths):
                score += 0.2
                # Individual word length match
                length_matches = sum(1 for a, b in zip(text_lengths, word_lengths)
                                     if a == b)
                score += 0.3 * length_matches / max(len(text_lengths), 1)

            if score > 0:
                candidates.append((text, score))

        if not candidates:
            return ("", 0.0)

        # Sort by score, pick best
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_text, best_score = candidates[0]

        # If there's a unique high-score match, confidence is high
        if len(candidates) == 1 and best_score >= 0.5:
            return (best_text, 0.9)
        elif best_score >= 0.7:
            return (best_text, 0.8)
        elif best_score >= 0.5:
            return (best_text, 0.6)
        else:
            return (best_text, 0.3)

    # ---- Public API ----

    def read_field(self, warped_gray: np.ndarray,
                   field_name: str) -> FieldResult:
        """
        Read a field:
        - student_no: per-box Tesseract digit recognition
        - name/surname: filled box pattern + roster matching
        """
        boxes = CHAR_BOX_POSITIONS.get(field_name, [])
        filled_info = self._detect_filled_boxes(warped_gray, field_name)

        # Build box pattern (which boxes have ink)
        pattern_str, char_count, word_lengths = self._build_box_pattern(filled_info)
        box_pattern = [f for _, f, _ in filled_info]

        logger.info(f"OCR {field_name}: pattern='{pattern_str}' "
                     f"chars={char_count} words={word_lengths}")

        if field_name == "student_no":
            return self._read_student_no(warped_gray, boxes, filled_info, box_pattern)
        else:
            return self._read_name_field(
                warped_gray, field_name, filled_info,
                pattern_str, char_count, word_lengths, box_pattern
            )

    def _read_student_no(self, warped_gray: np.ndarray, boxes: list,
                          filled_info: list, box_pattern: list) -> FieldResult:
        """Read student number using per-digit Tesseract."""
        characters = []
        confidences = []

        for idx, is_filled, ink_score in filled_info:
            if not is_filled:
                # Check if all remaining are empty
                remaining_filled = any(f for _, f, _ in filled_info[idx + 1:])
                if not remaining_filled:
                    break
                # Gap shouldn't happen in student number, but handle it
                characters.append("?")
                confidences.append(0.0)
                continue

            cell = self._extract_box(warped_gray, boxes[idx])
            digit, conf = self._read_digit(cell)
            characters.append(digit)
            confidences.append(conf)

        text = "".join(characters)
        avg_conf = sum(confidences) / max(len(confidences), 1)

        # Try roster matching for student_no too
        if "?" in text and self._roster_students:
            matched = self._match_student_no_roster(text)
            if matched:
                text = matched
                avg_conf = max(avg_conf, 0.7)

        needs_review = avg_conf < 0.5 or not text or "?" in text

        logger.info(f"OCR student_no: '{text}' (conf={avg_conf:.2f})")

        return FieldResult(
            text=text,
            characters=list(text),
            avg_confidence=avg_conf,
            needs_review=needs_review,
            char_confidences=confidences,
            box_pattern=box_pattern,
        )

    def _match_student_no_roster(self, partial_no: str) -> str:
        """Try to match a partial student number (with ? wildcards) to roster."""
        if not self._roster_students:
            return ""

        candidates = []
        for student in self._roster_students:
            sno = student.get("student_number", "").strip()
            if not sno or len(sno) != len(partial_no):
                continue

            match = True
            for a, b in zip(partial_no, sno):
                if a != "?" and a != b:
                    match = False
                    break

            if match:
                candidates.append(sno)

        if len(candidates) == 1:
            return candidates[0]

        return ""

    def _read_name_field(self, warped_gray: np.ndarray, field_name: str,
                          filled_info: list, pattern_str: str,
                          char_count: int, word_lengths: list,
                          box_pattern: list) -> FieldResult:
        """Read name/surname field using box pattern + roster matching."""

        # Try roster matching (use student_no hint if available)
        matched_text, match_conf = self._match_roster_name(
            field_name, pattern_str, char_count, word_lengths,
            student_no=self._last_student_no
        )

        if matched_text and match_conf >= 0.5:
            text = matched_text
            avg_conf = match_conf
        else:
            # No roster match — show pattern with char count
            # e.g., "XXXX XXX" → "[4] [3]" or just the raw pattern
            if word_lengths:
                text = " ".join("?" * l for l in word_lengths)
            elif char_count > 0:
                text = "?" * char_count
            else:
                text = ""
            avg_conf = 0.0

        needs_review = avg_conf < 0.7 or not text

        logger.info(f"OCR {field_name}: '{text}' (conf={avg_conf:.2f}, "
                     f"roster_match={bool(matched_text)})")

        return FieldResult(
            text=text,
            characters=list(text),
            avg_confidence=avg_conf,
            needs_review=needs_review,
            char_confidences=[avg_conf] * max(len(text), 1),
            box_pattern=box_pattern,
        )
