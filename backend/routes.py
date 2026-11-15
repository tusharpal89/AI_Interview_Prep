import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import settings
from backend.llm_client import (
    LLMError,
    evaluate_answer,
    generate_question,
    generate_report,
    is_key_configured,
)
from backend.schemas import (
    AnswerRequest,
    AnswerResponse,
    Evaluation,
    HealthResponse,
    QAItem,
    ReportResponse,
    StartRequest,
    StartResponse,
    TranscribeResponse,
)
from backend.store import InterviewSession, get_session, save_session
from backend.stt import STTError, transcribe_audio

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
        llm_key_configured=is_key_configured(),
    )


@router.post("/start", response_model=StartResponse)
def start(request: StartRequest) -> StartResponse:
    if not request.role.strip():
        raise HTTPException(status_code=400, detail="A role is required.")

    session = InterviewSession(
        session_id=uuid.uuid4().hex,
        role=request.role.strip(),
        difficulty=request.difficulty,
        interview_type=request.interview_type,
        job_description=request.job_description,
        num_questions=request.num_questions,
    )
    try:
        question = generate_question(
            session.role, session.difficulty, session.interview_type,
            asked=[], job_description=session.job_description,
        )
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}") from e

    session.current_question = question
    save_session(session)
    return StartResponse(
        session_id=session.session_id, question=question, index=1, total=session.num_questions
    )


@router.post("/answer", response_model=AnswerResponse)
def answer(request: AnswerRequest) -> AnswerResponse:
    session = get_session(request.session_id)
    if not session.current_question:
        raise HTTPException(status_code=400, detail="No active question for this session.")

    try:
        evaluation = evaluate_answer(session.role, session.current_question, request.answer)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}") from e

    session.qa.append(
        {"question": session.current_question, "answer": request.answer.strip(), "evaluation": evaluation}
    )
    session.asked.append(session.current_question)

    done = len(session.qa) >= session.num_questions
    next_question = None
    if not done:
        try:
            next_question = generate_question(
                session.role, session.difficulty, session.interview_type,
                asked=session.asked, job_description=session.job_description,
                previous_answer=request.answer,
            )
        except LLMError as e:
            raise HTTPException(status_code=502, detail=f"LLM error: {e}") from e
        session.current_question = next_question
    else:
        session.current_question = ""

    save_session(session)
    return AnswerResponse(
        evaluation=Evaluation(**evaluation),
        next_question=next_question,
        index=len(session.qa) + (0 if done else 1),
        total=session.num_questions,
        done=done,
    )


@router.post("/transcribe", response_model=TranscribeResponse)
def transcribe(file: UploadFile = File(...)) -> TranscribeResponse:
    file_bytes = file.file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(status_code=400, detail=f"Audio exceeds the {settings.MAX_UPLOAD_MB}MB limit.")
    try:
        text = transcribe_audio(file_bytes, file.filename or "answer.webm")
    except STTError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return TranscribeResponse(text=text)


@router.get("/report/{session_id}", response_model=ReportResponse)
def report(session_id: str) -> ReportResponse:
    session = get_session(session_id)
    if not session.qa:
        raise HTTPException(status_code=400, detail="No answers recorded yet.")
    try:
        rep = generate_report(session.role, session.qa)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {e}") from e

    questions = [
        QAItem(
            question=item["question"],
            answer=item["answer"],
            score=item["evaluation"]["score"],
            verdict=item["evaluation"]["verdict"],
        )
        for item in session.qa
    ]
    return ReportResponse(role=session.role, questions=questions, **rep)
