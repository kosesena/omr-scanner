"""
OMR Optical Form PDF Generator
Clean, Gradescope-style answer sheets with:
- 4 ArUco markers at corners
- Student info fields (Name, ID, Class, Date)
- Answer bubbles grouped in blocks of 5
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


PAGE_W, PAGE_H = A4
MARGIN = 15 * mm

ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARKER_SIZE = 9 * mm

DARK = HexColor("#222222")
MID = HexColor("#888888")
LIGHT = HexColor("#CCCCCC")


def generate_aruco_marker(marker_id: int, size_px: int = 200) -> np.ndarray:
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    return cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_px)


def draw_aruco_marker(c: canvas.Canvas, x: float, y: float, marker_id: int):
    marker_img = generate_aruco_marker(marker_id)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, marker_img)
    c.drawImage(tmp.name, x, y, width=MARKER_SIZE, height=MARKER_SIZE)
    os.unlink(tmp.name)


def draw_bubble(c: canvas.Canvas, x: float, y: float, label: str, r: float):
    """Draw a single clean bubble."""
    c.setStrokeColor(LIGHT)
    c.setLineWidth(0.5)
    c.circle(x, y, r, fill=0, stroke=1)
    c.setFillColor(MID)
    c.setFont("Helvetica", r * 1.8)
    c.drawCentredString(x, y - r * 0.4, label)
    c.setFillColor(black)
    c.setStrokeColor(black)


def draw_info_section(c: canvas.Canvas, x: float, y: float):
    """Draw student info fields like Gradescope."""
    fields_left = [("Name", 70 * mm), ("ID", 70 * mm)]
    fields_right = [("Class", 30 * mm), ("Date", 30 * mm)]

    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(DARK)

    # Left fields
    cy = y
    for label, width in fields_left:
        c.drawString(x, cy, label)
        c.setStrokeColor(LIGHT)
        c.setLineWidth(0.8)
        c.line(x + 15 * mm, cy - 1, x + width, cy - 1)
        c.setStrokeColor(black)
        cy -= 8 * mm

    # Right fields
    cy = y
    rx = PAGE_W / 2 + 10 * mm
    for label, width in fields_right:
        c.drawString(rx, cy, label)
        c.setStrokeColor(LIGHT)
        c.setLineWidth(0.8)
        c.line(rx + 15 * mm, cy - 1, rx + width + 15 * mm, cy - 1)
        c.setStrokeColor(black)
        cy -= 8 * mm

    return y - len(fields_left) * 8 * mm - 4 * mm


def draw_answer_section(c: canvas.Canvas, x_start: float, y_start: float,
                        num_questions: int, options: list, columns: int):
    """Draw answer bubbles in clean columns, grouped by 5."""

    questions_per_col = (num_questions + columns - 1) // columns
    available_width = PAGE_W - 2 * MARGIN
    col_width = available_width / columns

    # Calculate bubble sizing
    num_options = len(options)
    q_num_width = 9 * mm
    col_gap = 3 * mm
    usable = col_width - q_num_width - col_gap
    sp_x = usable / num_options
    bubble_r = min(2.2 * mm, sp_x * 0.4)

    # Vertical spacing
    sp_y = 5.8 * mm
    group_gap = 3.5 * mm  # extra space every 5 questions

    # Column headers: A B C D E
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(DARK)
    for col_idx in range(columns):
        col_x = x_start + col_idx * col_width
        for opt_idx, opt in enumerate(options):
            ox = col_x + q_num_width + opt_idx * sp_x + sp_x / 2
            c.drawCentredString(ox, y_start + 2 * mm, opt)
    c.setFillColor(black)

    # Draw questions
    for col_idx in range(columns):
        col_x = x_start + col_idx * col_width
        q_start = col_idx * questions_per_col

        row_y = y_start - 4 * mm

        for row in range(questions_per_col):
            q_num = q_start + row + 1
            if q_num > num_questions:
                break

            # Add group gap every 5 questions
            if row > 0 and row % 5 == 0:
                row_y -= group_gap

            # Question number
            c.setFont("Helvetica-Bold", 7)
            c.setFillColor(DARK)
            c.drawRightString(col_x + q_num_width - 2 * mm, row_y - 2, str(q_num))

            # Option bubbles
            for opt_idx, opt in enumerate(options):
                ox = col_x + q_num_width + opt_idx * sp_x + sp_x / 2
                draw_bubble(c, ox, row_y, opt, bubble_r)

            row_y -= sp_y

    c.setFillColor(black)


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

    # --- ArUco markers at corners ---
    m = 6 * mm
    draw_aruco_marker(c, m, PAGE_H - m - MARKER_SIZE, 0)
    draw_aruco_marker(c, PAGE_W - m - MARKER_SIZE, PAGE_H - m - MARKER_SIZE, 1)
    draw_aruco_marker(c, m, m, 2)
    draw_aruco_marker(c, PAGE_W - m - MARKER_SIZE, m, 3)

    # --- Title ---
    title_y = PAGE_H - m - MARKER_SIZE - 8 * mm
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(DARK)
    c.drawCentredString(PAGE_W / 2, title_y, title)

    # Thin line under title
    c.setStrokeColor(LIGHT)
    c.setLineWidth(0.8)
    c.line(MARGIN, title_y - 3 * mm, PAGE_W - MARGIN, title_y - 3 * mm)
    c.setStrokeColor(black)

    # --- Student info ---
    info_y = title_y - 10 * mm
    info_bottom = draw_info_section(c, MARGIN, info_y)

    # --- Marking instruction ---
    inst_y = info_bottom - 2 * mm
    c.setFont("Helvetica", 6)
    c.setFillColor(MID)
    c.drawString(MARGIN, inst_y,
                 "Fill bubbles completely with dark pen/pencil. Do not fold or damage.")

    # Example bubble
    ex_x = PAGE_W - MARGIN - 30 * mm
    c.setFont("Helvetica", 6)
    c.drawString(ex_x, inst_y, "Example:")
    c.setFillColor(DARK)
    c.circle(ex_x + 18 * mm, inst_y + 1.5, 2.2 * mm, fill=1, stroke=0)
    c.setFillColor(black)

    # --- Answer section ---
    answer_y = inst_y - 8 * mm

    # Determine columns
    if num_questions <= 25:
        cols = 2
    elif num_questions <= 50:
        cols = 2
    elif num_questions <= 100:
        cols = 4
    else:
        cols = 4

    draw_answer_section(c, MARGIN, answer_y, num_questions, options, cols)

    # --- Footer ---
    c.setFont("Helvetica", 5)
    c.setFillColor(MID)
    c.drawCentredString(PAGE_W / 2, m + MARKER_SIZE + 2 * mm,
                        f"OMR Scanner Form  |  {num_questions} Questions")

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
