from typing import List, Optional

from pydantic import BaseModel, Field


class StartRequest(BaseModel):
    role: str
    difficulty: str = "Mid"
    interview_type: str = "Mixed"
    num_questions: int = Field(default=5, ge=1, le=15)
    job_description: str = ""


class StartResponse(BaseModel):
    session_id: str
    question: str
    index: int
    total: int


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class Evaluation(BaseModel):
    score: int
    verdict: str
    strengths: List[str]
    improvements: List[str]
    ideal_answer: str


class AnswerResponse(BaseModel):
    evaluation: Evaluation
    next_question: Optional[str] = None
    index: int
    total: int
    done: bool


class TranscribeResponse(BaseModel):
    text: str


class QAItem(BaseModel):
    question: str
    answer: str
    score: int
    verdict: str


class ReportResponse(BaseModel):
    role: str
    overall_score: float
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    tips: List[str]
    questions: List[QAItem]


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    llm_model: str
    llm_key_configured: bool
