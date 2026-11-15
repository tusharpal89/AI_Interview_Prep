"""Provider-agnostic LLM client (OpenAI SDK against any compatible API).

Switch providers via .env:
  - groq    -> Groq (fast + free) through its OpenAI-compatible endpoint
  - gemini  -> Google Gemini
  - openai  -> OpenAI
  - ollama  -> a local Ollama server
"""
import functools
import json
import re
import time
from typing import Dict, List

from openai import OpenAI

from backend.config import settings


class LLMError(Exception):
    pass


_PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
    "openai": None,
    "ollama": "http://localhost:11434/v1",
}


def _is_real_key(key: str) -> bool:
    key = (key or "").strip()
    return bool(key) and not key.lower().startswith("your_")


def _resolve_base_url():
    if settings.LLM_BASE_URL:
        return settings.LLM_BASE_URL
    return _PROVIDER_BASE_URLS.get(settings.LLM_PROVIDER)


def _resolve_api_key() -> str:
    provider = settings.LLM_PROVIDER
    if provider == "groq":
        if not _is_real_key(settings.GROQ_API_KEY):
            raise LLMError(
                "GROQ_API_KEY is not set. Get a free key at "
                "https://console.groq.com/keys and add it to your .env file."
            )
        return settings.GROQ_API_KEY
    if provider == "gemini":
        if not _is_real_key(settings.GEMINI_API_KEY):
            raise LLMError(
                "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey."
            )
        return settings.GEMINI_API_KEY
    if provider == "openai":
        if not _is_real_key(settings.OPENAI_API_KEY):
            raise LLMError("OPENAI_API_KEY is not set in your .env file.")
        return settings.OPENAI_API_KEY
    if provider == "ollama":
        return "ollama"
    raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. Use groq, gemini, openai or ollama.")


def is_key_configured() -> bool:
    try:
        _resolve_api_key()
        return True
    except LLMError:
        return False


@functools.lru_cache(maxsize=1)
def get_client() -> OpenAI:
    base_url = _resolve_base_url()
    api_key = _resolve_api_key()
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url, timeout=90.0)
    return OpenAI(api_key=api_key, timeout=90.0)


_TRANSIENT_HINTS = (
    "503", "502", "429", "unavailable", "resource_exhausted",
    "high demand", "overloaded", "rate limit", "try again",
)


def _is_transient(error: Exception) -> bool:
    msg = str(error).lower()
    return any(hint in msg for hint in _TRANSIENT_HINTS)


def _create(**kwargs):
    last_error = None
    for attempt in range(3):
        try:
            return get_client().chat.completions.create(**kwargs)
        except Exception as e:
            last_error = e
            if _is_transient(e) and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    raise last_error


def _chat(messages, temperature=0.4, json_mode=False, max_tokens=1024) -> str:
    base_kwargs = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        if json_mode:
            try:
                resp = _create(**base_kwargs, response_format={"type": "json_object"})
            except Exception as e:
                if _is_transient(e):
                    raise
                resp = _create(**base_kwargs)
        else:
            resp = _create(**base_kwargs)
    except Exception as e:
        raise LLMError(str(e)) from e

    content = resp.choices[0].message.content
    if not content:
        raise LLMError("The LLM returned an empty response.")
    return content


def _safe_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    raise LLMError("Failed to parse the LLM's JSON response.")


# --------------------------------------------------------------------------- #
# Features
# --------------------------------------------------------------------------- #
def generate_question(
    role: str,
    difficulty: str,
    interview_type: str,
    asked: List[str],
    job_description: str = "",
    previous_answer: str = "",
) -> str:
    rules = (
        f"You are an expert interviewer conducting a {interview_type.lower()} interview for a "
        f"{difficulty} {role} position. Ask exactly ONE clear, realistic interview question. "
        "Keep it concise (1-3 sentences). Do NOT number it, do NOT add any preamble, commentary "
        "or answer — return only the question text."
    )
    context = ""
    if job_description.strip():
        context += f"\n\nJob description to tailor questions to:\n{job_description.strip()[:1500]}"
    if asked:
        joined = "\n".join(f"- {q}" for q in asked)
        context += f"\n\nAlready-asked questions (ask something DIFFERENT):\n{joined}"
    if previous_answer.strip():
        context += (
            f"\n\nThe candidate's previous answer was:\n{previous_answer.strip()[:800]}\n"
            "You may ask a natural follow-up, or move to a new topic."
        )
    messages = [
        {"role": "system", "content": rules},
        {"role": "user", "content": f"Generate the next interview question.{context}"},
    ]
    question = _chat(messages, temperature=0.7, max_tokens=200).strip()
    # strip wrapping quotes / leading numbering if the model adds them anyway
    question = re.sub(r'^\s*(\d+[\).]|Q:|Question:)\s*', "", question).strip().strip('"')
    return question


def evaluate_answer(role: str, question: str, answer: str) -> Dict:
    answer = (answer or "").strip()
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a seasoned interviewer evaluating a candidate's answer for a {role} role. "
                "Be fair, specific and constructive. If the answer is empty or off-topic, score it low. "
                'Respond with STRICT JSON: {"score": <integer 0-10>, "verdict": "<one-sentence verdict>", '
                '"strengths": ["..."], "improvements": ["..."], "ideal_answer": "<a concise model answer>"}.'
            ),
        },
        {
            "role": "user",
            "content": f"Question:\n{question}\n\nCandidate's answer:\n{answer or '(no answer given)'}",
        },
    ]
    raw = _chat(messages, temperature=0.2, json_mode=True, max_tokens=900)
    data = _safe_json(raw)
    try:
        score = int(round(float(data.get("score", 0))))
    except (ValueError, TypeError):
        score = 0
    score = max(0, min(10, score))
    return {
        "score": score,
        "verdict": str(data.get("verdict", "")).strip(),
        "strengths": [str(s) for s in (data.get("strengths") or [])],
        "improvements": [str(s) for s in (data.get("improvements") or [])],
        "ideal_answer": str(data.get("ideal_answer", "")).strip(),
    }


def generate_report(role: str, qa: List[dict]) -> Dict:
    transcript = "\n\n".join(
        f"Q{i + 1}: {item['question']}\n"
        f"Answer: {item['answer'] or '(no answer)'}\n"
        f"Score: {item['evaluation']['score']}/10"
        for i, item in enumerate(qa)
    )
    messages = [
        {
            "role": "system",
            "content": (
                f"You are an interviewer writing a final assessment for a {role} candidate based on "
                "their full interview below. Respond with STRICT JSON: "
                '{"overall_score": <number 0-10>, "summary": "<2-3 sentence overall assessment>", '
                '"strengths": ["..."], "weaknesses": ["..."], "tips": ["<actionable prep tips>"]}.'
            ),
        },
        {"role": "user", "content": f"Interview transcript:\n{transcript}"},
    ]
    raw = _chat(messages, temperature=0.3, json_mode=True, max_tokens=900)
    data = _safe_json(raw)
    try:
        overall = round(float(data.get("overall_score", 0)), 1)
    except (ValueError, TypeError):
        overall = 0.0
    return {
        "overall_score": max(0.0, min(10.0, overall)),
        "summary": str(data.get("summary", "")).strip(),
        "strengths": [str(s) for s in (data.get("strengths") or [])],
        "weaknesses": [str(s) for s in (data.get("weaknesses") or [])],
        "tips": [str(s) for s in (data.get("tips") or [])],
    }
