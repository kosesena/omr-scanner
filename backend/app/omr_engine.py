"""
OMR Engine v2 - Optical Mark Recognition
Reads filled answer sheets using OpenCV.

Key improvement: bubble positions are computed directly from the
form generator's layout parameters, so they match the PDF exactly.
No manual ratio calibration needed.

Pipeline:
1. Detect ArUco markers for alignment
2. Perspective correction
3. Compute exact bubble positions from form layout
4. Sample each bubble individually
5. Grade against answer key
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants matching form_generator.py ---
ARUCO_DICT_TYPE = cv2.aruco.DICT_4X4_50

# A4 page in points
PAGE_W_PT = 595.28
PAGE_H_PT = 841.89
MM = 2.8346457  # 1mm in points

# Form layout constants (must match form_generator.py)
MARGIN_PT = 14 * MM
MARKER_MARGIN_PT = 6 * MM
MARKER_SIZE_PT = 9 * MM

# Warped image dimensions (must match perspective_transform)
WARP_W = 1000
WARP_H = 1414
WARP_MARGIN = 30

# ArUco marker centers in ReportLab coords (bottom-left origin)
_marker_half = MARKER_SIZE_PT / 2
MARKERS_RL = {
    0: (MARKER_MARGIN_PT + _marker_half,
        PAGE_H_PT - MARKER_MARGIN_PT - _marker_half),  # top-left
    1: (PAGE_W_PT - MARKER_MARGIN_PT - _marker_half,
        PAGE_H_PT - MARKER_MARGIN_PT - _marker_half),  # top-right
    2: (MARKER_MARGIN_PT + _marker_half,
        MARKER_MARGIN_PT + _marker_half),               # bottom-left
    3: (PAGE_W_PT - MARKER_MARGIN_PT - _marker_half,
        MARKER_MARGIN_PT + _marker_half),               # bottom-right
}


def _rl_to_img(x_rl: float, y_rl: float,
               img_w: int = WARP_W, img_h: int = WARP_H) -> tuple:
    """Convert ReportLab coordinate (bottom-left origin) to warped image pixel (top-left origin)."""
    m = WARP_MARGIN
    # X: linear map from marker0.x..marker1.x → margin..img_w-margin
    x_frac = (x_rl - MARKERS_RL[0][0]) / (MARKERS_RL[1][0] - MARKERS_RL[0][0])
    x_img = m + x_frac * (img_w - 2 * m)
    # Y: linear map from marker0.y..marker2.y → margin..img_h-margin (flipped)
    y_frac = (MARKERS_RL[0][1] - y_rl) / (MARKERS_RL[0][1] - MARKERS_RL[2][1])
    y_img = m + y_frac * (img_h - 2 * m)
    return x_img, y_img


def _compute_bubble_positions(num_questions: int, num_options: int = 5):
    """
    Compute the exact center (in warped-image pixels) of every answer bubble,
    replicating the layout logic of form_generator.py _draw_answer_section().

    Returns:
        bubbles: dict {q_num: [(opt_idx, x_img, y_img), ...]}
        bubble_r_px: approximate bubble radius in warped image pixels
    """
    if num_questions <= 50:
        columns = 2
    else:
        columns = 4

    questions_per_col = (num_questions + columns - 1) // columns

    # --- Vertical position of answer section top ---
    title_y = PAGE_H_PT - MARKER_MARGIN_PT - MARKER_SIZE_PT - 5 * MM
    box_y = title_y - 14 * MM
    box_size = 5.5 * MM
    # 3 rows of character boxes (name, surname, student_no)
    for _ in range(3):
        box_y -= (box_size + 3 * MM)

    inst_y = box_y - 1.5 * MM
    answer_y = inst_y - 8 * MM  # y_start in _draw_answer_section

    footer_y = MARKER_MARGIN_PT + MARKER_SIZE_PT + 2.5 * MM
    y_bottom = footer_y + 6 * MM

    # --- Vertical spacing (matches form_generator.py) ---
    num_groups = (questions_per_col - 1) // 5
    available_height = answer_y - y_bottom - 8 * MM
    total_slots = questions_per_col + num_groups * 0.55
    sp_y = available_height / max(total_slots, 1)
    sp_y = min(sp_y, 20 * MM)
    sp_y = max(sp_y, 5.5 * MM)
    group_gap = sp_y * 0.55

    # --- Horizontal spacing ---
    available_width = PAGE_W_PT - 2 * MARGIN_PT
    col_width = available_width / columns
    q_num_width = 9 * MM
    col_gap = 3 * MM
    usable = col_width - q_num_width - col_gap
    sp_x = usable / num_options

    # Bubble radius
    bubble_r_pt = min(2.5 * MM, sp_x * 0.42, sp_y * 0.32)

    # --- Build bubble positions ---
    bubbles = {}

    for col_idx in range(columns):
        col_x = MARGIN_PT + col_idx * col_width
        row_y = answer_y - 3 * MM  # first bubble center y

        for row in range(questions_per_col):
            q_num = col_idx * questions_per_col + row + 1
            if q_num > num_questions:
                break

            if row > 0 and row % 5 == 0:
                row_y -= group_gap

            bubbles[q_num] = []
            for opt_idx in range(num_options):
                ox = col_x + q_num_width + opt_idx * sp_x + sp_x / 2
                oy = row_y
                x_img, y_img = _rl_to_img(ox, oy)
                bubbles[q_num].append((opt_idx, x_img, y_img))

            row_y -= sp_y

    # Convert bubble radius to pixels
    # Scale: points → pixels using the y-axis mapping
    scale = (WARP_H - 2 * WARP_MARGIN) / (MARKERS_RL[0][1] - MARKERS_RL[2][1])
    bubble_r_px = bubble_r_pt * scale

    return bubbles, bubble_r_px


def _compute_booklet_position():
    """Compute booklet A/B bubble positions in warped image."""
    title_y = PAGE_H_PT - MARKER_MARGIN_PT - MARKER_SIZE_PT - 5 * MM
    box_y = title_y - 14 * MM
    box_size = 5.5 * MM

    # After AD row
    box_y -= (box_size + 3 * MM)
    # After SOYAD row
    box_y -= (box_size + 3 * MM)
    # NO row y
    no_row_y = box_y

    # Booklet bubble positions (from form_generator.py)
    label_w = 24 * MM
    actual_no_boxes = 9  # default
    bk_x_base = MARGIN_PT + label_w + actual_no_boxes * box_size + 25 * MM

    # "KİTAPÇIK:" label width + offset
    bk_label_w = 30 * MM  # approximate

    positions = {}
    for i, bk in enumerate(["A", "B"]):
        bx = bk_x_base + bk_label_w + i * 8 * MM
        by = no_row_y + box_size * 0.4
        x_img, y_img = _rl_to_img(bx, by)
        positions[bk] = (x_img, y_img)

    return positions


@dataclass
class ScanResult:
    """Result of scanning a single answer sheet."""
    success: bool = False
    student_id: str = ""
    answers: dict = field(default_factory=dict)
    score: Optional[float] = None
    total_questions: int = 0
    correct_count: int = 0
    error: str = ""
    confidence: float = 0.0
    debug_image: Optional[np.ndarray] = None
    unmarked: list = field(default_factory=list)
    multiple_marks: list = field(default_factory=list)


class OMREngine:
    """Main OMR processing engine with exact position matching."""

    def __init__(self, num_questions: int = 40, num_options: int = 5,
                 fill_threshold: float = 0.3,
                 ambiguity_threshold: float = 0.12):
        self.num_questions = num_questions
        self.num_options = num_options
        self.fill_threshold = fill_threshold
        self.ambiguity_threshold = ambiguity_threshold

        self.aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self._tune_aruco_params()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)

        self.last_warped = None
        self.last_warped_gray = None          # CLAHE-enhanced (for bubble reading)
        self.last_warped_gray_raw = None      # Raw grayscale
        self.last_warped_normalized = None    # Shadow-removed (for OCR)

        # Pre-compute bubble positions
        self.bubbles, self.bubble_r_px = _compute_bubble_positions(
            num_questions, num_options
        )
        self.options = ["A", "B", "C", "D", "E"][:num_options]

    def _tune_aruco_params(self):
        """Optimize ArUco detection for phone camera photos."""
        p = self.aruco_params
        p.adaptiveThreshWinSizeMin = 3
        p.adaptiveThreshWinSizeMax = 30
        p.adaptiveThreshWinSizeStep = 4
        p.adaptiveThreshConstant = 7
        p.minMarkerPerimeterRate = 0.015
        p.maxMarkerPerimeterRate = 4.0
        p.polygonalApproxAccuracyRate = 0.05
        p.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

    def detect_markers(self, image: np.ndarray) -> dict:
        """Detect ArUco markers with multiple preprocessing attempts."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        best_corners, best_ids = None, None

        # Attempt 1: CLAHE enhanced
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        corners, ids, _ = self.detector.detectMarkers(enhanced)
        if ids is not None and (best_ids is None or len(ids) > len(best_ids)):
            best_corners, best_ids = corners, ids

        # Attempt 2: Original with slight blur
        if best_ids is None or len(best_ids) < 4:
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            corners, ids, _ = self.detector.detectMarkers(blurred)
            if ids is not None and (best_ids is None or len(ids) > len(best_ids)):
                best_corners, best_ids = corners, ids

        # Attempt 3: Shadow-normalized
        if best_ids is None or len(best_ids) < 4:
            blur_bg = cv2.GaussianBlur(gray, (101, 101), 0)
            blur_bg = np.maximum(blur_bg, 1).astype(np.float32)
            norm = (gray.astype(np.float32) / blur_bg * 180).clip(0, 255).astype(np.uint8)
            corners, ids, _ = self.detector.detectMarkers(norm)
            if ids is not None and (best_ids is None or len(ids) > len(best_ids)):
                best_corners, best_ids = corners, ids

        # Attempt 4: Adaptive threshold (binary)
        if best_ids is None or len(best_ids) < 4:
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 31, 10
            )
            corners, ids, _ = self.detector.detectMarkers(binary)
            if ids is not None and (best_ids is None or len(ids) > len(best_ids)):
                best_corners, best_ids = corners, ids

        # Attempt 5: Stronger CLAHE
        if best_ids is None or len(best_ids) < 4:
            clahe2 = cv2.createCLAHE(clipLimit=4.0, tileGridSize=(4, 4))
            enhanced2 = clahe2.apply(gray)
            corners, ids, _ = self.detector.detectMarkers(enhanced2)
            if ids is not None and (best_ids is None or len(ids) > len(best_ids)):
                best_corners, best_ids = corners, ids

        markers = {}
        if best_ids is not None:
            for i, mid in enumerate(best_ids.flatten()):
                markers[int(mid)] = {
                    "center": best_corners[i][0].mean(axis=0),
                    "corners": best_corners[i][0],
                }

        logger.info(f"ArUco detection: found {len(markers)} markers: {list(markers.keys())}")
        return markers

    def perspective_transform(self, image: np.ndarray, markers: dict) -> Optional[np.ndarray]:
        """Apply perspective transform using 4 ArUco markers."""
        required = [0, 1, 2, 3]
        if not all(mid in markers for mid in required):
            found = list(markers.keys())
            logger.warning(f"Missing markers. Found: {found}, need: {required}")
            return None

        src_pts = np.float32([
            markers[0]["center"],
            markers[1]["center"],
            markers[2]["center"],
            markers[3]["center"],
        ])

        dst_pts = np.float32([
            [WARP_MARGIN, WARP_MARGIN],
            [WARP_W - WARP_MARGIN, WARP_MARGIN],
            [WARP_MARGIN, WARP_H - WARP_MARGIN],
            [WARP_W - WARP_MARGIN, WARP_H - WARP_MARGIN],
        ])

        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(image, M, (WARP_W, WARP_H))
        return warped

    def _sample_bubble_intensity(self, gray: np.ndarray, cx: float, cy: float,
                                radius: float) -> float:
        """
        Sample a bubble's mean intensity from grayscale image.
        Returns mean intensity (0=black/filled, 255=white/empty).
        Uses inner ~60% of bubble radius to avoid border artifacts.
        """
        h, w = gray.shape[:2]
        # Use smaller inner radius to avoid the printed circle border
        r = max(int(radius * 0.6), 3)
        xi, yi = int(round(cx)), int(round(cy))

        y1 = max(yi - r, 0)
        y2 = min(yi + r, h)
        x1 = max(xi - r, 0)
        x2 = min(xi + r, w)

        if y2 <= y1 or x2 <= x1:
            return 255.0

        roi = gray[y1:y2, x1:x2]

        # Circular mask
        mask = np.zeros_like(roi)
        cy_local = yi - y1
        cx_local = xi - x1
        cv2.circle(mask, (cx_local, cy_local), r, 255, -1)

        # Mean intensity of pixels inside the circle
        pixels = roi[mask > 0]
        if len(pixels) == 0:
            return 255.0

        return float(np.mean(pixels))

    def read_answers(self, warped_gray: np.ndarray) -> tuple:
        """
        Read answers using intensity-based comparison.

        Instead of thresholding (which picks up printed circle outlines as noise),
        we compare the mean grayscale intensity of each bubble:
        - Filled bubble: dark (low intensity, ~50-120)
        - Empty bubble: light (high intensity, ~180-240)

        For each question, the darkest bubble is the answer IF it's significantly
        darker than the others.

        Returns: (answers_dict, unmarked, multiple_marks, confidence)
        """
        answers = {}
        unmarked = []
        multiple_marks = []
        total_conf = 0.0
        answered = 0

        sample_r = max(self.bubble_r_px, 5)

        for q_num in sorted(self.bubbles.keys()):
            # Get mean intensity for each option
            intensities = []
            for opt_idx, bx, by in self.bubbles[q_num]:
                intensity = self._sample_bubble_intensity(warped_gray, bx, by, sample_r)
                intensities.append(intensity)

            intensities = np.array(intensities)

            # Sort to find darkest (= most filled)
            sorted_indices = np.argsort(intensities)  # ascending = darkest first
            darkest_idx = sorted_indices[0]
            darkest_val = intensities[darkest_idx]

            # Mean of other (non-darkest) bubbles
            other_vals = np.delete(intensities, darkest_idx)
            other_mean = float(np.mean(other_vals))

            # Darkness gap: how much darker is the filled bubble vs unfilled ones
            # A clearly filled bubble should have a large gap
            gap = other_mean - darkest_val

            # Also check second darkest
            second_darkest_val = intensities[sorted_indices[1]]
            gap_to_second = second_darkest_val - darkest_val

            logger.debug(f"Q{q_num}: intensities={intensities.astype(int).tolist()} "
                         f"gap={gap:.0f} gap2={gap_to_second:.0f}")

            # Decision logic
            if gap < 8:
                # No bubble is significantly darker than others → unmarked
                unmarked.append(q_num)
                answers[q_num] = ""
            elif gap_to_second < 6:
                # Two bubbles are very close in darkness → multiple marks
                # But check if both are clearly dark (both filled)
                if darkest_val < 150 and second_darkest_val < 150:
                    multiple_marks.append(q_num)
                    answers[q_num] = "?"
                else:
                    # Just noise, pick the darkest
                    answers[q_num] = self.options[darkest_idx]
                    conf = min(gap / 80.0, 1.0)
                    total_conf += conf
                    answered += 1
            else:
                # Clear winner
                answers[q_num] = self.options[darkest_idx]
                conf = min(gap / 80.0, 1.0)
                total_conf += conf
                answered += 1

        confidence = total_conf / max(answered, 1)
        return answers, unmarked, multiple_marks, confidence

    def read_booklet(self, warped_gray: np.ndarray) -> str:
        """Read booklet selection (A or B) using intensity comparison."""
        try:
            positions = _compute_booklet_position()
            r = max(self.bubble_r_px, 5)
            intensities = {}
            for bk, (bx, by) in positions.items():
                intensities[bk] = self._sample_bubble_intensity(warped_gray, bx, by, r)

            # Darker = filled
            if intensities["B"] < intensities["A"] - 15:
                return "B"
            return "A"  # default
        except Exception:
            return "A"

    def grade(self, answers: dict, answer_key: dict) -> tuple:
        """Grade answers against answer key."""
        correct = 0
        total = len(answer_key)
        for q_num, correct_ans in answer_key.items():
            q = int(q_num)
            student_ans = answers.get(q, "")
            if student_ans and student_ans.upper() == correct_ans.upper():
                correct += 1
        score = (correct / total * 100) if total > 0 else 0
        return score, correct, total

    def scan(self, image: np.ndarray, answer_key: dict = None,
             debug: bool = False) -> ScanResult:
        """
        Complete scan pipeline.
        """
        result = ScanResult()

        # Step 1: Detect ArUco markers
        markers = self.detect_markers(image)
        if len(markers) < 4:
            missing = [m for m in [0, 1, 2, 3] if m not in markers]
            pos_names = {0: "sol üst", 1: "sağ üst", 2: "sol alt", 3: "sağ alt"}
            missing_str = ", ".join(f"{m} ({pos_names.get(m, '')})" for m in missing)
            result.error = (f"4 köşe işaretçisinden {4-len(markers)} tanesi bulunamadı: {missing_str}. "
                           f"Formu düz bir yüzeyde, iyi aydınlatılmış ortamda, tüm köşeler görünecek şekilde çekin.")
            return result

        logger.info(f"Found {len(markers)} ArUco markers: {list(markers.keys())}")

        # Step 2: Perspective transform
        warped = self.perspective_transform(image, markers)
        if warped is None:
            result.error = "Perspektif düzeltme başarısız"
            return result

        # Convert to grayscale
        if len(warped.shape) == 3:
            warped_gray_raw = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        else:
            warped_gray_raw = warped.copy()

        # Shadow removal: estimate local lighting with large blur, then normalize
        # This makes bubbles look the same whether in shadow or not
        blur = cv2.GaussianBlur(warped_gray_raw, (101, 101), 0)
        blur = np.maximum(blur, 1).astype(np.float32)
        # Divide by local mean → flat lighting; multiply by 200 to get nice range
        normalized = (warped_gray_raw.astype(np.float32) / blur * 200).clip(0, 255).astype(np.uint8)

        # CLAHE for bubble reading
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        warped_gray = clahe.apply(normalized)

        # Store all versions
        self.last_warped = warped
        self.last_warped_gray = warped_gray          # CLAHE (for bubbles)
        self.last_warped_gray_raw = warped_gray_raw  # Raw grayscale
        self.last_warped_normalized = normalized      # Shadow-removed (for OCR)

        # Step 3: Read answers (exact positions)
        answers, unmarked, multi, confidence = self.read_answers(warped_gray)
        result.answers = answers
        result.unmarked = unmarked
        result.multiple_marks = multi
        result.confidence = confidence
        result.student_id = ""  # Student ID is read by OCR, not bubbles

        logger.info(f"Read {len(answers)} answers, "
                     f"{len(unmarked)} unmarked, {len(multi)} multiple, "
                     f"confidence: {confidence:.2f}")

        # Step 4: Grade if answer key provided
        if answer_key:
            score, correct, total = self.grade(answers, answer_key)
            result.score = score
            result.correct_count = correct
            result.total_questions = total
            logger.info(f"Score: {correct}/{total} = {score:.1f}%")

        result.success = True

        # Debug visualization
        if debug and warped is not None and len(warped.shape) == 3:
            result.debug_image = self._create_debug_image(
                warped, answers, answer_key
            )

        return result

    def _create_debug_image(self, warped: np.ndarray, answers: dict,
                            answer_key: dict = None) -> np.ndarray:
        """Create annotated debug image showing detected bubbles."""
        debug_img = warped.copy()

        for q_num, bubble_list in self.bubbles.items():
            ans = answers.get(q_num, "")
            for opt_idx, bx, by in bubble_list:
                xi, yi = int(bx), int(by)
                r = int(self.bubble_r_px)

                if ans and ans != "?" and opt_idx == self.options.index(ans):
                    if answer_key:
                        correct_ans = answer_key.get(str(q_num),
                                                     answer_key.get(q_num, ""))
                        color = (0, 200, 0) if ans.upper() == str(correct_ans).upper() else (0, 0, 200)
                    else:
                        color = (200, 150, 0)
                    cv2.circle(debug_img, (xi, yi), r, color, 2)
                else:
                    cv2.circle(debug_img, (xi, yi), r, (180, 180, 180), 1)

        return debug_img

    def scan_from_file(self, image_path: str, answer_key: dict = None,
                       debug: bool = False) -> ScanResult:
        """Convenience method to scan from file path."""
        image = cv2.imread(image_path)
        if image is None:
            result = ScanResult()
            result.error = f"Dosya okunamadı: {image_path}"
            return result
        return self.scan(image, answer_key, debug)


# --- Calibration helper ---
def calibrate_from_image(image_path: str, num_questions: int = 40,
                         num_options: int = 5):
    """
    Visualize bubble detection regions on a sample image.
    Saves a debug image showing where each bubble is expected.
    """
    engine = OMREngine(num_questions=num_questions, num_options=num_options)
    image = cv2.imread(image_path)

    if image is None:
        print(f"Cannot read: {image_path}")
        return

    markers = engine.detect_markers(image)
    print(f"Found markers: {list(markers.keys())}")

    if len(markers) < 4:
        print("Need 4 markers for calibration!")
        return

    warped = engine.perspective_transform(image, markers)
    if warped is None:
        print("Transform failed!")
        return

    debug_img = warped.copy()

    # Draw all expected bubble positions
    for q_num, bubble_list in engine.bubbles.items():
        for opt_idx, bx, by in bubble_list:
            xi, yi = int(bx), int(by)
            r = int(engine.bubble_r_px)
            cv2.circle(debug_img, (xi, yi), r, (0, 255, 0), 1)
            if opt_idx == 0:
                cv2.putText(debug_img, str(q_num), (xi - 30, yi + 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

    output_path = image_path.replace(".", "_calibration.")
    cv2.imwrite(output_path, debug_img)
    print(f"Calibration image saved: {output_path}")
    return debug_img


if __name__ == "__main__":
    engine = OMREngine(num_questions=20, num_options=5)
    print(f"OMR Engine initialized: {engine.num_questions} questions")
    print(f"Bubble radius: {engine.bubble_r_px:.1f}px")
    print(f"Total bubbles: {sum(len(v) for v in engine.bubbles.values())}")

    # Print some sample positions
    for q in [1, 5, 10, 15, 20]:
        if q in engine.bubbles:
            pos = engine.bubbles[q]
            print(f"  Q{q}: A=({pos[0][1]:.0f},{pos[0][2]:.0f}) "
                  f"E=({pos[-1][1]:.0f},{pos[-1][2]:.0f})")
