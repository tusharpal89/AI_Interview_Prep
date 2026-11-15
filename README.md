# PrepPilot — AI Interview Prep Bot 🎤🧠

Practice mock interviews with an AI interviewer. Pick a role, answer questions
**by voice or text**, and get instant **scored feedback** on every answer plus a
full performance report at the end.

**Flow:** choose role / level / type → AI asks a question → you answer (🎤 voice via
Groq Whisper, or type) → AI scores it with strengths, improvements & a model answer →
repeat → final report with an overall score and prep tips.

## ✨ Features

| Feature | What it does |
|---|---|
| 🎯 **Role-based questions** | Tailored to role, level (Junior/Mid/Senior) & type (Technical/Behavioral/Mixed) |
| 📝 **Tailored to a JD** | Paste a job description to get targeted questions |
| 🎤 **Voice answers** | Speak your answer; it's transcribed with Groq Whisper |
| 🔊 **Spoken questions** | Optional text-to-speech reads questions aloud (browser TTS) |
| ✅ **Instant scoring** | Each answer scored 0–10 with strengths, fixes & a model answer |
| 📊 **Final report** | Overall score, summary, strengths/weaknesses, prep tips, per-question review |

## 🧱 Tech stack

- **Backend:** FastAPI + Uvicorn, Pydantic
- **LLM:** Groq (fast + free, `openai/gpt-oss-120b`) via OpenAI-compatible API — swappable to Gemini / OpenAI / Ollama in `.env`
- **Voice:** Groq Whisper (`whisper-large-v3-turbo`) for speech-to-text; browser Web Speech API for text-to-speech
- **Frontend:** React + Vite, `lucide-react`

> No RAG / embeddings here — it's a generative Q&A + evaluation app, so install is light (no PyTorch).

## 🚀 Setup

### 1. Backend

```bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
pip install -r requirements.txt
```

Create `.env` and add a **free** Groq key (https://console.groq.com/keys):

```bash
copy .env.example .env
```

### 2. Frontend

```bash
cd frontend
npm install
copy .env.example .env
```

## ▶️ Run

Easiest: **double-click `start.bat`**.

Or manually — Terminal 1 (backend, from project root):

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8001
```

Terminal 2 (frontend):

```bash
cd frontend
npm run dev
```

Open http://localhost:5174. API docs: http://localhost:8001/docs.

> **Mic note:** voice recording works on `localhost` (browsers require a secure context).
> If a feature shows **"Failed to fetch"**, the backend isn't running — start it again.

## 🔧 Configuration (`.env`)

| Key | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `groq` | `groq` \| `gemini` \| `openai` \| `ollama` |
| `LLM_MODEL` | `openai/gpt-oss-120b` | Groq: `openai/gpt-oss-20b` (faster), `qwen/qwen3.8-27b` |
| `GROQ_API_KEY` | — | free key from https://console.groq.com/keys |
| `GROQ_WHISPER_MODEL` | `whisper-large-v3-turbo` | voice-answer transcription |

## 📝 Notes

- Sessions are in memory; restarting the backend clears them.
- Voice answers are editable after transcription before you submit.
