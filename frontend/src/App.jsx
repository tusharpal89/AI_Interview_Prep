import { useEffect, useRef, useState } from 'react'
import {
  Award, BrainCircuit, Check, ChevronDown, Lightbulb, Loader2, Mic, Square,
  RefreshCw, Send, Sparkles, ThumbsDown, ThumbsUp, Volume2, X,
} from 'lucide-react'

// In a production build (served from the backend) the API is same-origin: use a
// relative base so "/api/..." hits whatever host the app is served from.
// In local dev, frontend/.env points at the separate backend dev server.
const API = import.meta.env.PROD ? '' : (import.meta.env.VITE_API_URL || 'http://localhost:8001')

const ROLES = [
  'Frontend Developer', 'Backend Developer', 'Full-Stack Developer', 'Data Scientist',
  'Machine Learning Engineer', 'DevOps Engineer', 'Product Manager', 'Data Analyst',
]
const DIFFICULTIES = ['Junior', 'Mid', 'Senior']
const TYPES = ['Technical', 'Behavioral', 'Mixed']

async function api(path, options = {}) {
  const res = await fetch(API + path, options)
  let body = {}
  try { body = await res.json() } catch { /* no json */ }
  if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`)
  return body
}
const post = (path, payload) =>
  api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })

const scoreClass = (s) => (s >= 8 ? 'good' : s >= 5 ? 'ok' : 'bad')

function speak(text, on) {
  if (!on || !('speechSynthesis' in window)) return
  try {
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(new SpeechSynthesisUtterance(text))
  } catch { /* ignore */ }
}

export default function App() {
  const [stage, setStage] = useState('setup')
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')

  // setup
  const [role, setRole] = useState('Frontend Developer')
  const [difficulty, setDifficulty] = useState('Mid')
  const [type, setType] = useState('Mixed')
  const [numQuestions, setNumQuestions] = useState(5)
  const [jd, setJd] = useState('')
  const [starting, setStarting] = useState(false)

  // interview
  const [session, setSession] = useState(null)
  const [q, setQ] = useState(null) // {question, index}
  const [answer, setAnswer] = useState('')
  const [evaluation, setEvaluation] = useState(null)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState(false)
  const [nextQ, setNextQ] = useState(null)
  const [speakOn, setSpeakOn] = useState(false)

  // voice
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const recRef = useRef(null)
  const chunksRef = useRef([])

  // report
  const [report, setReport] = useState(null)
  const [loadingReport, setLoadingReport] = useState(false)

  useEffect(() => { api('/api/health').then(setHealth).catch(() => {}) }, [])

  async function startInterview() {
    if (!role.trim()) return setError('Please enter a role.')
    setStarting(true); setError('')
    try {
      const s = await post('/api/start', {
        role, difficulty, interview_type: type, num_questions: numQuestions, job_description: jd,
      })
      setSession({ session_id: s.session_id, total: s.total })
      setQ({ question: s.question, index: s.index })
      setAnswer(''); setEvaluation(null); setDone(false); setNextQ(null)
      setStage('interview')
      speak(s.question, speakOn)
    } catch (e) { setError(e.message) } finally { setStarting(false) }
  }

  async function submitAnswer() {
    if (busy) return
    setBusy(true); setError('')
    try {
      const r = await post('/api/answer', { session_id: session.session_id, answer })
      setEvaluation(r.evaluation); setDone(r.done); setNextQ(r.next_question)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function goNext() {
    if (done) return loadReport()
    setQ({ question: nextQ, index: q.index + 1 })
    setAnswer(''); setEvaluation(null); setNextQ(null)
    speak(nextQ, speakOn)
  }

  async function loadReport() {
    setLoadingReport(true); setError('')
    try {
      const r = await api(`/api/report/${session.session_id}`)
      setReport(r); setStage('report')
      try { window.speechSynthesis.cancel() } catch { /* ignore */ }
    } catch (e) { setError(e.message) } finally { setLoadingReport(false) }
  }

  function reset() {
    try { window.speechSynthesis.cancel() } catch { /* ignore */ }
    setStage('setup'); setSession(null); setQ(null); setAnswer(''); setEvaluation(null)
    setReport(null); setError(''); setDone(false); setNextQ(null)
  }

  // ---- voice recording ----
  async function toggleRecord() {
    if (recording) { recRef.current?.stop(); return }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      return setError('Voice recording is not supported in this browser. Please type your answer.')
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream)
      chunksRef.current = []
      mr.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data)
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        setRecording(false); setTranscribing(true); setError('')
        try {
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
          const form = new FormData()
          form.append('file', blob, 'answer.webm')
          const res = await fetch(API + '/api/transcribe', { method: 'POST', body: form })
          const data = await res.json()
          if (!res.ok) throw new Error(data.detail || 'Transcription failed.')
          setAnswer((a) => (a.trim() ? a.trim() + ' ' : '') + (data.text || ''))
        } catch (e) { setError(e.message) } finally { setTranscribing(false) }
      }
      mr.start(); recRef.current = mr; setRecording(true); setError('')
    } catch {
      setError('Microphone access was blocked. Allow mic access, or type your answer.')
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand" onClick={reset} role="button" title="Back to home"><b><BrainCircuit /></b>Prep<em>Pilot</em></div>
        <div className="right">
          {stage !== 'setup' && <button className="ghost" onClick={reset}><RefreshCw />New interview</button>}
          {health && (
            <span className="pill" title={health.llm_key_configured ? 'LLM ready' : 'No LLM key'}>
              <i className={health.llm_key_configured ? 'ok' : 'bad'} />{health.llm_model}
            </span>
          )}
        </div>
      </header>

      {health && !health.llm_key_configured && (
        <div className="warn">No LLM key configured. Add <code>GROQ_API_KEY</code> to <code>.env</code> and restart the backend.</div>
      )}
      {error && <div className="error wrap"><X />{error}</div>}

      {stage === 'setup' && (
        <Setup
          {...{ role, setRole, difficulty, setDifficulty, type, setType,
            numQuestions, setNumQuestions, jd, setJd, starting, startInterview, speakOn, setSpeakOn }}
        />
      )}

      {stage === 'interview' && q && (
        <Interview
          {...{ q, total: session.total, role, answer, setAnswer, evaluation, busy, done,
            submitAnswer, goNext, loadingReport, recording, transcribing, toggleRecord,
            speakOn, setSpeakOn }}
        />
      )}

      {stage === 'report' && report && <Report report={report} reset={reset} />}
    </div>
  )
}

function Setup({ role, setRole, difficulty, setDifficulty, type, setType, numQuestions,
  setNumQuestions, jd, setJd, starting, startInterview, speakOn, setSpeakOn }) {
  return (
    <main className="setup">
      <div className="hero">
        <label><Sparkles />AI-POWERED MOCK INTERVIEWS</label>
        <h1>Practice the interview.<br /><em>Ace the real one.</em></h1>
        <p>Pick a role, answer by voice or text, and get instant scored feedback on every answer.</p>
      </div>

      <div className="card form">
        <div className="field">
          <span>Role you're interviewing for</span>
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Frontend Developer" />
          <div className="chips">
            {ROLES.map((r) => (
              <button key={r} className={role === r ? 'on' : ''} onClick={() => setRole(r)}>{r}</button>
            ))}
          </div>
        </div>

        <div className="row">
          <div className="field">
            <span>Level</span>
            <div className="seg">
              {DIFFICULTIES.map((d) => (
                <button key={d} className={difficulty === d ? 'on' : ''} onClick={() => setDifficulty(d)}>{d}</button>
              ))}
            </div>
          </div>
          <div className="field">
            <span>Interview type</span>
            <div className="seg">
              {TYPES.map((t) => (
                <button key={t} className={type === t ? 'on' : ''} onClick={() => setType(t)}>{t}</button>
              ))}
            </div>
          </div>
        </div>

        <div className="field">
          <span>Number of questions: <b>{numQuestions}</b></span>
          <input type="range" min="3" max="12" value={numQuestions}
            onChange={(e) => setNumQuestions(Number(e.target.value))} />
        </div>

        <div className="field">
          <span>Job description <small>(optional — tailors the questions)</small></span>
          <textarea value={jd} onChange={(e) => setJd(e.target.value)} rows={3}
            placeholder="Paste a job description to get more targeted questions…" />
        </div>

        <label className="toggle">
          <input type="checkbox" checked={speakOn} onChange={(e) => setSpeakOn(e.target.checked)} />
          <Volume2 /> Read questions aloud
        </label>

        <button className="primary big" onClick={startInterview} disabled={starting}>
          {starting ? <><Loader2 className="spin" />Preparing your interview…</> : <>Start interview</>}
        </button>
      </div>
    </main>
  )
}

function Interview({ q, total, role, answer, setAnswer, evaluation, busy, done, submitAnswer,
  goNext, loadingReport, recording, transcribing, toggleRecord, speakOn, setSpeakOn }) {
  const pct = Math.round(((q.index - 1) / total) * 100)
  return (
    <main className="interview">
      <div className="progress">
        <div className="bar"><i style={{ width: `${pct}%` }} /></div>
        <div className="meta"><span className="role">{role}</span><span>Question {q.index} of {total}</span></div>
      </div>

      <div className="card question">
        <div className="qhead">
          <b><Sparkles /></b>
          <button className="speak" onClick={() => speak(q.question, true)} title="Read aloud"><Volume2 /></button>
        </div>
        <h2>{q.question}</h2>
      </div>

      {!evaluation ? (
        <div className="card answer">
          <textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={6}
            placeholder="Type your answer here, or use the mic to speak…" disabled={busy} />
          <div className="actions">
            <button className={`rec ${recording ? 'on' : ''}`} onClick={toggleRecord} disabled={busy || transcribing}>
              {transcribing ? <><Loader2 className="spin" />Transcribing…</>
                : recording ? <><Square />Stop recording</>
                  : <><Mic />Record answer</>}
            </button>
            <button className="primary" onClick={submitAnswer} disabled={busy || transcribing || !answer.trim()}>
              {busy ? <><Loader2 className="spin" />Evaluating…</> : <><Send />Submit answer</>}
            </button>
          </div>
          {recording && <div className="reclive"><i />Recording… speak now, then press Stop.</div>}
        </div>
      ) : (
        <>
          <EvalCard evaluation={evaluation} />
          <div className="nextbar">
            <button className="primary big" onClick={goNext} disabled={loadingReport}>
              {loadingReport ? <><Loader2 className="spin" />Building your report…</>
                : done ? <><Award />See my results</> : <>Next question →</>}
            </button>
          </div>
        </>
      )}
    </main>
  )
}

function EvalCard({ evaluation }) {
  return (
    <div className="card eval">
      <div className="evalhead">
        <div className={`scorering ${scoreClass(evaluation.score)}`}>
          <b>{evaluation.score}</b><span>/10</span>
        </div>
        <p className="verdict">{evaluation.verdict}</p>
      </div>
      <div className="cols">
        {evaluation.strengths?.length > 0 && (
          <section className="strengths">
            <h4><ThumbsUp />Strengths</h4>
            <ul>{evaluation.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
          </section>
        )}
        {evaluation.improvements?.length > 0 && (
          <section className="improvements">
            <h4><ThumbsDown />To improve</h4>
            <ul>{evaluation.improvements.map((s, i) => <li key={i}>{s}</li>)}</ul>
          </section>
        )}
      </div>
      {evaluation.ideal_answer && (
        <details className="ideal">
          <summary><Lightbulb />Model answer</summary>
          <p>{evaluation.ideal_answer}</p>
        </details>
      )}
    </div>
  )
}

function Report({ report, reset }) {
  const [open, setOpen] = useState(-1)
  return (
    <main className="report">
      <div className="card overall">
        <div className={`bigscore ${scoreClass(report.overall_score)}`}>
          <b>{report.overall_score}</b><span>/ 10</span>
        </div>
        <div className="overallinfo">
          <label><Award />Interview complete — {report.role}</label>
          <p>{report.summary}</p>
        </div>
      </div>

      <div className="cols two">
        <section className="card strengths">
          <h4><ThumbsUp />What went well</h4>
          <ul>{report.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </section>
        <section className="card improvements">
          <h4><ThumbsDown />Work on this</h4>
          <ul>{report.weaknesses.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </section>
      </div>

      {report.tips?.length > 0 && (
        <section className="card tips">
          <h4><Lightbulb />Prep tips</h4>
          <ul>{report.tips.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </section>
      )}

      <div className="card qreview">
        <h4>Question-by-question</h4>
        {report.questions.map((item, i) => (
          <div className={`qrow ${open === i ? 'open' : ''}`} key={i}>
            <button onClick={() => setOpen(open === i ? -1 : i)}>
              <span className={`mini ${scoreClass(item.score)}`}>{item.score}</span>
              <span className="qtext">{item.question}</span>
              <ChevronDown className="chev" />
            </button>
            {open === i && (
              <div className="qbody">
                <p className="verdict">{item.verdict}</p>
                <div className="yoursaid"><small>YOUR ANSWER</small><p>{item.answer || <em>(no answer)</em>}</p></div>
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="nextbar">
        <button className="primary big" onClick={reset}><RefreshCw />Practice again</button>
      </div>
    </main>
  )
}
