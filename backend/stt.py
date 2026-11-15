"""Speech-to-text for voice answers, via Groq's Whisper API."""
import os
import tempfile

from backend.config import settings

_ACCEPTED_EXTS = {
    ".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".opus", ".wav", ".webm",
}


class STTError(Exception):
    pass


def _groq_available() -> bool:
    key = (settings.GROQ_API_KEY or "").strip()
    return bool(key) and not key.lower().startswith("your_")


def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    if not _groq_available():
        raise STTError(
            "Voice input needs a Groq API key. Add GROQ_API_KEY to .env, "
            "or just type your answer instead."
        )

    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in _ACCEPTED_EXTS:
        ext = ".webm"  # browser MediaRecorder default

    from openai import OpenAI

    client = OpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        timeout=120.0,
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "answer" + ext)
        with open(path, "wb") as f:
            f.write(file_bytes)
        try:
            with open(path, "rb") as f:
                result = client.audio.transcriptions.create(
                    model=settings.GROQ_WHISPER_MODEL,
                    file=f,
                    response_format="text",
                )
        except Exception as e:
            raise STTError(f"Transcription failed: {e}") from e

    text = result if isinstance(result, str) else getattr(result, "text", "")
    return (text or "").strip()
