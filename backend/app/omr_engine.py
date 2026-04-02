"""
OMR Engine - Optical Mark Recognition
Reads filled answer sheets using OpenCV:
1. Detect ArUco markers for alignment
2. Perspective correction (handles tilted/angled photos)
3. Extract student ID from bubble grid
4. Extract answers from bubble grid
5. Grade against answer key
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Configuration ---
ARUCO_DICT_TYPE = cv2.aruco.DICT_4X4_50

# These ratios define where bubbles are on the form, relative to the
# area bounded by the 4 ArUco markers. Adjust if form layout changes.
# All values are ratios (0.0 - 1.0) of the warped image dimensions.

FORM_CONFIG = {
    "student_id": {
        "num_digits": 10,
        "num_choices": 10,  # 0-9
        "top": 0.145,       # top of first bubble row
        "bottom": 0.42,     # bottom of last bubble row
        "left": 0.055,      # left of first column
        "right": 0.52,      # right of last column
    },
    "answers": {
        "num_options": 5,  # A-B-C-D-E
        "options": ["A", "B", "C", "D", "E"],
    }
}

# Answer section layout ratios for different question counts
# (top, bottom, left, right, columns, questions_per_col)
ANSWER_LAYOUTS = {
    20: {
        "top": 0.48, "bottom": 0.92,
        "left": 0.04, "right": 0.96,
        "columns": 2,
    },
    40: {
        "top": 0.48, "bottom": 0.92,
        "left": 0.04, "right": 0.96,
        "columns": 4,
    },
    100: {
        "top": 0.48, "bottom": 0.95,
        "left": 0.04, "right": 0.96,
        "columns": 5,
    },
}


@dataclass
class ScanResult:
    """Result of scanning a single answer sheet."""
    success: bool = False
    student_id: str = ""
    answers: dict = field(default_factory=dict)  # {question_num: "A"/"B"/...}
    score: Optional[float] = None
    total_questions: int = 0
    correct_count: int = 0
    error: str = ""
    confidence: float = 0.0
    debug_image: Optional[np.ndarray] = None
    unmarked: list = field(default_factory=list)  # questions with no answer
    multiple_marks: list = field(default_factory=list)  # questions with >1 answer


class OMREngine:
    """Main OMR processing engine."""

    def __init__(self, num_questions: int = 40, fill_threshold: float = 0.35,
                 ambiguity_threshold: float = 0.15):
        """
        Args:
            num_questions: Expected number of questions on the form
            fill_threshold: Minimum fill ratio to consider a bubble marked
            ambiguity_threshold: Minimum difference between top-2 bubbles
        """
        self.num_questions = num_questions
        self.fill_threshold = fill_threshold
        self.ambiguity_threshold = ambiguity_threshold
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)
        self.aruco_params = cv2.aruco.DetectorParameters()

        # Optimize detection parameters
        self.aruco_params.adaptiveThreshWinSizeMin = 3
        self.aruco_params.adaptiveThreshWinSizeMax = 23
        self.aruco_params.adaptiveThreshWinSizeStep = 5
        self.aruco_params.adaptiveThreshConstant = 7
        self.aruco_params.minMarkerPerimeterRate = 0.02
        self.aruco_params.maxMarkerPerimeterRate = 4.0
        self.aruco_params.polygonalApproxAccuracyRate = 0.05
        self.aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX

        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        self.last_warped_gray = None  # stored for OCR after scan

        # Get answer layout
        self._setup_answer_layout()

    def _setup_answer_layout(self):
        """Setup answer section layout based on num_questions."""
        # Find closest layout
        layout_key = min(ANSWER_LAYOUTS.keys(), key=lambda k: abs(k - self.num_questions))
        self.answer_layout = ANSWER_LAYOUTS[layout_key]
        self.answer_layout["questions_per_col"] = (
            (self.num_questions + self.answer_layout["columns"] - 1)
            // self.answer_layout["columns"]
        )

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for better detection."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # Mild denoise
        gray = cv2.GaussianBlur(gray, (3, 3), 0)

        # CLAHE for contrast enhancement (handles varying lighting)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        return gray

    def detect_markers(self, image: np.ndarray) -> dict:
        """
        Detect ArUco markers and return their centers.
        Returns dict: {marker_id: center_point}
        """
        gray = self.preprocess_image(image)
        corners, ids, rejected = self.detector.detectMarkers(gray)

        markers = {}
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                # Get center of marker
                center = corners[i][0].mean(axis=0)
                markers[int(marker_id)] = {
                    "center": center,
                    "corners": corners[i][0]
                }

        return markers

    def perspective_transform(self, image: np.ndarray, markers: dict) -> Optional[np.ndarray]:
        """
        Apply perspective transform using 4 ArUco markers.
        Markers: 0=top-left, 1=top-right, 2=bottom-left, 3=bottom-right
        """
        required = [0, 1, 2, 3]
        if not all(mid in markers for mid in required):
            found = list(markers.keys())
            logger.warning(f"Missing markers. Found: {found}, need: {required}")
            return None

        # Source points (detected marker centers)
        src_pts = np.float32([
            markers[0]["center"],  # top-left
            markers[1]["center"],  # top-right
            markers[2]["center"],  # bottom-left
            markers[3]["center"],  # bottom-right
        ])

        # Destination: standard A4 aspect ratio, fixed size
        dst_w, dst_h = 1000, 1414  # A4 ratio
        margin = 30
        dst_pts = np.float32([
            [margin, margin],
            [dst_w - margin, margin],
            [margin, dst_h - margin],
            [dst_w - margin, dst_h - margin],
        ])

        # Compute and apply transform
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(image, M, (dst_w, dst_h))

        return warped

    def extract_bubble_grid(self, warped_gray: np.ndarray,
                            top: float, bottom: float,
                            left: float, right: float,
                            rows: int, cols: int) -> np.ndarray:
        """
        Extract fill ratios from a bubble grid region.
        Returns array of shape (rows, cols) with fill ratios.
        """
        h, w = warped_gray.shape[:2]

        # Region of interest
        y1, y2 = int(h * top), int(h * bottom)
        x1, x2 = int(w * left), int(w * right)
        roi = warped_gray[y1:y2, x1:x2]

        # Adaptive threshold (handles varying lighting)
        thresh = cv2.adaptiveThreshold(
            roi, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 8
        )

        # Calculate cell dimensions
        cell_h = thresh.shape[0] / rows
        cell_w = thresh.shape[1] / cols

        fill_ratios = np.zeros((rows, cols))

        for r in range(rows):
            for c_idx in range(cols):
                # Cell boundaries
                cy1 = int(r * cell_h)
                cy2 = int((r + 1) * cell_h)
                cx1 = int(c_idx * cell_w)
                cx2 = int((c_idx + 1) * cell_w)

                cell = thresh[cy1:cy2, cx1:cx2]

                if cell.size == 0:
                    continue

                # Focus on center of cell (ignore edges/borders)
                pad_y = max(int(cell.shape[0] * 0.2), 2)
                pad_x = max(int(cell.shape[1] * 0.2), 2)
                inner = cell[pad_y:-pad_y, pad_x:-pad_x]

                if inner.size == 0:
                    continue

                # Create circular mask (bubbles are round)
                mask = np.zeros_like(inner)
                center = (inner.shape[1] // 2, inner.shape[0] // 2)
                radius = min(center) - 1
                if radius > 0:
                    cv2.circle(mask, center, radius, 255, -1)
                    masked = cv2.bitwise_and(inner, mask)
                    fill_ratios[r, c_idx] = np.sum(masked > 0) / max(np.sum(mask > 0), 1)
                else:
                    fill_ratios[r, c_idx] = np.sum(inner > 0) / inner.size

        return fill_ratios

    def read_student_id(self, warped_gray: np.ndarray) -> tuple:
        """
        Read student ID from bubble grid.
        Returns: (student_id_string, confidence)
        """
        config = FORM_CONFIG["student_id"]
        num_digits = config["num_digits"]
        num_choices = config["num_choices"]

        fill_ratios = self.extract_bubble_grid(
            warped_gray,
            top=config["top"], bottom=config["bottom"],
            left=config["left"], right=config["right"],
            rows=num_choices, cols=num_digits
        )

        student_id = ""
        total_conf = 0

        for col in range(num_digits):
            col_fills = fill_ratios[:, col]
            max_idx = np.argmax(col_fills)
            max_fill = col_fills[max_idx]

            if max_fill < self.fill_threshold * 0.8:
                student_id += "?"
                continue

            # Check ambiguity
            sorted_fills = np.sort(col_fills)[::-1]
            if len(sorted_fills) > 1:
                diff = sorted_fills[0] - sorted_fills[1]
                if diff < self.ambiguity_threshold * 0.5:
                    student_id += "?"
                    continue

            student_id += str(max_idx)
            total_conf += max_fill

        confidence = total_conf / max(num_digits, 1)
        return student_id, confidence

    def read_answers(self, warped_gray: np.ndarray) -> tuple:
        """
        Read answers from bubble grid.
        Returns: (answers_dict, unmarked_list, multiple_marks_list, confidence)
        """
        layout = self.answer_layout
        options = FORM_CONFIG["answers"]["options"]
        num_options = len(options)
        columns = layout["columns"]
        qpc = layout["questions_per_col"]

        h, w = warped_gray.shape[:2]
        answers = {}
        unmarked = []
        multiple_marks = []
        total_conf = 0
        answered_count = 0

        for col_idx in range(columns):
            # Calculate this column's region
            col_width_ratio = (layout["right"] - layout["left"]) / columns
            col_left = layout["left"] + col_idx * col_width_ratio
            col_right = col_left + col_width_ratio

            # Offset for question number label area (~15% of column width)
            bubble_left = col_left + col_width_ratio * 0.2
            bubble_right = col_right - col_width_ratio * 0.02

            fill_ratios = self.extract_bubble_grid(
                warped_gray,
                top=layout["top"], bottom=layout["bottom"],
                left=bubble_left, right=bubble_right,
                rows=qpc, cols=num_options
            )

            for row in range(qpc):
                q_num = col_idx * qpc + row + 1
                if q_num > self.num_questions:
                    break

                row_fills = fill_ratios[row]
                max_idx = np.argmax(row_fills)
                max_fill = row_fills[max_idx]

                # Count how many bubbles are significantly filled
                filled_count = np.sum(row_fills > self.fill_threshold)

                if max_fill < self.fill_threshold:
                    # No answer marked
                    unmarked.append(q_num)
                    answers[q_num] = ""
                elif filled_count > 1:
                    # Check if there's a clear winner
                    sorted_fills = np.sort(row_fills)[::-1]
                    diff = sorted_fills[0] - sorted_fills[1]
                    if diff > self.ambiguity_threshold:
                        # Clear winner despite multiple marks
                        answers[q_num] = options[max_idx]
                        total_conf += max_fill
                        answered_count += 1
                    else:
                        # Truly ambiguous
                        multiple_marks.append(q_num)
                        answers[q_num] = "?"
                else:
                    answers[q_num] = options[max_idx]
                    total_conf += max_fill
                    answered_count += 1

        confidence = total_conf / max(answered_count, 1)
        return answers, unmarked, multiple_marks, confidence

    def grade(self, answers: dict, answer_key: dict) -> tuple:
        """
        Grade answers against answer key.
        Returns: (score, correct_count, total)
        """
        correct = 0
        total = len(answer_key)

        for q_num, correct_ans in answer_key.items():
            q_num = int(q_num)
            student_ans = answers.get(q_num, "")
            if student_ans.upper() == correct_ans.upper():
                correct += 1

        score = (correct / total * 100) if total > 0 else 0
        return score, correct, total

    def scan(self, image: np.ndarray, answer_key: dict = None,
             debug: bool = False) -> ScanResult:
        """
        Complete scan pipeline: detect → transform → read → grade.

        Args:
            image: Input image (BGR or grayscale)
            answer_key: Optional dict {question_num: correct_answer}
            debug: If True, include debug visualization

        Returns:
            ScanResult with all extracted data
        """
        result = ScanResult()

        # Step 1: Detect ArUco markers
        markers = self.detect_markers(image)
        if len(markers) < 4:
            result.error = f"Could not find all 4 markers. Found {len(markers)}: {list(markers.keys())}"
            return result

        logger.info(f"Found {len(markers)} ArUco markers")

        # Step 2: Perspective transform
        warped = self.perspective_transform(image, markers)
        if warped is None:
            result.error = "Perspective transform failed"
            return result

        # Convert to grayscale for processing
        if len(warped.shape) == 3:
            warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        else:
            warped_gray = warped

        # Enhance contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        warped_gray = clahe.apply(warped_gray)

        # Store for OCR engine
        self.last_warped_gray = warped_gray

        # Step 3: Read student ID
        student_id, id_conf = self.read_student_id(warped_gray)
        result.student_id = student_id
        logger.info(f"Student ID: {student_id} (confidence: {id_conf:.2f})")

        # Step 4: Read answers
        answers, unmarked, multiple_marks, ans_conf = self.read_answers(warped_gray)
        result.answers = answers
        result.unmarked = unmarked
        result.multiple_marks = multiple_marks
        result.confidence = (id_conf + ans_conf) / 2

        # Step 5: Grade if answer key provided
        if answer_key:
            score, correct, total = self.grade(answers, answer_key)
            result.score = score
            result.correct_count = correct
            result.total_questions = total

        result.success = True

        # Debug visualization
        if debug and len(warped.shape) == 3:
            result.debug_image = self._create_debug_image(warped, answers, answer_key)

        return result

    def _create_debug_image(self, warped: np.ndarray, answers: dict,
                            answer_key: dict = None) -> np.ndarray:
        """Create annotated debug image showing detected bubbles."""
        debug_img = warped.copy()
        h, w = debug_img.shape[:2]

        layout = self.answer_layout
        options = FORM_CONFIG["answers"]["options"]
        columns = layout["columns"]
        qpc = layout["questions_per_col"]

        for col_idx in range(columns):
            col_width_ratio = (layout["right"] - layout["left"]) / columns
            col_left = layout["left"] + col_idx * col_width_ratio
            bubble_left = col_left + col_width_ratio * 0.2
            bubble_right = col_left + col_width_ratio - col_width_ratio * 0.02

            for row in range(qpc):
                q_num = col_idx * qpc + row + 1
                if q_num > self.num_questions:
                    break

                ans = answers.get(q_num, "")
                if ans and ans != "?" and ans in options:
                    opt_idx = options.index(ans)
                    # Calculate bubble position
                    bx1 = int(w * bubble_left)
                    bx2 = int(w * bubble_right)
                    by1 = int(h * layout["top"])
                    by2 = int(h * layout["bottom"])

                    cell_w = (bx2 - bx1) / len(options)
                    cell_h = (by2 - by1) / qpc

                    cx = int(bx1 + (opt_idx + 0.5) * cell_w)
                    cy = int(by1 + (row + 0.5) * cell_h)

                    # Color: green if correct, red if wrong, blue if no key
                    if answer_key:
                        correct_ans = answer_key.get(str(q_num), answer_key.get(q_num, ""))
                        color = (0, 200, 0) if ans.upper() == correct_ans.upper() else (0, 0, 200)
                    else:
                        color = (200, 150, 0)

                    cv2.circle(debug_img, (cx, cy), 12, color, 2)

        return debug_img

    def scan_from_file(self, image_path: str, answer_key: dict = None,
                       debug: bool = False) -> ScanResult:
        """Convenience method to scan from file path."""
        image = cv2.imread(image_path)
        if image is None:
            result = ScanResult()
            result.error = f"Could not read image: {image_path}"
            return result
        return self.scan(image, answer_key, debug)


# --- Calibration helper ---
def calibrate_from_image(image_path: str, num_questions: int = 40):
    """
    Helper to visualize bubble detection regions on a sample image.
    Use this to fine-tune FORM_CONFIG ratios.
    """
    engine = OMREngine(num_questions=num_questions)
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

    h, w = warped.shape[:2]

    # Draw student ID region
    cfg = FORM_CONFIG["student_id"]
    cv2.rectangle(warped,
                  (int(w * cfg["left"]), int(h * cfg["top"])),
                  (int(w * cfg["right"]), int(h * cfg["bottom"])),
                  (255, 0, 0), 2)
    cv2.putText(warped, "STUDENT ID", (int(w * cfg["left"]), int(h * cfg["top"]) - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # Draw answer region
    layout = engine.answer_layout
    cv2.rectangle(warped,
                  (int(w * layout["left"]), int(h * layout["top"])),
                  (int(w * layout["right"]), int(h * layout["bottom"])),
                  (0, 0, 255), 2)
    cv2.putText(warped, "ANSWERS", (int(w * layout["left"]), int(h * layout["top"]) - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    # Draw column dividers
    for col in range(layout["columns"]):
        col_w = (layout["right"] - layout["left"]) / layout["columns"]
        cx = int(w * (layout["left"] + col * col_w))
        cv2.line(warped, (cx, int(h * layout["top"])), (cx, int(h * layout["bottom"])),
                 (0, 255, 0), 1)

    output_path = image_path.replace(".", "_calibration.")
    cv2.imwrite(output_path, warped)
    print(f"Calibration image saved: {output_path}")
    return warped


if __name__ == "__main__":
    # Quick test
    engine = OMREngine(num_questions=40)
    print(f"OMR Engine initialized: {engine.num_questions} questions")
    print(f"Fill threshold: {engine.fill_threshold}")
    print(f"Answer layout: {engine.answer_layout}")
