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
MARGIN = 12 * mm

# ArUco marker config
ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARKER_SIZE_MM = 10
MARKER_SIZE = MARKER_SIZE_MM * mm

# Colors
LIGHT_GRAY = HexColor("#E8E8E8")
DARK_GRAY = HexColor("#333333")
MID_GRAY = HexColor("#999999")
HEADER_BG = HexColor("#2C3E50")
ACCENT = HexColor("#3498DB")


def generate_aruco_marker(marker_id: int, size_px: int = 100) -> np.ndarray:
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_px)
    return marker_img


def draw_aruco_marker(c: canvas.Canvas, x: float, y: float, marker_id: int):
    size_px = 200
    marker_img = generate_aruco_marker(marker_id, size_px)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, marker_img)
    c.drawImage(tmp.name, x, y, width=MARKER_SIZE, height=MARKER_SIZE)
    os.unlink(tmp.name)


def draw_bubble(c: canvas.Canvas, x: float, y: float, label: str,
                radius: float = 2.0 * mm, font_size: float = 5.5):
    """Draw a single OMR bubble."""
    c.setStrokeColor(MID_GRAY)
    c.setLineWidth(0.4)
    c.circle(x, y, radius, fill=0, stroke=1)
    c.setFillColor(DARK_GRAY)
    c.setFont("Helvetica", font_size)
    c.drawCentredString(x, y - font_size * 0.35, label)
    c.setStrokeColor(black)
    c.setFillColor(black)


def draw_student_id_section(c: canvas.Canvas, x_start: float, y_start: float,
                            num_digits: int = 10):
    """Draw the student ID bubble grid."""
    bubble_r = 2.0 * mm
    sp_x = 6.0 * mm  # horizontal spacing between digit columns
    sp_y = 5.5 * mm  # vertical spacing between rows

    section_width = num_digits * sp_x + 8 * mm

    # Section header
    c.setFillColor(HEADER_BG)
    c.roundRect(x_start - 1 * mm, y_start + 1 * mm,
                section_width, 5.5 * mm, 2, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x_start + 1 * mm, y_start + 2.8 * mm, "STUDENT NO")
    c.setFillColor(black)

    # Column headers (1, 2, 3, ...)
    c.setFont("Helvetica-Bold", 5.5)
    c.setFillColor(ACCENT)
    for col in range(num_digits):
        cx = x_start + 3 * mm + col * sp_x
        c.drawCentredString(cx, y_start - 2 * mm, str(col + 1))
    c.setFillColor(black)

    # Bubble grid: 10 rows (0-9) x num_digits columns
    for row in range(10):
        ry = y_start - 5 * mm - row * sp_y

        # Row label
        c.setFillColor(MID_GRAY)
        c.setFont("Helvetica", 5)
        c.drawRightString(x_start - 2 * mm, ry - 1.8, str(row))
        c.setFillColor(black)

        for col in range(num_digits):
            cx = x_start + 3 * mm + col * sp_x
            draw_bubble(c, cx, ry, str(row), radius=bubble_r, font_size=5)

    bottom_y = y_start - 5 * mm - 9 * sp_y - 3 * mm
    return bottom_y


def draw_answer_section(c: canvas.Canvas, x_start: float, y_start: float,
                        num_questions: int = 40, options: list = None,
                        columns: int = 4):
    """Draw the answer bubbles section."""
    if options is None:
        options = ["A", "B", "C", "D", "E"]

    num_options = len(options)
    questions_per_col = (num_questions + columns - 1) // columns

    available_width = PAGE_W - 2 * MARGIN
    col_width = available_width / columns

    # Calculate spacing to fit within column
    # Layout per column: [q_num_space] [opt1] [opt2] [opt3] [opt4] [opt5] [gap]
    q_num_space = 7 * mm  # space for question number
    right_gap = 2 * mm    # gap at right of column
    bubble_area = col_width - q_num_space - right_gap
    sp_x = bubble_area / num_options  # spacing between option bubbles

    # Clamp bubble radius to not exceed half of spacing
    bubble_r = min(2.0 * mm, sp_x * 0.38)
    font_size = min(5.5, bubble_r / mm * 2.8)
    q_font_size = font_size + 0.5

    # Vertical spacing - fit in available height
    available_height = y_start - (MARGIN + MARKER_SIZE + 10 * mm)
    sp_y = min(6.5 * mm, available_height / (questions_per_col + 1))
    sp_y = max(sp_y, 4.5 * mm)  # minimum readable spacing

    # Section header
    c.setFillColor(HEADER_BG)
    c.roundRect(x_start - 1 * mm, y_start + 1 * mm,
                available_width + 2 * mm, 5.5 * mm, 2, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(x_start + 1 * mm, y_start + 2.8 * mm,
                 f"ANSWERS  ({num_questions} questions)")
    c.setFillColor(black)

    for col_idx in range(columns):
        col_x = x_start + col_idx * col_width

        q_start = col_idx * questions_per_col

        # Column option headers (A, B, C, D, E)
        c.setFont("Helvetica-Bold", max(font_size, 4.5))
        c.setFillColor(ACCENT)
        for opt_idx, opt in enumerate(options):
            ox = col_x + q_num_space + opt_idx * sp_x
            c.drawCentredString(ox, y_start - 2.5 * mm, opt)
        c.setFillColor(black)

        # Draw question rows
        for row in range(questions_per_col):
            q_num = q_start + row + 1
            if q_num > num_questions:
                break

            ry = y_start - 6 * mm - row * sp_y

            # Alternating row background
            if row % 2 == 0:
                c.setFillColor(HexColor("#F5F5F5"))
                c.rect(col_x, ry - bubble_r - 0.8 * mm,
                       col_width - 1 * mm, sp_y, fill=1, stroke=0)
                c.setFillColor(black)

            # Question number
            c.setFont("Helvetica-Bold", q_font_size)
            c.setFillColor(DARK_GRAY)
            c.drawRightString(col_x + q_num_space - 2 * mm, ry - 1.8, str(q_num))
            c.setFillColor(black)

            # Option bubbles
            for opt_idx, opt in enumerate(options):
                ox = col_x + q_num_space + opt_idx * sp_x
                draw_bubble(c, ox, ry, opt, radius=bubble_r, font_size=font_size)

        # Column separator
        if col_idx < columns - 1:
            sep_x = col_x + col_width - 0.5 * mm
            c.setStrokeColor(LIGHT_GRAY)
            c.setLineWidth(0.3)
            c.line(sep_x, y_start - 3 * mm,
                   sep_x, y_start - 6 * mm - questions_per_col * sp_y)
            c.setStrokeColor(black)

    bottom_y = y_start - 6 * mm - questions_per_col * sp_y
    return bottom_y


def generate_form_pdf(
    num_questions: int = 40,
    num_id_digits: int = 10,
    options: list = None,
    title: str = "OMR ANSWER SHEET",
    output_path: str = None,
) -> bytes:
    if options is None:
        options = ["A", "B", "C", "D", "E"]

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # --- ArUco markers at 4 corners ---
    marker_margin = 6 * mm
    draw_aruco_marker(c, marker_margin,
                      PAGE_H - marker_margin - MARKER_SIZE, 0)
    draw_aruco_marker(c, PAGE_W - marker_margin - MARKER_SIZE,
                      PAGE_H - marker_margin - MARKER_SIZE, 1)
    draw_aruco_marker(c, marker_margin, marker_margin, 2)
    draw_aruco_marker(c, PAGE_W - marker_margin - MARKER_SIZE,
                      marker_margin, 3)

    # --- Title ---
    title_y = PAGE_H - marker_margin - MARKER_SIZE - 5 * mm
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(HEADER_BG)
    c.drawCentredString(PAGE_W / 2, title_y, title)

    # Accent line
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.2)
    c.line(MARGIN, title_y - 3 * mm, PAGE_W - MARGIN, title_y - 3 * mm)

    # --- Name/Class ---
    info_y = title_y - 10 * mm
    c.setFont("Helvetica", 7)
    c.setFillColor(DARK_GRAY)
    c.drawString(MARGIN, info_y, "Name: ____________________________")
    c.drawString(PAGE_W / 2, info_y, "Class: ________  Date: ________")

    # --- Student ID ---
    id_y = info_y - 8 * mm
    id_bottom = draw_student_id_section(c, MARGIN + 2 * mm, id_y, num_id_digits)

    # --- Answers ---
    answer_y = id_bottom - 2 * mm

    if num_questions <= 20:
        cols = 2
    elif num_questions <= 60:
        cols = 4
    else:
        cols = 5

    draw_answer_section(c, MARGIN, answer_y, num_questions, options, cols)

    # --- Footer ---
    c.setFont("Helvetica", 5)
    c.setFillColor(MID_GRAY)
    c.drawCentredString(PAGE_W / 2, marker_margin + MARKER_SIZE + 2 * mm,
                        "Do not fold or damage. Fill bubbles completely with dark pen/pencil.")

    # --- Timing marks ---
    mark_size = 2 * mm
    c.setFillColor(black)
    for i in range(20):
        my = answer_y - 5 * mm - i * 6 * mm
        if my < marker_margin + MARKER_SIZE + 6 * mm:
            break
        c.rect(MARGIN - 4.5 * mm, my - mark_size / 2,
               mark_size, mark_size, fill=1, stroke=0)

    c.setFillColor(black)
    c.save()

    pdf_bytes = buffer.getvalue()
    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
    return pdf_bytes


if __name__ == "__main__":
    for nq in [20, 40, 60, 80, 100]:
        print(f"Generating {nq}-question form...")
        generate_form_pdf(
            num_questions=nq,
            title=f"SINAV OPTIK FORMU - {nq} SORU",
            output_path=f"sample_form_{nq}q.pdf"
        )
    print("Done!")
