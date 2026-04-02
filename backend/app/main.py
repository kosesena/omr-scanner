"""
OMR Scanner API
FastAPI backend for optical mark recognition.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import numpy as np
import cv2
import uuid
import json
import os
import base64
from typing import Optional

from app.models import (
    AnswerKeyRequest, FormGenerateRequest, ScanResponse,
    ExamSession, StatsResponse
)
from app.omr_engine import OMREngine
from app.form_generator import generate_form_pdf

app = FastAPI(
    title="OMR Scanner API",
    description="Optical Mark Recognition - Scan and grade answer sheets",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage
sessions: dict[str, ExamSession] = {}

# Ensure output directory
FORMS_DIR = "/tmp/omr_forms"
os.makedirs(FORMS_DIR, exist_ok=True)


@app.get("/")
def root():
    return {"status": "OMR Scanner API is running", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


# =====================
# Form Generation
# =====================

@app.post("/api/forms/generate")
def generate_form(req: FormGenerateRequest):
    """Generate a printable OMR form PDF."""
    try:
        filename = f"omr_form_{req.num_questions}q_{uuid.uuid4().hex[:6]}.pdf"
        filepath = os.path.join(FORMS_DIR, filename)

        generate_form_pdf(
            num_questions=req.num_questions,
            num_id_digits=req.num_id_digits,
            title=req.title,
            options=req.options,
            output_path=filepath,
        )

        return FileResponse(
            filepath,
            media_type="application/pdf",
            filename=filename,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/forms/download/{num_questions}")
def download_default_form(num_questions: int = 40):
    """Download a default form with specified question count."""
    if num_questions not in [20, 40, 60, 80, 100]:
        raise HTTPException(400, "Supported: 20, 40, 60, 80, 100 questions")

    filepath = os.path.join(FORMS_DIR, f"default_{num_questions}q.pdf")
    if not os.path.exists(filepath):
        generate_form_pdf(
            num_questions=num_questions,
            title=f"SINAV OPTIK FORMU - {num_questions} SORU",
            output_path=filepath,
        )
    return FileResponse(filepath, media_type="application/pdf",
                        filename=f"optik_form_{num_questions}q.pdf")


# =====================
# Exam Sessions
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
    """Get session details and results."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    session = sessions[session_id]
    return session


@app.get("/api/sessions")
def list_sessions():
    """List all sessions."""
    return [
        {
            "session_id": s.session_id,
            "num_questions": s.num_questions,
            "scanned_count": len(s.results),
        }
        for s in sessions.values()
    ]


# =====================
# Scanning
# =====================

@app.post("/api/scan", response_model=ScanResponse)
async def scan_sheet(
    image: UploadFile = File(...),
    answer_key: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    num_questions: int = Form(40),
):
    """
    Scan an answer sheet image.

    - Upload image file (JPG/PNG)
    - Optionally provide answer_key as JSON string
    - Or provide session_id to use session's answer key
    """
    # Read image
    contents = await image.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise HTTPException(400, "Invalid image file")

    # Determine answer key
    key = None
    if session_id and session_id in sessions:
        key = sessions[session_id].answer_key
        num_questions = sessions[session_id].num_questions
    elif answer_key:
        try:
            key = json.loads(answer_key)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid answer_key JSON")

    # Run OMR
    engine = OMREngine(num_questions=num_questions)
    result = engine.scan(img, answer_key=key, debug=False)

    response = ScanResponse(
        success=result.success,
        student_id=result.student_id,
        answers=result.answers,
        score=result.score,
        correct_count=result.correct_count,
        total_questions=result.total_questions,
        confidence=result.confidence,
        error=result.error,
        unmarked=result.unmarked,
        multiple_marks=result.multiple_marks,
    )

    # Save to session if provided
    if session_id and session_id in sessions:
        sessions[session_id].results.append(response)

    return response


@app.post("/api/scan/base64", response_model=ScanResponse)
async def scan_sheet_base64(
    image_base64: str = Form(...),
    answer_key: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    num_questions: int = Form(40),
):
    """
    Scan from base64-encoded image (for camera capture from frontend).
    """
    try:
        # Remove data URL prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",")[1]
        img_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    except Exception:
        raise HTTPException(400, "Invalid base64 image")

    if img is None:
        raise HTTPException(400, "Could not decode image")

    # Same logic as file upload scan
    key = None
    if session_id and session_id in sessions:
        key = sessions[session_id].answer_key
        num_questions = sessions[session_id].num_questions
    elif answer_key:
        try:
            key = json.loads(answer_key)
        except json.JSONDecodeError:
            raise HTTPException(400, "Invalid answer_key JSON")

    engine = OMREngine(num_questions=num_questions)
    result = engine.scan(img, answer_key=key, debug=False)

    response = ScanResponse(
        success=result.success,
        student_id=result.student_id,
        answers=result.answers,
        score=result.score,
        correct_count=result.correct_count,
        total_questions=result.total_questions,
        confidence=result.confidence,
        error=result.error,
        unmarked=result.unmarked,
        multiple_marks=result.multiple_marks,
    )

    if session_id and session_id in sessions:
        sessions[session_id].results.append(response)

    return response


# =====================
# Results & Stats
# =====================

@app.get("/api/sessions/{session_id}/stats", response_model=StatsResponse)
def get_stats(session_id: str):
    """Get statistics for an exam session."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    results = [r for r in session.results if r.success and r.score is not None]

    if not results:
        return StatsResponse()

    scores = [r.score for r in results]

    # Score distribution (buckets of 10)
    distribution = {}
    for s in scores:
        bucket = f"{int(s // 10) * 10}-{int(s // 10) * 10 + 9}"
        distribution[bucket] = distribution.get(bucket, 0) + 1

    # Per-question correct rate
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
    """Export results as CSV."""
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    lines = ["student_id,score,correct,total,confidence"]

    for r in session.results:
        if r.success:
            lines.append(
                f"{r.student_id},{r.score:.1f},{r.correct_count},"
                f"{r.total_questions},{r.confidence:.2f}"
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
