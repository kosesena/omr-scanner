"""
OMR Optical Form PDF Generator v3
Polished design with:
- ArUco markers at 4 corners
- QR code with exam metadata
- Character boxes for name, surname, student number
- Answer bubbles grouped in blocks of 5
- Turkish character support (DejaVuSans)
"""

import cv2
import numpy as np
import qrcode
import json
import uuid
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white, HexColor, Color
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
DARK = HexColor("#1a1a2e")
MID = HexColor("#7f8c8d")
LIGHT = HexColor("#bdc3c7")
VERY_LIGHT = HexColor("#ecf0f1")
ACCENT = HexColor("#2980b9")
ACCENT_DARK = HexColor("#1a5276")
HEADER_BG = HexColor("#2c3e50")
BOX_BORDER = HexColor("#95a5a6")
BUBBLE_BORDER = HexColor("#aab7b8")
BUBBLE_TEXT = HexColor("#566573")
ROW_ALT = HexColor("#f8f9fa")
SEPARATOR = HexColor("#d5dbdb")

# Font setup
_FONT_REGISTERED = False
FONT_NAME = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"


def _register_fonts():
    """Register DejaVuSans for Turkish character support."""
    global _FONT_REGISTERED, FONT_NAME, FONT_NAME_BOLD

    if _FONT_REGISTERED:
        return

    # Search paths: Linux (Docker/Render) + macOS
    search_paths_regular = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        # macOS
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNSText.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    search_paths_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]

    regular = None
    bold = None
    for p in search_paths_regular:
        if os.path.exists(p):
            regular = p
            break
    for p in search_paths_bold:
        if os.path.exists(p):
            bold = p
            break

    # Try fc-list (Linux)
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

    # macOS: try mdfind for any DejaVu font
    if not regular:
        try:
            result = subprocess.run(
                ["mdfind", "-name", "DejaVuSans.ttf"],
                capture_output=True, text=True, timeout=5
            )
            if result.stdout.strip():
                regular = result.stdout.strip().split("\n")[0]
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
        pass

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
                  data: dict, size: float = 20 * mm):
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
# Character Boxes (polished)
# ============================================================

def _draw_char_boxes(c: canvas.Canvas, x: float, y: float,
                     label: str, num_boxes: int,
                     box_size: float = 5.8 * mm,
                     label_width: float = 28 * mm):
    # Label with accent color
    c.setFont(FONT_NAME_BOLD, 7.5)
    c.setFillColor(ACCENT_DARK)
    c.drawString(x, y + box_size * 0.25, label)

    bx = x + label_width
    for i in range(num_boxes):
        # Alternating very subtle background
        if i % 2 == 0:
            c.setFillColor(HexColor("#f7f9fc"))
            c.rect(bx + i * box_size, y, box_size, box_size, fill=1, stroke=0)

        c.setStrokeColor(BOX_BORDER)
        c.setLineWidth(0.5)
        c.rect(bx + i * box_size, y, box_size, box_size, fill=0, stroke=1)

    c.setStrokeColor(black)
    c.setFillColor(black)
    return y - box_size - 3 * mm


# ============================================================
# Answer Bubbles (polished)
# ============================================================

def _draw_bubble(c: canvas.Canvas, x: float, y: float,
                 label: str, r: float = 2.2 * mm):
    c.setStrokeColor(BUBBLE_BORDER)
    c.setLineWidth(0.5)
    c.circle(x, y, r, fill=0, stroke=1)
    c.setFillColor(BUBBLE_TEXT)
    fs = max(r * 1.6, 3.8)
    c.setFont(FONT_NAME, fs)
    c.drawCentredString(x, y - fs * 0.35, label)
    c.setFillColor(black)
    c.setStrokeColor(black)


def _draw_answer_section(c: canvas.Canvas, x_start: float, y_start: float,
                         num_questions: int, options: list, columns: int,
                         y_bottom: float = 0):
    questions_per_col = (num_questions + columns - 1) // columns
    available_width = PAGE_W - 2 * MARGIN
    col_width = available_width / columns

    num_options = len(options)
    q_num_width = 9 * mm
    col_gap = 3 * mm
    usable = col_width - q_num_width - col_gap
    sp_x = usable / num_options

    # Calculate spacing dynamically to fill available vertical space
    num_groups = (questions_per_col - 1) // 5  # number of group gaps
    available_height = y_start - y_bottom - 8 * mm  # header + padding
    # total_height = questions_per_col * sp_y + num_groups * group_gap
    # Solve for sp_y with group_gap = sp_y * 0.55
    total_slots = questions_per_col + num_groups * 0.55
    sp_y = available_height / max(total_slots, 1)
    sp_y = min(sp_y, 16 * mm)  # cap max (allows 20q to spread)
    sp_y = max(sp_y, 5.5 * mm)  # cap min
    group_gap = sp_y * 0.55

    # Scale bubble radius with row spacing for a balanced look
    bubble_r = min(2.5 * mm, sp_x * 0.42, sp_y * 0.32)

    # Scale font size with spacing
    header_fs = min(8.5, max(7, sp_y / mm * 0.75))
    q_fs = min(8.5, max(7, sp_y / mm * 0.7))

    # Column headers with accent underline
    for col_idx in range(columns):
        col_x = x_start + col_idx * col_width
        c.setFont(FONT_NAME_BOLD, header_fs)
        c.setFillColor(ACCENT_DARK)
        for opt_idx, opt in enumerate(options):
            ox = col_x + q_num_width + opt_idx * sp_x + sp_x / 2
            c.drawCentredString(ox, y_start + 2.5 * mm, opt)
    c.setFillColor(black)

    # Header line
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.8)
    c.line(x_start, y_start - 0.5 * mm,
           x_start + available_width, y_start - 0.5 * mm)
    c.setStrokeColor(black)

    for col_idx in range(columns):
        col_x = x_start + col_idx * col_width
        q_start_num = col_idx * questions_per_col
        row_y = y_start - 4.5 * mm

        for row in range(questions_per_col):
            q_num = q_start_num + row + 1
            if q_num > num_questions:
                break

            if row > 0 and row % 5 == 0:
                row_y -= group_gap
                # Group separator line
                c.setStrokeColor(VERY_LIGHT)
                c.setLineWidth(0.3)
                c.line(col_x + 2 * mm, row_y + sp_y - 1 * mm,
                       col_x + col_width - col_gap, row_y + sp_y - 1 * mm)
                c.setStrokeColor(black)

            # Question number
            c.setFont(FONT_NAME_BOLD, q_fs)
            c.setFillColor(DARK)
            c.drawRightString(col_x + q_num_width - 2 * mm, row_y - 1.8, str(q_num))

            # Bubbles
            for opt_idx, opt in enumerate(options):
                ox = col_x + q_num_width + opt_idx * sp_x + sp_x / 2
                _draw_bubble(c, ox, row_y, opt, bubble_r)

            row_y -= sp_y

        # Column separator
        if col_idx < columns - 1:
            sep_x = col_x + col_width - 1 * mm
            c.setStrokeColor(SEPARATOR)
            c.setLineWidth(0.4)
            c.line(sep_x, y_start + 3 * mm, sep_x, row_y + sp_y - 2 * mm)
            c.setStrokeColor(black)


# ============================================================
# Main Generator
# ============================================================

def generate_form_pdf(
    num_questions: int = 40,
    title: str = "SINAV OPT\u0130K FORMU",
    options: list = None,
    output_path: str = None,
    exam_id: str = None,
    course_code: str = "",
    answer_key_id: str = None,
    name_boxes: int = 20,
    surname_boxes: int = 20,
    student_no_boxes: int = 9,
    num_id_digits: int = 10,
) -> bytes:
    _register_fonts()

    if options is None:
        options = ["A", "B", "C", "D", "E"]

    if exam_id is None:
        exam_id = uuid.uuid4().hex[:8]

    num_questions = min(num_questions, 80)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    m = 6 * mm

    # === ArUco markers ===
    _draw_aruco(c, m, PAGE_H - m - MARKER_SIZE, 0)
    _draw_aruco(c, PAGE_W - m - MARKER_SIZE, PAGE_H - m - MARKER_SIZE, 1)
    _draw_aruco(c, m, m, 2)
    _draw_aruco(c, PAGE_W - m - MARKER_SIZE, m, 3)

    # === Header bar ===
    header_h = 10 * mm
    title_y = PAGE_H - m - MARKER_SIZE - 5 * mm

    # Accent line under title
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.5)
    c.line(MARGIN, title_y - 4 * mm, PAGE_W - MARGIN, title_y - 4 * mm)

    # Title text
    c.setFont(FONT_NAME_BOLD, 13)
    c.setFillColor(HEADER_BG)
    c.drawCentredString(PAGE_W / 2, title_y, title)
    c.setFillColor(black)

    # Course code subtitle if provided
    if course_code:
        c.setFont(FONT_NAME, 8)
        c.setFillColor(ACCENT)
        c.drawCentredString(PAGE_W / 2, title_y - 10 * mm, f"Ders: {course_code}")
        c.setFillColor(black)

    # === QR Code (right side) ===
    qr_data = {
        "v": 2,
        "exam_id": exam_id,
        "course": course_code,
        "q": num_questions,
        "opts": len(options),
    }
    if answer_key_id:
        qr_data["key_id"] = answer_key_id

    qr_size = 20 * mm
    qr_x = PAGE_W - MARGIN - qr_size
    qr_y = title_y - 8 * mm - qr_size
    _draw_qr_code(c, qr_x, qr_y, qr_data, qr_size)

    # QR label
    c.setFont(FONT_NAME, 4.5)
    c.setFillColor(MID)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 3 * mm,
                        f"S\u0131nav ID: {exam_id}")
    c.setFillColor(black)

    # === Character boxes ===
    box_y = title_y - 14 * mm
    box_size = 5.5 * mm
    label_w = 24 * mm

    available_box_width = qr_x - MARGIN - label_w - 8 * mm
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

    # === Instruction line ===
    inst_y = box_y - 1.5 * mm

    # Instruction box with light background
    inst_box_h = 6 * mm
    c.setFillColor(HexColor("#eaf2f8"))
    c.roundRect(MARGIN, inst_y - 1.5 * mm, PAGE_W - 2 * MARGIN, inst_box_h,
                1.5 * mm, fill=1, stroke=0)

    c.setFont(FONT_NAME, 5.5)
    c.setFillColor(ACCENT_DARK)
    c.drawString(MARGIN + 3 * mm, inst_y + 0.5 * mm,
                 "Kutulara B\u00dcY\u00dcK HARF ile yaz\u0131n\u0131z. "
                 "Cevap balonlar\u0131n\u0131 tamamen doldurunuz.")

    # Example bubble
    c.setFont(FONT_NAME, 5.5)
    ex_x = PAGE_W - MARGIN - 30 * mm
    c.drawString(ex_x, inst_y + 0.5 * mm, "\u00d6rnek:")
    c.setFillColor(DARK)
    c.circle(ex_x + 14 * mm, inst_y + 1.8 * mm, 2.2 * mm, fill=1, stroke=0)
    c.setFillColor(black)

    # === Answer section ===
    answer_y = inst_y - 8 * mm

    if num_questions <= 50:
        cols = 2
    else:
        cols = 4

    footer_y = m + MARKER_SIZE + 2.5 * mm
    _draw_answer_section(c, MARGIN, answer_y, num_questions, options, cols,
                         y_bottom=footer_y + 6 * mm)

    # === Footer ===

    # Footer line
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.5)
    c.line(MARGIN, footer_y + 4 * mm, PAGE_W - MARGIN, footer_y + 4 * mm)

    c.setFont(FONT_NAME, 6)
    c.setFillColor(ACCENT_DARK)
    c.drawCentredString(PAGE_W / 2, footer_y,
                        "Made by Sena K\u00f6se  \u2022  omr-scanner")
    c.setFillColor(black)

    c.save()

    pdf_bytes = buffer.getvalue()
    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)
    return pdf_bytes


if __name__ == "__main__":
    for nq in [20, 40]:
        print(f"Generating {nq}-question form...")
        generate_form_pdf(
            num_questions=nq,
            title=f"SINAV OPT\u0130K FORMU - {nq} SORU",
            course_code="MAT101",
            output_path=f"sample_form_{nq}q.pdf"
        )
    print("Done!")
