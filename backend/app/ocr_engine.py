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

WARP_W = 1500
WARP_H = 2121
WARP_MARGIN = 45

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

        # Step 1: Upscale to ~180px tall (increased from 120 for better OCR)
        target_h = 180
        scale = max(target_h / max(inner.shape[0], 1), 4)
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

    def _ocr_single_digit(self, processed: np.ndarray, config: str) -> tuple:
        """Run Tesseract on a preprocessed digit image. Returns (digit, confidence)."""
        try:
            text = pytesseract.image_to_string(processed, lang="eng", config=config).strip()
            if text and text[0].isdigit():
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
        except Exception:
            pass
        return ("?", 0.0)

    def _read_digit(self, cell: np.ndarray) -> tuple:
        """Read a single digit using consensus of two preprocessing strategies.
        If both agree -> high confidence. If they disagree -> return '?' for roster matching."""
        if not HAS_TESSERACT:
            return ("?", 0.0)

        config = "--psm 10 --oem 3 -c tessedit_char_whitelist=0123456789"

        # Strategy A: Adaptive threshold (good for uneven lighting)
        digit_a, conf_a = "?", 0.0
        processed_a = self._preprocess_digit(cell)
        if processed_a is not None:
            digit_a, conf_a = self._ocr_single_digit(processed_a, config)

        # Strategy B: Otsu threshold + higher upscale (good for clean images)
        digit_b, conf_b = "?", 0.0
        inner = self._get_inner(cell, margin_frac=0.20)
        if inner is not None and inner.size > 0:
            scale = max(250 / max(inner.shape[0], 1), 5)
            big = cv2.resize(inner, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_CUBIC)
            blurred = cv2.GaussianBlur(big, (5, 5), 0)
            _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            border = 25
            padded = cv2.copyMakeBorder(binary, border, border, border, border,
                                         cv2.BORDER_CONSTANT, value=255)
            digit_b, conf_b = self._ocr_single_digit(padded, config)

        # Consensus logic
        if digit_a != "?" and digit_b != "?" and digit_a == digit_b:
            # Both strategies agree — high confidence
            return (digit_a, max(conf_a, conf_b))

        if digit_a != "?" and digit_b != "?" and digit_a != digit_b:
            # Strategies disagree — uncertain, return '?' so roster matching can fix it
            logger.info(f"Digit disagreement: A='{digit_a}'({conf_a:.0%}) vs B='{digit_b}'({conf_b:.0%}) -> '?'")
            return ("?", 0.0)

        # One succeeded, the other didn't
        if digit_a != "?":
            return (digit_a, conf_a)
        if digit_b != "?":
            return (digit_b, conf_b)

        return ("?", 0.0)

    def _preprocess_letter_adaptive(self, cell: np.ndarray) -> Optional[np.ndarray]:
        """Strategy A: Adaptive threshold preprocessing for letters."""
        if cell is None or cell.size == 0:
            return None

        inner = self._get_inner(cell, margin_frac=0.20)
        if inner is None:
            return None

        # Upscale to ~200px tall (was 120 — higher res helps Tesseract)
        target_h = 200
        scale = max(target_h / max(inner.shape[0], 1), 4)
        big = cv2.resize(inner, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

        # Normalize contrast
        min_v, max_v = float(np.min(big)), float(np.max(big))
        if max_v - min_v > 20:
            normalized = ((big.astype(float) - min_v) / (max_v - min_v) * 255).astype(np.uint8)
        else:
            normalized = big

        # Gaussian blur
        blurred = cv2.GaussianBlur(normalized, (3, 3), 0)

        # Adaptive threshold
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 21, 8
        )

        # Morphological close
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        # White border
        border = 25
        padded = cv2.copyMakeBorder(binary, border, border, border, border,
                                     cv2.BORDER_CONSTANT, value=255)
        return padded

    def _preprocess_letter_otsu(self, cell: np.ndarray) -> Optional[np.ndarray]:
        """Strategy B: Otsu threshold + higher upscale for letters."""
        if cell is None or cell.size == 0:
            return None

        inner = self._get_inner(cell, margin_frac=0.20)
        if inner is None or inner.size == 0:
            return None

        # Higher upscale for Otsu strategy
        scale = max(250 / max(inner.shape[0], 1), 5)
        big = cv2.resize(inner, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

        blurred = cv2.GaussianBlur(big, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological close to fill gaps in strokes
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        border = 30
        padded = cv2.copyMakeBorder(binary, border, border, border, border,
                                     cv2.BORDER_CONSTANT, value=255)
        return padded

    def _ocr_single_letter(self, processed: np.ndarray, config: str, lang: str = "tur") -> tuple:
        """Run Tesseract on a preprocessed letter image. Returns (letter, confidence)."""
        try:
            text = pytesseract.image_to_string(processed, lang=lang, config=config).strip()

            if not text:
                # Fallback: try with eng
                text = pytesseract.image_to_string(processed, lang="eng", config=config).strip()

            if text and text[0].isalpha():
                data = pytesseract.image_to_data(
                    processed, lang=lang, config=config,
                    output_type=pytesseract.Output.DICT
                )
                conf = 0.0
                for i, t in enumerate(data["text"]):
                    if t.strip():
                        c = int(data["conf"][i])
                        if c > conf:
                            conf = c
                return (text[0].upper(), conf / 100.0)
        except Exception as e:
            logger.warning(f"Tesseract letter error: {e}")
        return ("?", 0.0)

    def _read_letter(self, cell: np.ndarray) -> tuple:
        """Read a single letter using dual-strategy consensus (like _read_digit).
        If both strategies agree -> high confidence. If they disagree -> lower confidence."""
        if not HAS_TESSERACT:
            return ("?", 0.0)

        config = "--psm 10 --oem 3 -c tessedit_char_whitelist=ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZabcçdefgğhıijklmnoöprsştuüvyz"

        # Strategy A: Adaptive threshold
        letter_a, conf_a = "?", 0.0
        processed_a = self._preprocess_letter_adaptive(cell)
        if processed_a is not None:
            letter_a, conf_a = self._ocr_single_letter(processed_a, config, "tur")

        # Strategy B: Otsu threshold + higher upscale
        letter_b, conf_b = "?", 0.0
        processed_b = self._preprocess_letter_otsu(cell)
        if processed_b is not None:
            letter_b, conf_b = self._ocr_single_letter(processed_b, config, "tur")

        # Consensus logic
        if letter_a != "?" and letter_b != "?" and letter_a == letter_b:
            # Both strategies agree — high confidence
            return (letter_a, max(conf_a, conf_b))

        if letter_a != "?" and letter_b != "?" and letter_a != letter_b:
            # Strategies disagree — pick higher confidence but reduce it
            logger.info(f"Letter disagreement: A='{letter_a}'({conf_a:.0%}) vs B='{letter_b}'({conf_b:.0%})")
            if conf_a >= conf_b:
                return (letter_a, conf_a * 0.7)
            else:
                return (letter_b, conf_b * 0.7)

        # One succeeded, the other didn't
        if letter_a != "?":
            return (letter_a, conf_a)
        if letter_b != "?":
            return (letter_b, conf_b)

        return ("?", 0.0)

    def _read_name_strip(self, warped_gray: np.ndarray,
                          field_name: str,
                          filled_info: list) -> tuple:
        """Read name/surname by joining filled boxes into a strip and using word-mode Tesseract.
        This is more accurate than per-character reading for handwritten text.
        Returns (text, confidence)."""
        boxes = CHAR_BOX_POSITIONS.get(field_name, [])

        # Find first and last filled box
        first_filled = -1
        last_filled = -1
        for idx, is_filled, _ in filled_info:
            if is_filled:
                if first_filled < 0:
                    first_filled = idx
                last_filled = idx

        if first_filled < 0:
            return ("", 0.0)

        # Build word groups (split by empty boxes)
        word_groups = []
        current_word_boxes = []
        for idx, is_filled, _ in filled_info:
            if idx < first_filled or idx > last_filled:
                continue
            if is_filled:
                current_word_boxes.append(boxes[idx])
            else:
                if current_word_boxes:
                    word_groups.append(current_word_boxes)
                    current_word_boxes = []
        if current_word_boxes:
            word_groups.append(current_word_boxes)

        if not word_groups:
            return ("", 0.0)

        config = "--psm 7 --oem 3 -c tessedit_char_whitelist=ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZabcçdefgğhıijklmnoöprsştuüvyz "

        words = []
        total_conf = 0.0
        word_count = 0

        for group_boxes in word_groups:
            # Merge boxes into a single strip image
            x1 = min(b[0] for b in group_boxes)
            y1 = min(b[1] for b in group_boxes)
            x2 = max(b[2] for b in group_boxes)
            y2 = max(b[3] for b in group_boxes)

            h, w = warped_gray.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)

            strip = warped_gray[y1:y2, x1:x2]
            if strip.size == 0:
                continue

            # Upscale the strip
            target_h = 80
            scale = max(target_h / max(strip.shape[0], 1), 3)
            big = cv2.resize(strip, None, fx=scale, fy=scale,
                              interpolation=cv2.INTER_CUBIC)

            # Normalize contrast
            min_v, max_v = float(np.min(big)), float(np.max(big))
            if max_v - min_v > 20:
                normalized = ((big.astype(float) - min_v) / (max_v - min_v) * 255).astype(np.uint8)
            else:
                normalized = big

            blurred = cv2.GaussianBlur(normalized, (3, 3), 0)
            binary = cv2.adaptiveThreshold(
                blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 21, 8
            )

            # Add border
            border = 20
            padded = cv2.copyMakeBorder(binary, border, border, border, border,
                                         cv2.BORDER_CONSTANT, value=255)

            try:
                text = pytesseract.image_to_string(padded, lang="tur", config=config).strip()
                if text:
                    # Clean up: keep only letters and spaces
                    cleaned = "".join(c for c in text if c.isalpha() or c == " ").strip().upper()
                    if cleaned:
                        words.append(cleaned)
                        # Get confidence
                        data = pytesseract.image_to_data(
                            padded, lang="tur", config=config,
                            output_type=pytesseract.Output.DICT
                        )
                        confs = [int(c) for c, t in zip(data["conf"], data["text"])
                                 if t.strip() and int(c) > 0]
                        if confs:
                            total_conf += sum(confs) / len(confs)
                            word_count += 1
            except Exception as e:
                logger.warning(f"Strip OCR error: {e}")

        result_text = " ".join(words)
        avg_conf = (total_conf / max(word_count, 1)) / 100.0

        logger.info(f"OCR strip {field_name}: '{result_text}' (conf={avg_conf:.2f})")
        return (result_text, avg_conf)

    def _read_name_with_tesseract(self, warped_gray: np.ndarray,
                                    field_name: str,
                                    filled_info: list) -> tuple:
        """Read name/surname using both strip and per-character approaches.
        Returns the better result."""
        boxes = CHAR_BOX_POSITIONS.get(field_name, [])

        # Approach 1: Strip reading (word mode — better for connected handwriting)
        strip_text, strip_conf = self._read_name_strip(warped_gray, field_name, filled_info)

        # Approach 2: Per-character reading (single char mode — better for printed letters)
        characters = []
        confidences = []
        for idx, is_filled, ink_score in filled_info:
            if not is_filled:
                remaining_filled = any(f for _, f, _ in filled_info[idx + 1:])
                if not remaining_filled:
                    break
                if characters and characters[-1] != " ":
                    characters.append(" ")
                    confidences.append(1.0)
                continue

            cell = self._extract_box(warped_gray, boxes[idx])
            letter, conf = self._read_letter(cell)
            characters.append(letter)
            confidences.append(conf)

        char_text = "".join(characters).strip()
        char_conf = sum(confidences) / max(len(confidences), 1)

        logger.info(f"OCR Tesseract {field_name}: strip='{strip_text}'({strip_conf:.2f}) "
                     f"char='{char_text}'({char_conf:.2f})")

        # Pick the better result
        # Prefer strip if it has decent confidence (word context helps)
        if strip_text and strip_conf > char_conf and strip_conf >= 0.3:
            return (strip_text, strip_conf)
        elif char_text and "?" not in char_text:
            return (char_text, char_conf)
        elif strip_text:
            return (strip_text, strip_conf)
        else:
            return (char_text, char_conf)

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

    def _read_student_no_strip(self, warped_gray: np.ndarray, boxes: list) -> tuple:
        """Read all 9 digit boxes as a single strip using Tesseract word mode.
        Returns (text, confidence). More reliable than per-digit for connected writing."""
        if not HAS_TESSERACT or not boxes:
            return ("", 0.0)

        # Merge all 9 boxes into one strip
        x1 = min(b[0] for b in boxes)
        y1 = min(b[1] for b in boxes)
        x2 = max(b[2] for b in boxes)
        y2 = max(b[3] for b in boxes)

        h, w = warped_gray.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        strip = warped_gray[y1:y2, x1:x2]
        if strip.size == 0:
            return ("", 0.0)

        # Upscale
        target_h = 100
        scale = max(target_h / max(strip.shape[0], 1), 3)
        big = cv2.resize(strip, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

        # Normalize
        min_v, max_v = float(np.min(big)), float(np.max(big))
        if max_v - min_v > 20:
            normalized = ((big.astype(float) - min_v) / (max_v - min_v) * 255).astype(np.uint8)
        else:
            normalized = big

        blurred = cv2.GaussianBlur(normalized, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 21, 8
        )

        border = 20
        padded = cv2.copyMakeBorder(binary, border, border, border, border,
                                     cv2.BORDER_CONSTANT, value=255)

        config = "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789"
        try:
            text = pytesseract.image_to_string(padded, lang="eng", config=config).strip()
            # Keep only digits
            digits = "".join(c for c in text if c.isdigit())

            if digits:
                data = pytesseract.image_to_data(
                    padded, lang="eng", config=config,
                    output_type=pytesseract.Output.DICT
                )
                confs = [int(c) for c, t in zip(data["conf"], data["text"])
                         if t.strip() and int(c) > 0]
                avg_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.3
                logger.info(f"OCR student_no strip: '{digits}' (conf={avg_conf:.2f})")
                return (digits, avg_conf)
        except Exception as e:
            logger.warning(f"Strip digit OCR error: {e}")

        return ("", 0.0)

    def _read_student_no(self, warped_gray: np.ndarray, boxes: list,
                          filled_info: list, box_pattern: list) -> FieldResult:
        """Read student number using per-digit Tesseract + strip reading.
        All 9 boxes are always read (student numbers are always 9 digits)."""

        # Approach 1: Per-digit reading (existing dual-strategy consensus)
        characters = []
        confidences = []
        for idx in range(len(boxes)):
            cell = self._extract_box(warped_gray, boxes[idx])
            digit, conf = self._read_digit(cell)
            characters.append(digit)
            confidences.append(conf)

        per_digit_text = "".join(characters)
        per_digit_conf = sum(confidences) / max(len(confidences), 1)

        # Approach 2: Strip reading (all 9 digits as one image)
        strip_text, strip_conf = self._read_student_no_strip(warped_gray, boxes)

        # Merge: use strip to fill in '?' gaps from per-digit
        text = per_digit_text
        avg_conf = per_digit_conf

        if strip_text and len(strip_text) == 9:
            if "?" in per_digit_text:
                # Fill '?' positions with strip digits
                merged = list(per_digit_text)
                for i in range(min(len(merged), len(strip_text))):
                    if merged[i] == "?":
                        merged[i] = strip_text[i]
                        confidences[i] = strip_conf
                text = "".join(merged)
                avg_conf = sum(confidences) / max(len(confidences), 1)
                logger.info(f"OCR student_no: merged per-digit '{per_digit_text}' + strip '{strip_text}' -> '{text}'")
            elif per_digit_conf < strip_conf:
                # Strip is more confident overall
                text = strip_text
                avg_conf = strip_conf
                confidences = [strip_conf] * 9

        # Try roster matching for remaining '?'
        if "?" in text and self._roster_students:
            matched = self._match_student_no_roster(text)
            if matched:
                logger.info(f"OCR student_no: roster matched '{text}' -> '{matched}'")
                text = matched
                avg_conf = max(avg_conf, 0.7)
                confidences = [0.7] * len(text)

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
        """Read name/surname field using box pattern + roster matching + Tesseract fallback."""

        # Try roster matching first (use student_no hint if available)
        matched_text, match_conf = self._match_roster_name(
            field_name, pattern_str, char_count, word_lengths,
            student_no=self._last_student_no
        )

        if matched_text and match_conf >= 0.5:
            text = matched_text
            avg_conf = match_conf
        else:
            # No roster match — try Tesseract character-by-character
            tess_text, tess_conf = self._read_name_with_tesseract(
                warped_gray, field_name, filled_info
            )
            if tess_text and tess_conf > 0.1:
                text = tess_text
                avg_conf = tess_conf
            else:
                # Final fallback — show pattern with ?
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
