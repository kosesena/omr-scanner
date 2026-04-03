"""Pydantic models for OMR Scanner API."""

from pydantic import BaseModel, Field
from typing import Optional


class AnswerKeyRequest(BaseModel):
    """Answer key for grading."""
    answers: dict = Field(..., example={"1": "A", "2": "B", "3": "C"})
    answers_b: Optional[dict] = None  # Booklet B answer key
    use_booklet: bool = False
    num_questions: int = Field(40, ge=1, le=200)


class FormGenerateRequest(BaseModel):
    """Request to generate a new OMR form."""
    num_questions: int = Field(40, ge=5, le=200)
    title: str = Field("SINAV OPTIK FORMU", max_length=100)
    options: list[str] = Field(default=["A", "B", "C", "D", "E"])
    exam_id: Optional[str] = None
    course_code: str = Field("", max_length=30)
    name_boxes: int = Field(20, ge=10, le=30)
    surname_boxes: int = Field(20, ge=10, le=30)
    student_no_boxes: int = Field(10, ge=5, le=15)
    show_booklet: bool = Field(True)


class CharFieldResult(BaseModel):
    """Result of reading a handwritten character field."""
    text: str = ""
    confidence: float = 0.0
    needs_review: bool = False
    char_confidences: list[float] = []


class ScanResponse(BaseModel):
    """Response from scanning an answer sheet."""
    success: bool
    # Student info from OCR
    student_id: str = ""
    student_name: Optional[CharFieldResult] = None
    student_surname: Optional[CharFieldResult] = None
    student_number: Optional[CharFieldResult] = None
    # QR metadata
    exam_id: Optional[str] = None
    course_code: Optional[str] = None
    # Booklet
    booklet: Optional[str] = None  # "A" or "B"
    # Answers
    answers: dict = {}
    score: Optional[float] = None
    correct_count: int = 0
    total_questions: int = 0
    confidence: float = 0.0
    error: str = ""
    unmarked: list[int] = []
    multiple_marks: list[int] = []
    # Review
    needs_review: bool = False
    form_image_base64: Optional[str] = None


class Student(BaseModel):
    """A student in a class roster."""
    name: str = ""
    surname: str = ""
    student_number: str = ""
    score: Optional[float] = None
    correct_count: int = 0
    total_questions: int = 0
    scan_index: Optional[int] = None  # index in session results
    verified: bool = False


class ClassRoster(BaseModel):
    """Class roster / student list."""
    students: list[Student] = []


class ExamSession(BaseModel):
    """An exam session with answer key, class roster and results."""
    session_id: str
    answer_key: dict
    answer_key_b: Optional[dict] = None  # Booklet B
    use_booklet: bool = False
    num_questions: int
    results: list[ScanResponse] = []
    # New fields
    exam_id: Optional[str] = None
    course_code: str = ""
    roster: ClassRoster = ClassRoster()
    pending_review: list[int] = []


class VerificationRequest(BaseModel):
    """Teacher correction of OCR results."""
    result_index: int
    student_name: Optional[str] = None
    student_surname: Optional[str] = None
    student_number: Optional[str] = None
    approved: bool = False


class RosterUploadRequest(BaseModel):
    """Upload a class roster."""
    students: list[dict] = Field(
        ...,
        example=[
            {"name": "SENA", "surname": "KOSE", "student_number": "214501"},
            {"name": "ALI", "surname": "YILMAZ", "student_number": "214502"},
        ]
    )


class StatsResponse(BaseModel):
    """Statistics for an exam session."""
    total_students: int = 0
    average_score: float = 0.0
    highest_score: float = 0.0
    lowest_score: float = 0.0
    score_distribution: dict = {}
    question_stats: dict = {}
