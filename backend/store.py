import time
from dataclasses import dataclass, field
from typing import Dict, List

from fastapi import HTTPException


@dataclass
class InterviewSession:
    session_id: str
    role: str
    difficulty: str
    interview_type: str
    job_description: str
    num_questions: int
    current_question: str = ""
    asked: List[str] = field(default_factory=list)
    qa: List[dict] = field(default_factory=list)  # [{question, answer, evaluation}]
    created_at: float = field(default_factory=time.time)


# In-memory session store. Cleared when the backend restarts.
SESSIONS: Dict[str, InterviewSession] = {}


def save_session(session: InterviewSession) -> None:
    SESSIONS[session.session_id] = session


def get_session(session_id: str) -> InterviewSession:
    session = SESSIONS.get(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Interview session not found or expired. Please start a new interview.",
        )
    return session
