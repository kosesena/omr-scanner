"""Pydantic models for OMR Scanner API."""

from pydantic import BaseModel, Field
from typing import Optional


class AnswerKeyRequest(BaseModel):
    """Answer key for grading."""
    answers: dict = Field(..., example={"1": "A", "2": "B", "3": "C"})
    num_questions: int = Field(40, ge=1, le=200)


class FormGenerateRequest(BaseModel):
    """Request to generate a new OMR form."""
    num_questions: int = Field(40, ge=5, le=200)
    num_id_digits: int = Field(10, ge=4, le=15)
    title: str = Field("SINAV OPTIK FORMU", max_length=100)
    options: list[str] = Field(default=["A", "B", "C", "D", "E"])


class ScanResponse(BaseModel):
    """Response from scanning an answer sheet."""
    success: bool
    student_id: str = ""
    answers: dict = {}
    score: Optional[float] = None
    correct_count: int = 0
    total_questions: int = 0
    confidence: float = 0.0
    error: str = ""
    unmarked: list[int] = []
    multiple_marks: list[int] = []


class ExamSession(BaseModel):
    """An exam session with answer key and results."""
    session_id: str
    answer_key: dict
    num_questions: int
    results: list[ScanResponse] = []


class StatsResponse(BaseModel):
    """Statistics for an exam session."""
    total_students: int = 0
    average_score: float = 0.0
    highest_score: float = 0.0
    lowest_score: float = 0.0
    score_distribution: dict = {}
    question_stats: dict = {}  # per-question correct rate
