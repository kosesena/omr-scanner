"""
OMR Optical Form PDF Generator v2
Clean form with:
- ArUco markers at 4 corners
- QR code with exam metadata
- Character boxes for name, surname, student number (handwriting)
- Answer bubbles grouped in blocks of 5 (Gradescope-style)
"""

import cv2
import numpy as np
import qrcode
import json
import uuid
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import tempfile
import os
import subprocess

PAGE_W, PAGE_H = A4
MARGIN = 14 * mm

ARUCO_DICT = cv2.aruco.DICT_4X4_50
MARKER_SIZE = 9 * mm

# Colors
DARK = HexColor("#222222")
MID = HexColor("#888888")
LIGHT = HexColor("#CCCCCC")
VERY_LIGHT = HexColor("#F0F0F0")
ACCENT = HexColor("#3498DB")
HEADER_BG = HexColor("#2C3E50")

# Font setup - try to register a Unicode-capable font
_FONT_REGISTERED = False
FONT_NAME = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"


def _register_fonts():
    """Register a Unicode-capable TTF font for Turkish character support."""
    global _FONT_REGISTERED, FONT_NAME, FONT_NAME_BOLD

    if _FONT_REGISTERED:
        return

    # Search for DejaVuSans (commonly available on Linux/Docker)
    search_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]

    regular = None
    bold = None
    for p in search_paths:
        if os.path.exists(p):
            if "Bold" in p:
                bold = p
            else:
                regular = p

    # Try to find via fc-list
    if not regular:
        try:
            result = subprocess.run(
                ["fc-list", "DejaVu Sans:style=Book", "-f", "%{file}"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                regular = result.stdout.strip().split("\n")[0]
        except Exception:
            pass

    if not bold:
        try:
            result = subprocess.run(
                ["fc-list", "DejaVu Sans:style=Bold", "-f", "%{file}"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                bold = result.stdout.strip().split("\n")[0]
        except Exception:
            pass

    try:
        if regular:
            pdfmetrics.registerFont(TTFont("DejaVuSans", regular))
            FONT_NAME = "DejaVuSans"
        if bold:
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold))
            FONT_NAME_BOLD = "DejaVuSans-Bold"
        elif regular:
            FONT_NAME_BOLD = "DejaVuSans"
    except Exception:
        pass  # Fall back to Helvetica

    _FONT_REGISTERED = True


# ============================================================
# ArUco Markers
# ============================================================

def _generate_aruco(marker_id: int, size_px: int = 200) -> np.ndarray:
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    return cv2.aruco.generateImageMarker(aruco_dict, marker_id, size_px)


def _draw_aruco(c: canvas.Canvas, x: float, y: float, marker_id: int):
    img = _generate_aruco(marker_id)
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    cv2.imwrite(tmp.name, img)
    c.drawImage(tmp.name, x, y, width=MARKER_SIZE, height=MARKER_SIZE)
    os.unlink(tmp.name)


# ============================================================
# QR Code
# ============================================================

def _draw_qr_code(c: canvas.Canvas, x: float, y: float,
                  data: dict, size: float = 18 * mm):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=1,
    )
    qr.add_data(json.dumps(data, ensure_ascii=False))
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    qr_img.save(tmp.name)
    c.drawImage(tmp.name, x, y, width=size, height=size)
    os.unlink(tmp.name)


# ============================================================
# Character Boxes
# ============================================================

def _draw_char_boxes(c: canvas.Canvas, x: float, y: float,
                     label: str, num_boxes: int,
                     box_size: float = 5.5 * mm,
                     label_width: float = 28 * mm):
    c.setFont(FONT_NAME_BOLD, 7)
    c.setFillColor(DARK)
    c.drawString(x, y + box_size * 0.3, label)

    bx = x + label_width
    for i in range(num_boxes):
        c.setStrokeColor(LIGHT)
        c.setLineWidth(0.6)
        c.rect(bx + i * box_size, y, box_size, box_size, fill=0, stroke=1)

    c.setStrokeColor(black)
    c.setFillColor(black)
    return y - box_size - 2.5 * mm


# ============================================================
# Answer Bubbles
# ============================================================

def _draw_bubble(c: canvas.Canvas, x: float, y: float,
                 label: str, r: float = 2.0 * mm):
    c.setStrokeColor(LIGHT)
    c.setLineWidth(0.45)
    c.circle(x, y, r, fill=0, stroke=1)
    c.setFillColor(MID)
    fs = max(r * 1.7, 3.5)
    c.setFont(FONT_NAME, fs)
    c.drawCentredString(x, y - fs * 0.35, label)
    c.setFillColor(black)
    c.setStrokeColor(black)


def _draw_answer_section(c: canvas.Canvas, x_start: float, y_start: float,
                         num_questions: int, options: list, columns: int):
    questions_per_col = (num_questions + columns - 1) // columns
    available_width = PAGE_W - 2 * MARGIN
    col_width = available_width / columns

    num_options = len(options)
    q_num_width = 8 * mm
    col_gap = 2 * mm
    usable = col_width - q_num_width - col_gap
    sp_x = usable / num_options
    bubble_r = min(2.2 * mm, sp_x * 0.4)

    sp_y = 5.5 * mm
    group_gap = 3.0 * mm

    # Column headers
    c.setFont(FONT_NAME_BOLD, 6.5)
    c.setFillColor(DARK)
    for col_idx in range(columns):
        col_x = x_start + col_idx * col_width
        for opt_idx, opt in enumerate(options):
            ox = col_x + q_num_width + opt_idx * sp_x + sp_x / 2
            c.drawCentredString(ox, y_start + 2 * mm, opt)
    c.setFillColor(black)

    c.setStrokeColor(LIGHT)
    c.setLineWidth(0.4)
    c.line(x_start, y_start - 0.5 * mm,
           x_start + available_width, y_start - 0.5 * mm)
    c.setStrokeColor(black)

    for col_idx in range(columns):
        col_x = x_start + col_idx * col_width
        q_start_num = col_idx * questions_per_col
        row_y = y_start - 4 * mm

        for row in range(questions_per_col):
            q_num = q_start_num + row + 1
            if q_num > num_questions:
                break

            if row > 0 and row % 5 == 0:
                row_y -= group_gap

            c.setFont(FONT_NAME_BOLD, 6.5)
            c.setFillColor(DARK)
            c.drawRightString(col_x + q_num_width - 2 * mm, row_y - 2, str(q_num))

            for opt_idx, opt in enumerate(options):
                ox = col_x + q_num_width + opt_idx * sp_x + sp_x / 2
                _draw_bubble(c, ox, row_y, opt, bubble_r)

            row_y -= sp_y

        if col_idx < columns - 1:
            sep_x = col_x + col_width - 0.5 * mm
            c.setStrokeColor(VERY_LIGHT)
            c.setLineWidth(0.3)
            c.line(sep_x, y_start, sep_x, row_y + sp_y - 2 * mm)
            c.setStrokeColor(black)


# ============================================================
# Main Generator
# ============================================================

def generate_form_pdf(
    num_questions: int = 40,
    title: str = "SINAV OPTIK FORMU",
    options: list = None,
    output_path: str = None,
    exam_id: str = None,
    course_code: str = "",
    answer_key_id: str = None,
    name_boxes: int = 20,
    surname_boxes: int = 20,
    student_no_boxes: int = 9,
    # Legacy parameters (ignored)
    num_id_digits: int = 10,
) -> bytes:
    _register_fonts()

    if options is None:
        options = ["A", "B", "C", "D", "E"]

    if exam_id is None:
        exam_id = uuid.uuid4().hex[:8]

    # Max 80 questions
    num_questions = min(num_questions, 80)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    m = 6 * mm

    # === ArUco markers ===
    _draw_aruco(c, m, PAGE_H - m - MARKER_SIZE, 0)
    _draw_aruco(c, PAGE_W - m - MARKER_SIZE, PAGE_H - m - MARKER_SIZE, 1)
    _draw_aruco(c, m, m, 2)
    _draw_aruco(c, PAGE_W - m - MARKER_SIZE, m, 3)

    # === Title ===
    title_y = PAGE_H - m - MARKER_SIZE - 7 * mm
    c.setFont(FONT_NAME_BOLD, 12)
    c.setFillColor(HEADER_BG)
    c.drawCentredString(PAGE_W / 2, title_y, title)

    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.0)
    c.line(MARGIN, title_y - 3 * mm, PAGE_W - MARGIN, title_y - 3 * mm)
    c.setStrokeColor(black)
    c.setFillColor(black)

    # === QR Code ===
    qr_data = {
        "v": 2,
        "exam_id": exam_id,
        "course": course_code,
        "q": num_questions,
        "opts": len(options),
    }
    if answer_key_id:
        qr_data["key_id"] = answer_key_id

    qr_size = 18 * mm
    qr_x = PAGE_W - MARGIN - qr_size
    qr_y = title_y - 6 * mm - qr_size
    _draw_qr_code(c, qr_x, qr_y, qr_data, qr_size)

    c.setFont(FONT_NAME, 4.5)
    c.setFillColor(MID)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 2.5 * mm,
                        f"Exam: {exam_id}")
    c.setFillColor(black)

    # === Character boxes ===
    box_y = title_y - 10 * mm
    box_size = 5.2 * mm
    label_w = 22 * mm

    available_box_width = qr_x - MARGIN - label_w - 5 * mm
    max_boxes = int(available_box_width / box_size)

    actual_name_boxes = min(name_boxes, max_boxes)
    actual_surname_boxes = min(surname_boxes, max_boxes)
    actual_no_boxes = min(student_no_boxes, max_boxes)

    box_y = _draw_char_boxes(c, MARGIN, box_y, "AD:", actual_name_boxes,
                             box_size=box_size, label_width=label_w)
    box_y = _draw_char_boxes(c, MARGIN, box_y, "SOYAD:", actual_surname_boxes,
                             box_size=box_size, label_width=label_w)
    box_y = _draw_char_boxes(c, MARGIN, box_y, "NO:", actual_no_boxes,
                             box_size=box_size, label_width=label_w)

    # === Instruction ===
    inst_y = box_y - 2 * mm
    c.setFont(FONT_NAME, 5.5)
    c.setFillColor(MID)
    c.drawString(MARGIN, inst_y,
                 "Kutulara BUYUK HARF ile yaziniz. Cevap balonlarini tamamen doldurunuz.")

    c.setFont(FONT_NAME, 5.5)
    ex_x = PAGE_W - MARGIN - 35 * mm
    c.drawString(ex_x, inst_y, "Ornek:")
    c.setFillColor(DARK)
    c.circle(ex_x + 14 * mm, inst_y + 1.5, 2.2 * mm, fill=1, stroke=0)
    c.setFillColor(black)

    # === Answer section ===
    answer_y = inst_y - 7 * mm

    if num_questions <= 25:
        cols = 2
    elif num_questions <= 50:
        cols = 2
    else:
        cols = 4

    _draw_answer_section(c, MARGIN, answer_y, num_questions, options, cols)

    # === Footer ===
    c.setFont(FONT_NAME, 4.5)
    c.setFillColor(MID)
    c.drawCentredString(PAGE_W / 2, m + MARKER_SIZE + 2 * mm,
                        f"OMR Scanner  |  {num_questions} Soru  |  Katlamayiniz ve kirletmeyiniz.")
    c.setFillColor(black)

    c.save()

    pdf_bytes = buffer.getvalue()
    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
    return pdf_bytes


if __name__ == "__main__":
    for nq in [20, 40, 60, 80]:
        print(f"Generating {nq}-question form...")
        generate_form_pdf(
            num_questions=nq,
            title=f"SINAV OPTIK FORMU - {nq} SORU",
            course_code="MAT101",
            output_path=f"sample_form_{nq}q.pdf"
        )
    print("Done!")
