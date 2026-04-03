"""
OMR Scanner API v2
FastAPI backend for optical mark recognition + handwriting recognition.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import numpy as np
import cv2
import uuid
import json
import os
import re
import base64
from typing import Optional
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

from app.models import (
    AnswerKeyRequest, FormGenerateRequest, ScanResponse,
    ExamSession, StatsResponse, CharFieldResult,
    Student, ClassRoster, RosterUploadRequest, VerificationRequest,
)
from app.omr_engine import OMREngine
from app.form_generator import generate_form_pdf
from app.qr_reader import read_qr_from_image
from app.ocr_engine import OCREngine
from app.storage import init_db, save_session, load_all_sessions, delete_session

app = FastAPI(
    title="OMR Scanner API",
    description="Optical Mark Recognition + Handwriting Recognition",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent storage — load saved sessions from SQLite on startup
init_db()
sessions: dict[str, ExamSession] = load_all_sessions()

FORMS_DIR = "/tmp/omr_forms"
os.makedirs(FORMS_DIR, exist_ok=True)


# =====================
# Health
# =====================

@app.get("/")
def root():
    return {"status": "OMR Scanner API v2", "version": "2.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


# =====================
# Form Generation
# =====================

@app.post("/api/forms/generate")
def generate_form(req: FormGenerateRequest):
    """Generate a printable OMR form PDF with character boxes + QR code."""
    try:
        filename = f"omr_form_{req.num_questions}q_{uuid.uuid4().hex[:6]}.pdf"
        filepath = os.path.join(FORMS_DIR, filename)

        generate_form_pdf(
            num_questions=req.num_questions,
            title=req.title,
            options=req.options,
            output_path=filepath,
            exam_id=req.exam_id,
            course_code=req.course_code,
            name_boxes=req.name_boxes,
            surname_boxes=req.surname_boxes,
            student_no_boxes=req.student_no_boxes,
            show_booklet=req.show_booklet,
        )

        return FileResponse(filepath, media_type="application/pdf", filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/forms/download/{num_questions}")
def download_default_form(num_questions: int = 40, options: str = "A,B,C,D,E",
                          show_booklet: bool = True, course_code: str = ""):
    """Download a default form."""
    if num_questions not in [20, 40]:
        raise HTTPException(400, "Supported: 20, 40 questions")

    opt_list = [o.strip() for o in options.split(",") if o.strip()]
    if not opt_list:
        opt_list = ["A", "B", "C", "D", "E"]

    code = course_code.strip()
    num_opts = len(opt_list)
    bk_suffix = "_nobk" if not show_booklet else ""
    code_suffix = f"_{code}" if code else ""
    filepath = os.path.join(FORMS_DIR, f"default_v4_{num_questions}q_{num_opts}opt{bk_suffix}{code_suffix}.pdf")
    # Always regenerate to pick up latest design changes
    generate_form_pdf(
        num_questions=num_questions,
        title=f"SINAV OPT\u0130K FORMU - {num_questions} SORU",
        options=opt_list,
        output_path=filepath,
        show_booklet=show_booklet,
        course_code=code,
    )
    fname = f"optik_form_{code}_{num_questions}q.pdf" if code else f"optik_form_{num_questions}q.pdf"
    return FileResponse(filepath, media_type="application/pdf",
                        filename=fname)


# =====================
# Sessions
# =====================

@app.post("/api/sessions/create")
def create_session(req: AnswerKeyRequest):
    """Create a new exam session with answer key."""
    session_id = uuid.uuid4().hex[:8]
    session = ExamSession(
        session_id=session_id,
        answer_key=req.answers,
        answer_key_b=req.answers_b,
        use_booklet=req.use_booklet,
        num_questions=req.num_questions,
        course_code=req.course_code,
        num_options=req.num_options,
    )
    sessions[session_id] = session
    save_session(session)
    return {
        "session_id": session_id,
        "num_questions": req.num_questions,
        "use_booklet": req.use_booklet,
        "course_code": req.course_code,
    }


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return sessions[session_id]


@app.get("/api/sessions")
def list_sessions():
    return [
        {
            "session_id": s.session_id,
            "course_code": s.course_code,
            "num_questions": s.num_questions,
            "num_options": s.num_options,
            "use_booklet": s.use_booklet,
            "scanned_count": len(s.results),
            "roster_count": len(s.roster.students),
        }
        for s in sessions.values()
    ]


@app.delete("/api/sessions/{session_id}")
def delete_session_endpoint(session_id: str):
    """Delete an exam session."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    del sessions[session_id]
    delete_session(session_id)
    return {"message": "Session deleted"}


@app.delete("/api/sessions/{session_id}/results/{result_index}")
def delete_result_endpoint(session_id: str, result_index: int):
    """Delete a single scan result from a session."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    session = sessions[session_id]
    if result_index < 0 or result_index >= len(session.results):
        raise HTTPException(404, "Result not found")
    session.results.pop(result_index)
    save_session(session)
    return {"message": "Result deleted"}


# =====================
# Class Roster
# =====================

@app.post("/api/sessions/{session_id}/roster")
def upload_roster(session_id: str, req: RosterUploadRequest):
    """Upload class roster (student list)."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    students = []
    for s in req.students:
        students.append(Student(
            name=s.get("name", "").upper().strip(),
            surname=s.get("surname", "").upper().strip(),
            student_number=str(s.get("student_number", "")).strip(),
        ))
    session.roster = ClassRoster(students=students)
    save_session(session)

    return {
        "message": f"{len(students)} students uploaded",
        "students": len(students),
    }


@app.get("/api/sessions/{session_id}/roster")
def get_roster(session_id: str):
    """Get class roster with grades."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    return sessions[session_id].roster


@app.post("/api/sessions/{session_id}/roster/pdf")
async def upload_roster_pdf(session_id: str, file: UploadFile = File(...)):
    """Parse a PDF class roster and extract student list."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    if not HAS_PDFPLUMBER:
        raise HTTPException(500, "PDF parsing not available")

    contents = await file.read()
    students = _parse_roster_pdf(contents)

    if not students:
        raise HTTPException(400, "PDF'den ogrenci bilgisi cikarilamamistir. "
                            "PDF'de tablo veya 'ad soyad numara' formati olmalidir.")

    session = sessions[session_id]
    # Append to existing roster (don't replace)
    existing = session.roster.students if session.roster else []
    existing_numbers = {s.student_number for s in existing}

    added = 0
    for s in students:
        if s.student_number and s.student_number in existing_numbers:
            continue  # skip duplicates
        existing.append(s)
        existing_numbers.add(s.student_number)
        added += 1

    session.roster = ClassRoster(students=existing)
    save_session(session)

    return {
        "message": f"{added} yeni ogrenci eklendi (toplam {len(existing)})",
        "added": added,
        "total": len(existing),
        "students": [
            {"name": s.name, "surname": s.surname, "student_number": s.student_number}
            for s in students
        ],
    }


def _parse_roster_pdf(pdf_bytes: bytes) -> list:
    """Extract student list from PDF. Tries table extraction first, then text."""
    students = []

    try:
        pdf_io = BytesIO(pdf_bytes)
        with pdfplumber.open(pdf_io) as pdf:
            # Try table extraction first
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or all(cell is None for cell in row):
                            continue
                        student = _parse_table_row(row)
                        if student:
                            students.append(student)

            # If no tables found, try text-based parsing
            if not students:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        for line in text.split("\n"):
                            student = _parse_text_line(line)
                            if student:
                                students.append(student)
    except Exception as e:
        raise HTTPException(400, f"PDF okuma hatasi: {str(e)}")

    return students


def _clean_student_name(text: str) -> str:
    """Remove admission type suffixes like ÖSYS, ÜNİ. YATAY GEÇİŞ ÖSYM PU, etc."""
    # Common admission type patterns in Turkish university rosters
    patterns = [
        r'\s*ÜNİ\.?\s*YATAY\s*GEÇİŞ\s*ÖSYM\s*PU\s*$',
        r'\s*YATAY\s*GEÇİŞ\s*ÖSYM\s*PU\s*$',
        r'\s*YATAY\s*GEÇİŞ\s*$',
        r'\s*DİKEY\s*GEÇİŞ\s*$',
        r'\s*\(?\s*ULUSLARARASI\s*\)?\s*$',
        r'\s*YÖS\s*(\(ULUSLARARASI\))?\s*$',
        r'\s*ÖSYS\s*$',
        r'\s*ÖSYM\s*$',
        r'\s*EK\s*MADDE\s*\d*\s*$',
        r'\s*EK\s*KONTENJAN\s*$',
        r'\s*AF\s*$',
    ]
    result = text.strip()
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
    return result


def _parse_table_row(row: list) -> Student | None:
    """Try to extract student data from a table row."""
    cells = [str(c).strip() if c else "" for c in row]
    cells = [c for c in cells if c]

    if len(cells) < 2:
        return None

    # Skip header rows
    header_words = {"ad", "soyad", "name", "surname", "no", "numara",
                    "ogrenci", "sira", "#", "student", "number"}
    if any(w in cells[0].lower() for w in header_words):
        return None

    # Find student number (9-digit number pattern)
    student_no = ""
    name = ""
    surname = ""

    for cell in cells:
        # Check if cell looks like a student number
        digits = re.sub(r'\D', '', cell)
        if len(digits) >= 6 and not student_no:
            student_no = digits
            continue

        # Skip pure numbers (like row index)
        if cell.isdigit() and len(cell) <= 3:
            continue

        # Remaining text cells are name/surname
        if not name:
            name = cell.upper()
        elif not surname:
            surname = cell.upper()

    if not name and not student_no:
        return None

    # If name contains space and no surname, split it
    if name and not surname and " " in name:
        parts = name.split(None, 1)
        name = parts[0]
        surname = " ".join(parts[1:]).upper() if len(parts) > 1 else ""

    # Clean admission type suffixes from names
    full_name = f"{name} {surname}".strip()
    full_name = _clean_student_name(full_name)
    parts = full_name.split()
    if not parts:
        return None
    surname = parts[-1] if len(parts) > 1 else ""
    name = " ".join(parts[:-1]) if len(parts) > 1 else parts[0]

    return Student(name=name, surname=surname, student_number=student_no)


def _parse_text_line(line: str) -> Student | None:
    """Try to extract student data from a text line."""
    line = line.strip()
    if len(line) < 3:
        return None

    # Skip headers
    lower = line.lower()
    if any(w in lower for w in ["ad", "soyad", "numara", "ogrenci", "sinif", "ders", "---"]):
        return None

    # Find numbers in line
    numbers = re.findall(r'\d{6,}', line)
    student_no = numbers[0] if numbers else ""

    # Remove the student number from line to get name parts
    text = re.sub(r'\d{3,}', '', line).strip()
    text = re.sub(r'[,;|\t]+', ' ', text).strip()

    # Remove leading index number (1. or 1)
    text = re.sub(r'^\d{1,3}[.\-)\s]+', '', text).strip()

    if not text:
        return None

    # Clean admission type suffixes
    text = _clean_student_name(text)

    parts = text.split()
    if len(parts) == 0:
        return None

    name = parts[0].upper()
    surname = " ".join(parts[1:]).upper() if len(parts) > 1 else ""

    if not name:
        return None

    return Student(name=name, surname=surname, student_number=student_no)


def _match_student_to_roster(session: ExamSession, scan_result: ScanResponse,
                             result_index: int):
    """Try to match a scanned student to the class roster."""
    if not session.roster.students:
        return

    student_no = ""
    if scan_result.student_number:
        student_no = scan_result.student_number.text

    student_name = ""
    if scan_result.student_name:
        student_name = scan_result.student_name.text

    student_surname = ""
    if scan_result.student_surname:
        student_surname = scan_result.student_surname.text

    # Try matching by student number first (most reliable)
    for student in session.roster.students:
        if student_no and student.student_number == student_no:
            student.score = scan_result.score
            student.correct_count = scan_result.correct_count
            student.total_questions = scan_result.total_questions
            student.scan_index = result_index
            return

    # Try matching by name+surname
    for student in session.roster.students:
        if (student_name and student_surname and
            student.name == student_name and
            student.surname == student_surname):
            student.score = scan_result.score
            student.correct_count = scan_result.correct_count
            student.total_questions = scan_result.total_questions
            student.scan_index = result_index
            return


# =====================
# Scanning
# =====================

def _process_scan(image: np.ndarray, answer_key: dict = None,
                  session_id: str = None, num_questions: int = 40,
                  answer_key_b: dict = None, use_booklet: bool = False,
                  num_options: int = 5) -> ScanResponse:
    """Core scan processing pipeline."""
    try:
        return _process_scan_inner(image, answer_key, session_id,
                                    num_questions, answer_key_b, use_booklet, num_options)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return ScanResponse(success=False, error=f"Sunucu hatası: {str(e)}")


def _process_scan_inner(image: np.ndarray, answer_key: dict = None,
                        session_id: str = None, num_questions: int = 40,
                        answer_key_b: dict = None, use_booklet: bool = False,
                        num_options: int = 5) -> ScanResponse:
    """Inner scan pipeline — errors caught by _process_scan wrapper."""

    # Step 1: Read QR code from raw image
    qr_data = read_qr_from_image(image)
    exam_id = None
    course_code = None
    if qr_data:
        exam_id = qr_data.get("exam_id")
        course_code = qr_data.get("course")
        if "q" in qr_data:
            num_questions = qr_data["q"]

    # Step 2: OMR scan (markers, transform, read answers)
    engine = OMREngine(num_questions=num_questions, num_options=num_options)
    # First scan without grading to detect booklet
    omr_result = engine.scan(image, answer_key=answer_key, debug=False)

    # Step 2.5: Detect booklet and re-grade if needed
    detected_booklet = "A"
    if use_booklet and engine.last_warped_gray is not None:
        detected_booklet = engine.read_booklet(engine.last_warped_gray)
        if detected_booklet == "B" and answer_key_b:
            # Re-grade with booklet B answer key
            omr_result = engine.scan(image, answer_key=answer_key_b, debug=False)

    if not omr_result.success:
        return ScanResponse(
            success=False,
            error=omr_result.error,
            exam_id=exam_id,
        )

    # Step 3: OCR - read character boxes
    ocr = OCREngine()
    # Use shadow-normalized grayscale for OCR (not raw, not CLAHE)
    # Normalized removes shadow gradients while preserving ink contrast
    warped = engine.last_warped_normalized if engine.last_warped_normalized is not None else engine.last_warped_gray_raw
    if warped is None:
        warped = engine.last_warped_gray

    # Pass roster to OCR engine for name/surname matching
    logger.info(f"OCR: session_id={session_id}, in_sessions={session_id in sessions if session_id else False}")
    if session_id and session_id in sessions:
        sess = sessions[session_id]
        has_roster = bool(sess.roster and sess.roster.students)
        logger.info(f"OCR: session found, has_roster={has_roster}, "
                     f"student_count={len(sess.roster.students) if has_roster else 0}")
        if has_roster:
            ocr.set_roster([
                {"name": s.name, "surname": s.surname,
                 "student_number": s.student_number}
                for s in sess.roster.students
            ])

    student_name_result = None
    student_surname_result = None
    student_number_result = None
    needs_review = False

    if warped is not None:
        # Read student_no first (Tesseract digits), then use it for name matching
        number_field = ocr.read_field(warped, "student_no")
        # Pass partial student_no to help name matching
        if number_field.text and number_field.text != "?":
            ocr._last_student_no = number_field.text
        name_field = ocr.read_field(warped, "name")
        surname_field = ocr.read_field(warped, "surname")

        # If we have a roster and the student number matched, use roster name/surname
        roster_name = ""
        roster_surname = ""
        matched_number = ""
        if session_id and session_id in sessions:
            sess = sessions[session_id]
            if sess.roster and sess.roster.students and number_field.text:
                ocr_no = number_field.text

                # 1. Exact match
                for s in sess.roster.students:
                    if s.student_number == ocr_no:
                        roster_name = s.name
                        roster_surname = s.surname
                        matched_number = s.student_number
                        break

                # 2. Wildcard match (? characters)
                if not roster_name and "?" in ocr_no:
                    for s in sess.roster.students:
                        sno = s.student_number.strip()
                        if len(sno) == len(ocr_no):
                            match = all(a == "?" or a == b for a, b in zip(ocr_no, sno))
                            if match:
                                roster_name = s.name
                                roster_surname = s.surname
                                matched_number = sno
                                break

                # 3. Fuzzy match — allow only 1 wrong digit for safety
                if not roster_name:
                    best_match = None
                    best_diff = 99
                    for s in sess.roster.students:
                        sno = s.student_number.strip()
                        if len(sno) != len(ocr_no):
                            continue
                        diff = sum(1 for a, b in zip(ocr_no, sno) if a != "?" and a != b)
                        if diff < best_diff:
                            best_diff = diff
                            best_match = s

                    # Accept fuzzy match only if unique with exactly 1 difference
                    if best_match and best_diff == 1:
                        same_diff_count = sum(
                            1 for s in sess.roster.students
                            if len(s.student_number.strip()) == len(ocr_no)
                            and sum(1 for a, b in zip(ocr_no, s.student_number.strip()) if a != "?" and a != b) == 1
                        )
                        if same_diff_count == 1:
                            roster_name = best_match.name
                            roster_surname = best_match.surname
                            matched_number = best_match.student_number
                            logger.info(f"Fuzzy roster match: '{ocr_no}' -> '{matched_number}' "
                                         f"(diff={best_diff})")

                if matched_number:
                    number_field.text = matched_number
                    number_field.avg_confidence = max(number_field.avg_confidence, 0.7)

        final_name = roster_name if roster_name else name_field.text
        final_surname = roster_surname if roster_surname else surname_field.text
        name_conf = 0.95 if roster_name else name_field.avg_confidence
        surname_conf = 0.95 if roster_surname else surname_field.avg_confidence

        student_name_result = CharFieldResult(
            text=final_name,
            confidence=name_conf,
            needs_review=not roster_name and name_field.needs_review,
            char_confidences=[name_conf] * max(len(final_name), 1),
        )
        student_surname_result = CharFieldResult(
            text=final_surname,
            confidence=surname_conf,
            needs_review=not roster_surname and surname_field.needs_review,
            char_confidences=[surname_conf] * max(len(final_surname), 1),
        )
        student_number_result = CharFieldResult(
            text=number_field.text,
            confidence=number_field.avg_confidence,
            needs_review=number_field.needs_review,
            char_confidences=number_field.char_confidences,
        )

        needs_review = (student_name_result.needs_review or
                        student_surname_result.needs_review or
                        number_field.needs_review)

    # Step 4: Encode form image (always save for later review)
    form_image_b64 = None
    warped_color = engine.last_warped  # color version for display
    if warped_color is not None:
        _, buffer = cv2.imencode(".jpg", warped_color, [cv2.IMWRITE_JPEG_QUALITY, 92])
        form_image_b64 = base64.b64encode(buffer).decode("utf-8")

    response = ScanResponse(
        success=True,
        student_id=omr_result.student_id,
        student_name=student_name_result,
        student_surname=student_surname_result,
        student_number=student_number_result,
        booklet=detected_booklet if use_booklet else None,
        exam_id=exam_id,
        course_code=course_code,
        answers=omr_result.answers,
        score=omr_result.score,
        correct_count=omr_result.correct_count,
        total_questions=omr_result.total_questions,
        confidence=omr_result.confidence,
        error=omr_result.error,
        unmarked=omr_result.unmarked,
        multiple_marks=omr_result.multiple_marks,
        needs_review=needs_review,
        form_image_base64=form_image_b64,
    )

    return response


@app.post("/api/scan", response_model=ScanResponse)
async def scan_sheet(
    image: UploadFile = File(...),
    answer_key: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    num_questions: int = Form(40),
):
    """Scan an answer sheet image (file upload)."""
    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(400, "Invalid image file")

    key = None
    key_b = None
    use_bk = False
    num_opts = 5
    if session_id and session_id in sessions:
        s = sessions[session_id]
        key = s.answer_key
        key_b = s.answer_key_b
        use_bk = s.use_booklet
        num_questions = s.num_questions
        num_opts = s.num_options
    elif answer_key:
        try:
            key = json.loads(answer_key)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid answer_key JSON")

    response = _process_scan(img, key, session_id, num_questions, key_b, use_bk, num_opts)

    if session_id and session_id in sessions:
        session = sessions[session_id]
        result_idx = len(session.results)
        session.results.append(response)
        if response.needs_review:
            session.pending_review.append(result_idx)
        if response.success:
            _match_student_to_roster(session, response, result_idx)
        save_session(session)

    return response


@app.post("/api/scan/base64", response_model=ScanResponse)
async def scan_sheet_base64(
    image_base64: str = Form(...),
    answer_key: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    num_questions: int = Form(40),
):
    """Scan from base64-encoded image (camera capture)."""
    try:
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        img_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception:
        raise HTTPException(400, "Invalid base64 image")

    if img is None:
        raise HTTPException(400, "Could not decode image")

    key = None
    key_b = None
    use_bk = False
    num_opts = 5
    if session_id and session_id in sessions:
        s = sessions[session_id]
        key = s.answer_key
        key_b = s.answer_key_b
        use_bk = s.use_booklet
        num_questions = s.num_questions
        num_opts = s.num_options
    elif answer_key:
        try:
            key = json.loads(answer_key)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid answer_key JSON")

    response = _process_scan(img, key, session_id, num_questions, key_b, use_bk, num_opts)

    if session_id and session_id in sessions:
        session = sessions[session_id]
        result_idx = len(session.results)
        session.results.append(response)
        if response.needs_review:
            session.pending_review.append(result_idx)
        if response.success:
            _match_student_to_roster(session, response, result_idx)
        save_session(session)

    return response


# =====================
# Verification
# =====================

@app.get("/api/sessions/{session_id}/review")
def get_pending_reviews(session_id: str):
    """Get scan results that need manual review."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    reviews = []
    for idx in session.pending_review:
        if idx < len(session.results):
            reviews.append({
                "index": idx,
                "result": session.results[idx],
            })
    return reviews


@app.post("/api/sessions/{session_id}/verify")
def verify_result(session_id: str, req: VerificationRequest):
    """Teacher verification/correction of OCR results."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    idx = req.result_index

    if idx < 0 or idx >= len(session.results):
        raise HTTPException(400, "Invalid result index")

    result = session.results[idx]

    # Update with corrections
    if req.student_name is not None and result.student_name:
        result.student_name.text = req.student_name.upper()
        result.student_name.needs_review = False
    if req.student_surname is not None and result.student_surname:
        result.student_surname.text = req.student_surname.upper()
        result.student_surname.needs_review = False
    if req.student_number is not None and result.student_number:
        result.student_number.text = req.student_number
        result.student_number.needs_review = False

    if req.approved:
        result.needs_review = False
        if idx in session.pending_review:
            session.pending_review.remove(idx)
        # Re-match to roster with corrected data
        _match_student_to_roster(session, result, idx)

    save_session(session)
    return {"message": "Verified", "index": idx}


# =====================
# Results & Stats
# =====================

@app.get("/api/sessions/{session_id}/stats", response_model=StatsResponse)
def get_stats(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    results = [r for r in session.results if r.success and r.score is not None]

    if not results:
        return StatsResponse()

    scores = [r.score for r in results]

    distribution = {}
    for s in scores:
        bucket = f"{int(s // 10) * 10}-{int(s // 10) * 10 + 9}"
        distribution[bucket] = distribution.get(bucket, 0) + 1

    question_stats = {}
    answer_key = session.answer_key
    for q_num_str, correct_ans in answer_key.items():
        q_num = int(q_num_str)
        correct_count = sum(
            1 for r in results
            if r.answers.get(q_num, "").upper() == correct_ans.upper()
        )
        question_stats[q_num] = {
            "correct_rate": correct_count / len(results),
            "correct_count": correct_count,
        }

    return StatsResponse(
        total_students=len(results),
        average_score=sum(scores) / len(scores),
        highest_score=max(scores),
        lowest_score=min(scores),
        score_distribution=distribution,
        question_stats=question_stats,
    )


@app.get("/api/sessions/{session_id}/export")
def export_results(session_id: str):
    """Export results as CSV with student info."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    lines = ["student_name,student_surname,student_number,score,correct,total,confidence,needs_review"]

    for r in session.results:
        if r.success:
            name = r.student_name.text if r.student_name else ""
            surname = r.student_surname.text if r.student_surname else ""
            number = r.student_number.text if r.student_number else ""
            lines.append(
                f"{name},{surname},{number},{r.score:.1f},{r.correct_count},"
                f"{r.total_questions},{r.confidence:.2f},{r.needs_review}"
            )

    csv_content = "\n".join(lines)
    filepath = os.path.join(FORMS_DIR, f"results_{session_id}.csv")
    with open(filepath, "w") as f:
        f.write(csv_content)

    return FileResponse(filepath, media_type="text/csv",
                        filename=f"results_{session_id}.csv")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
