"""
OMR Optical Form PDF Generator
Generates printable A4 answer sheets with:
- 4 ArUco markers at corners (for perspective correction)
- Student ID bubble grid (10 digits, each 0-9)
- Answer bubbles (configurable questions, A-B-C-D-E)
"""

import cv2
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white, HexColor
from io import BytesIO
import tempfile
import os


# --- Constants ---
PAGE_W, PAGE_H = A4  # 210mm x 297mm
MARGIN = 15 * mm

# ArUco marker config
ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARKER_SIZE_MM = 12
MARKER_SIZE = MARKER_SIZE_MM * mm

# Bubble config
BUBBLE_RADIUS = 3.2 * mm
BUBBLE_SPACING_X = 8.5 * mm
BUBBLE_SPACING_Y = 7.5 * mm

# Colors
LIGHT_GRAY = HexColor("#E8E8E8")
DARK_GRAY = HexColor("#333333")
MID_GRAY = HexColor("#999999")
HEADER_BG = HexColor("#2C3E50")
ACCENT = HexColor("#3498DB")


def generate_aruco_marker(marker_id: int, size_px: int = 100) -> np.ndarray:
    """Generate an ArUco marker image."""
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_px)
    return marker_img


def draw_aruco_marker(c: canvas.Canvas, x: float, y: float, marker_id: int):
    """Draw an ArUco marker on the PDF canvas at (x, y) position."""
    size_px = 200
    marker_img = generate_aruco_marker(marker_id, size_px)

    # Save marker as temporary PNG
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, marker_img)

    # Draw on canvas
    c.drawImage(tmp.name, x, y, width=MARKER_SIZE, height=MARKER_SIZE)
    os.unlink(tmp.name)


def draw_bubble(c: canvas.Canvas, x: float, y: float, label: str, filled: bool = False):
    """Draw a single bubble with a label."""
    if filled:
        c.setFillColor(DARK_GRAY)
        c.circle(x, y, BUBBLE_RADIUS, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(x, y - 2.5, label)
        c.setFillColor(black)
    else:
        c.setStrokeColor(MID_GRAY)
        c.setLineWidth(0.6)
        c.circle(x, y, BUBBLE_RADIUS, fill=0, stroke=1)
        c.setFillColor(DARK_GRAY)
        c.setFont("Helvetica", 6.5)
        c.drawCentredString(x, y - 2.2, label)
        c.setStrokeColor(black)


def draw_student_id_section(c: canvas.Canvas, x_start: float, y_start: float, num_digits: int = 10):
    """Draw the student ID bubble grid."""
    # Section header
    c.setFillColor(HEADER_BG)
    c.roundRect(x_start - 2 * mm, y_start + 2 * mm, num_digits * BUBBLE_SPACING_X + 6 * mm, 7 * mm, 2, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_start + 1 * mm, y_start + 4.5 * mm, "STUDENT NO")
    c.setFillColor(black)

    # Column headers (digit positions)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(ACCENT)
    for col in range(num_digits):
        cx = x_start + col * BUBBLE_SPACING_X + BUBBLE_SPACING_X / 2
        c.drawCentredString(cx, y_start - 2 * mm, str(col + 1))
    c.setFillColor(black)

    # Bubble grid: 10 rows (digits 0-9) x num_digits columns
    for row in range(10):
        ry = y_start - 6 * mm - row * BUBBLE_SPACING_Y
        # Row label
        c.setFillColor(MID_GRAY)
        c.setFont("Helvetica", 6)
        c.drawRightString(x_start - 3 * mm, ry - 2.2, str(row))
        c.setFillColor(black)

        for col in range(num_digits):
            cx = x_start + col * BUBBLE_SPACING_X + BUBBLE_SPACING_X / 2
            draw_bubble(c, cx, ry, str(row))

    # Return the bottom Y coordinate
    return y_start - 6 * mm - 9 * BUBBLE_SPACING_Y - 5 * mm


def draw_answer_section(c: canvas.Canvas, x_start: float, y_start: float,
                        num_questions: int = 40, options: list = None,
                        columns: int = 4):
    """Draw the answer bubbles section in multiple columns."""
    if options is None:
        options = ["A", "B", "C", "D", "E"]

    num_options = len(options)
    questions_per_col = (num_questions + columns - 1) // columns

    # Available width for answer section
    available_width = PAGE_W - 2 * MARGIN
    col_width = available_width / columns

    # Section header
    c.setFillColor(HEADER_BG)
    header_width = available_width + 4 * mm
    c.roundRect(x_start - 2 * mm, y_start + 2 * mm, header_width, 7 * mm, 2, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_start + 1 * mm, y_start + 4.5 * mm, f"ANSWERS  ({num_questions} questions)")
    c.setFillColor(black)

    for col_idx in range(columns):
        col_x = x_start + col_idx * col_width
        q_start = col_idx * questions_per_col

        # Column option headers
        c.setFont("Helvetica-Bold", 6.5)
        c.setFillColor(ACCENT)
        for opt_idx, opt in enumerate(options):
            ox = col_x + 12 * mm + opt_idx * BUBBLE_SPACING_X
            c.drawCentredString(ox, y_start - 2 * mm, opt)
        c.setFillColor(black)

        # Draw rows
        for row in range(questions_per_col):
            q_num = q_start + row + 1
            if q_num > num_questions:
                break

            ry = y_start - 6 * mm - row * BUBBLE_SPACING_Y

            # Alternating row background
            if row % 2 == 0:
                c.setFillColor(HexColor("#F5F5F5"))
                c.rect(col_x, ry - BUBBLE_RADIUS - 1 * mm,
                       col_width - 2 * mm, BUBBLE_SPACING_Y, fill=1, stroke=0)
                c.setFillColor(black)

            # Question number
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(DARK_GRAY)
            c.drawRightString(col_x + 9 * mm, ry - 2.2, str(q_num))
            c.setFillColor(black)

            # Option bubbles
            for opt_idx, opt in enumerate(options):
                ox = col_x + 12 * mm + opt_idx * BUBBLE_SPACING_X
                draw_bubble(c, ox, ry, opt)

        # Column separator line
        if col_idx < columns - 1:
            sep_x = col_x + col_width - 1 * mm
            c.setStrokeColor(LIGHT_GRAY)
            c.setLineWidth(0.3)
            c.line(sep_x, y_start - 3 * mm, sep_x, y_start - 6 * mm - questions_per_col * BUBBLE_SPACING_Y)
            c.setStrokeColor(black)

    bottom_y = y_start - 6 * mm - questions_per_col * BUBBLE_SPACING_Y
    return bottom_y


def generate_form_pdf(
    num_questions: int = 40,
    num_id_digits: int = 10,
    options: list = None,
    title: str = "OMR ANSWER SHEET",
    output_path: str = None,
) -> bytes:
    """
    Generate a complete OMR form PDF.

    Args:
        num_questions: Number of questions (max ~100 for single page)
        num_id_digits: Number of digits in student ID
        options: Answer options list, default ["A","B","C","D","E"]
        title: Form title
        output_path: If provided, save to file; otherwise return bytes

    Returns:
        PDF file as bytes
    """
    if options is None:
        options = ["A", "B", "C", "D", "E"]

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # --- ArUco markers at 4 corners ---
    marker_margin = 8 * mm
    # Top-left (ID: 0)
    draw_aruco_marker(c, marker_margin, PAGE_H - marker_margin - MARKER_SIZE, 0)
    # Top-right (ID: 1)
    draw_aruco_marker(c, PAGE_W - marker_margin - MARKER_SIZE, PAGE_H - marker_margin - MARKER_SIZE, 1)
    # Bottom-left (ID: 2)
    draw_aruco_marker(c, marker_margin, marker_margin, 2)
    # Bottom-right (ID: 3)
    draw_aruco_marker(c, PAGE_W - marker_margin - MARKER_SIZE, marker_margin, 3)

    # --- Title ---
    title_y = PAGE_H - marker_margin - MARKER_SIZE - 8 * mm
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(HEADER_BG)
    c.drawCentredString(PAGE_W / 2, title_y, title)

    # Subtitle line
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.5)
    c.line(MARGIN, title_y - 4 * mm, PAGE_W - MARGIN, title_y - 4 * mm)

    # --- Name/Class line ---
    info_y = title_y - 14 * mm
    c.setFont("Helvetica", 8)
    c.setFillColor(DARK_GRAY)
    c.drawString(MARGIN, info_y, "Name: ____________________________")
    c.drawString(PAGE_W / 2, info_y, "Class: ________  Date: ________")

    # --- Student ID Section ---
    id_y = info_y - 12 * mm
    id_bottom = draw_student_id_section(c, MARGIN + 2 * mm, id_y, num_id_digits)

    # --- Answer Section ---
    answer_y = id_bottom - 5 * mm
    # Determine column count based on questions
    if num_questions <= 20:
        cols = 2
    elif num_questions <= 40:
        cols = 4
    else:
        cols = 5

    draw_answer_section(c, MARGIN, answer_y, num_questions, options, cols)

    # --- Footer ---
    c.setFont("Helvetica", 6)
    c.setFillColor(MID_GRAY)
    c.drawCentredString(PAGE_W / 2, 8 * mm + MARKER_SIZE,
                        "Do not fold or damage. Fill bubbles completely with dark pen/pencil.")

    # --- Timing marks (small squares along edges for additional alignment) ---
    mark_size = 2.5 * mm
    c.setFillColor(black)
    # Left edge timing marks
    for i in range(20):
        my = PAGE_H / 2 - 10 * (BUBBLE_SPACING_Y) + i * BUBBLE_SPACING_Y
        c.rect(MARGIN - 6 * mm, my - mark_size / 2, mark_size, mark_size, fill=1, stroke=0)

    c.setFillColor(black)
    c.save()

    pdf_bytes = buffer.getvalue()

    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes


if __name__ == "__main__":
    # Generate sample forms
    print("Generating 20-question form...")
    generate_form_pdf(
        num_questions=20,
        title="SINAV OPTIK FORMU - 20 SORU",
        output_path="sample_form_20q.pdf"
    )

    print("Generating 40-question form...")
    generate_form_pdf(
        num_questions=40,
        title="SINAV OPTIK FORMU - 40 SORU",
        output_path="sample_form_40q.pdf"
    )

    print("Generating 100-question form...")
    generate_form_pdf(
        num_questions=100,
        title="SINAV OPTIK FORMU - 100 SORU",
        output_path="sample_form_100q.pdf"
    )

    print("Done! Forms saved.")
