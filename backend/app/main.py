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

# In-memory storage
sessions: dict[str, ExamSession] = {}

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
        )

        return FileResponse(filepath, media_type="application/pdf", filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/forms/download/{num_questions}")
def download_default_form(num_questions: int = 40, options: str = "A,B,C,D,E"):
    """Download a default form."""
    if num_questions not in [20, 40]:
        raise HTTPException(400, "Supported: 20, 40 questions")

    opt_list = [o.strip() for o in options.split(",") if o.strip()]
    if not opt_list:
        opt_list = ["A", "B", "C", "D", "E"]

    num_opts = len(opt_list)
    filepath = os.path.join(FORMS_DIR, f"default_v3_{num_questions}q_{num_opts}opt.pdf")
    if not os.path.exists(filepath):
        generate_form_pdf(
            num_questions=num_questions,
            title=f"SINAV OPT\u0130K FORMU - {num_questions} SORU",
            options=opt_list,
            output_path=filepath,
        )
    return FileResponse(filepath, media_type="application/pdf",
                        filename=f"optik_form_{num_questions}q.pdf")


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
        num_questions=req.num_questions,
    )
    sessions[session_id] = session
    return {"session_id": session_id, "num_questions": req.num_questions}


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
            "num_questions": s.num_questions,
            "scanned_count": len(s.results),
            "roster_count": len(s.roster.students),
        }
        for s in sessions.values()
    ]


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
        surname = parts[1] if len(parts) > 1 else ""

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
                  session_id: str = None, num_questions: int = 40) -> ScanResponse:
    """Core scan processing pipeline."""

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
    engine = OMREngine(num_questions=num_questions)
    omr_result = engine.scan(image, answer_key=answer_key, debug=False)

    if not omr_result.success:
        return ScanResponse(
            success=False,
            error=omr_result.error,
            exam_id=exam_id,
        )

    # Step 3: OCR - read character boxes
    ocr = OCREngine()
    warped = engine.last_warped_gray  # get from engine after scan

    student_name_result = None
    student_surname_result = None
    student_number_result = None
    needs_review = False

    if warped is not None:
        name_field = ocr.read_field(warped, "name")
        surname_field = ocr.read_field(warped, "surname")
        number_field = ocr.read_field(warped, "student_no")

        student_name_result = CharFieldResult(
            text=name_field.text,
            confidence=name_field.avg_confidence,
            needs_review=name_field.needs_review,
            char_confidences=name_field.char_confidences,
        )
        student_surname_result = CharFieldResult(
            text=surname_field.text,
            confidence=surname_field.avg_confidence,
            needs_review=surname_field.needs_review,
            char_confidences=surname_field.char_confidences,
        )
        student_number_result = CharFieldResult(
            text=number_field.text,
            confidence=number_field.avg_confidence,
            needs_review=number_field.needs_review,
            char_confidences=number_field.char_confidences,
        )

        needs_review = (name_field.needs_review or
                        surname_field.needs_review or
                        number_field.needs_review)

    # Step 4: Encode form image for review if needed
    form_image_b64 = None
    if needs_review and warped is not None:
        _, buffer = cv2.imencode(".jpg", warped, [cv2.IMWRITE_JPEG_QUALITY, 60])
        form_image_b64 = base64.b64encode(buffer).decode("utf-8")

    response = ScanResponse(
        success=True,
        student_id=omr_result.student_id,
        student_name=student_name_result,
        student_surname=student_surname_result,
        student_number=student_number_result,
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
    if session_id and session_id in sessions:
        key = sessions[session_id].answer_key
        num_questions = sessions[session_id].num_questions
    elif answer_key:
        try:
            key = json.loads(answer_key)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid answer_key JSON")

    response = _process_scan(img, key, session_id, num_questions)

    if session_id and session_id in sessions:
        session = sessions[session_id]
        result_idx = len(session.results)
        session.results.append(response)
        if response.needs_review:
            session.pending_review.append(result_idx)
        if response.success:
            _match_student_to_roster(session, response, result_idx)

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
    if session_id and session_id in sessions:
        key = sessions[session_id].answer_key
        num_questions = sessions[session_id].num_questions
    elif answer_key:
        try:
            key = json.loads(answer_key)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid answer_key JSON")

    response = _process_scan(img, key, session_id, num_questions)

    if session_id and session_id in sessions:
        session = sessions[session_id]
        result_idx = len(session.results)
        session.results.append(response)
        if response.needs_review:
            session.pending_review.append(result_idx)
        if response.success:
            _match_student_to_roster(session, response, result_idx)

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
