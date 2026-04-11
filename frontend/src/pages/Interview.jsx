import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import Navbar from '../components/Navbar'
import { interviewApi } from '../api/interview'
import { usePlan } from '../context/PlanContext'

const DIFFICULTY_LABEL = { 1: 'Beginner', 2: 'Easy', 3: 'Medium', 4: 'Hard', 5: 'Expert' }
const DIFFICULTY_COLOR  = { 1: 'text-green-400', 2: 'text-green-300', 3: 'text-yellow-400', 4: 'text-orange-400', 5: 'text-red-400' }
const GRADE_LABEL = ['Blackout', 'Familiar', 'Recalled', 'Correct', 'Good', 'Perfect']
const GRADE_COLOR = ['bg-red-600', 'bg-red-500', 'bg-orange-500', 'bg-yellow-500', 'bg-blue-500', 'bg-green-500']
const MOCK_DURATION_MINUTES = 20

// ── State machine ─────────────────────────────────────────────────────────────
const S = {
  LOBBY:       'lobby',
  QUESTION:    'question',
  EVALUATING:  'evaluating',
  FEEDBACK:    'feedback',   // practice only
  DONE:        'done',
  REVIEWING:   'reviewing',  // loading review data
  REVIEW:      'review',     // mock end-of-session
}

export default function Interview() {
  const { activePlan } = usePlan()
  const [state, setState]         = useState(S.LOBBY)
  const [dueCount, setDueCount]   = useState(null)
  const [sessionType, setSessionType] = useState('practice')
  const [sessionId, setSessionId] = useState(null)
  const [question, setQuestion]   = useState(null)
  const [answer, setAnswer]       = useState('')
  const [retryAnswer, setRetryAnswer] = useState('')
  const [evaluation, setEvaluation] = useState(null)
  const [reviewItems, setReviewItems] = useState([])
  const [error, setError]         = useState('')

  // Mock timer: seconds remaining
  const [timeLeft, setTimeLeft]   = useState(null)
  const timerRef = useRef(null)

  // Answered count for mock mode
  const answeredRef = useRef(0)

  useEffect(() => {
    interviewApi.getDueCount(activePlan.id)
      .then(setDueCount)
      .catch(() => setDueCount({ due: 0, new: 0, total_available: 0 }))
  }, [activePlan.id])

  // Timer tick
  useEffect(() => {
    if (timeLeft === null) return
    if (timeLeft <= 0) {
      clearInterval(timerRef.current)
      handleTimerExpired()
      return
    }
    timerRef.current = setInterval(() => setTimeLeft((t) => t - 1), 1000)
    return () => clearInterval(timerRef.current)
  }, [timeLeft])

  const handleTimerExpired = useCallback(async () => {
    if (sessionId) {
      await interviewApi.endSession(sessionId).catch(() => {})
      loadReview(sessionId)
    }
  }, [sessionId])

  function startTimer() {
    clearInterval(timerRef.current)
    setTimeLeft(MOCK_DURATION_MINUTES * 60)
  }

  function stopTimer() {
    clearInterval(timerRef.current)
    setTimeLeft(null)
  }

  async function loadReview(sid) {
    setState(S.REVIEWING)
    try {
      const items = await interviewApi.getReview(sid)
      setReviewItems(items)
      setState(S.REVIEW)
    } catch (err) {
      setError(err.message)
      setState(S.DONE)
    }
  }

  async function startSession() {
    setError('')
    answeredRef.current = 0
    try {
      const data = await interviewApi.startSession(sessionType, activePlan.id)
      setSessionId(data.session_id)
      if (!data.first_question) { setState(S.DONE); return }
      setQuestion(data.first_question)
      setAnswer('')
      if (sessionType === 'mock') startTimer()
      setState(S.QUESTION)
    } catch (err) {
      setError(err.message)
    }
  }

  async function submitAnswer() {
    if (!answer.trim()) return
    setError('')
    setState(S.EVALUATING)
    try {
      const data = await interviewApi.submitAnswer(sessionId, question.id, answer.trim())
      setEvaluation(data)
      answeredRef.current += 1

      if (sessionType === 'mock') {
        // No feedback — go straight to next question or end
        if (data.next_question) {
          setQuestion(data.next_question)
          setAnswer('')
          setState(S.QUESTION)
        } else {
          stopTimer()
          await interviewApi.endSession(sessionId).catch(() => {})
          loadReview(sessionId)
        }
      } else {
        setState(S.FEEDBACK)
      }
    } catch (err) {
      setError(err.message)
      setState(S.QUESTION)
    }
  }

  async function submitRetry() {
    if (!retryAnswer.trim()) return
    setError('')
    setState(S.EVALUATING)
    try {
      const data = await interviewApi.submitAnswer(sessionId, question.id, retryAnswer.trim(), true)
      setEvaluation(data)
      setRetryAnswer('')
      if (sessionType === 'mock') {
        if (data.next_question) { setQuestion(data.next_question); setAnswer(''); setState(S.QUESTION) }
        else { stopTimer(); await interviewApi.endSession(sessionId).catch(() => {}); loadReview(sessionId) }
      } else {
        setState(S.FEEDBACK)
      }
    } catch (err) {
      setError(err.message)
      setState(S.FEEDBACK)
    }
  }

  function nextQuestion() {
    if (!evaluation.next_question) {
      setState(S.DONE)
      return
    }
    setQuestion(evaluation.next_question)
    setEvaluation(null)
    setAnswer('')
    setState(S.QUESTION)
  }

  async function endEarly() {
    stopTimer()
    if (sessionId) {
      await interviewApi.endSession(sessionId).catch(() => {})
      if (sessionType === 'mock' && answeredRef.current > 0) {
        loadReview(sessionId)
        return
      }
    }
    setState(S.DONE)
  }

  function restart() {
    stopTimer()
    setSessionId(null); setQuestion(null); setEvaluation(null)
    setAnswer(''); setError(''); setReviewItems([])
    answeredRef.current = 0
    interviewApi.getDueCount(activePlan.id).then(setDueCount).catch(() => {})
    setState(S.LOBBY)
  }

  return (
    <div className="h-screen bg-gray-950 flex flex-col overflow-hidden">
      <Navbar />

      {/* Mock timer banner */}
      {sessionType === 'mock' && timeLeft !== null && state === S.QUESTION && (
        <div className={`text-center py-2 text-sm font-mono font-medium ${
          timeLeft < 120 ? 'bg-red-900/60 text-red-300' : 'bg-gray-900 text-gray-400'
        }`}>
          ⏱ {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, '0')} remaining
        </div>
      )}

      <div className="flex-1 overflow-y-auto flex flex-col items-center px-4 py-12">

        {/* ── LOBBY ── */}
        {state === S.LOBBY && (
          <div className="w-full max-w-md text-center space-y-6">
            <div>
              <p className="text-3xl mb-3">🎯</p>
              <h2 className="text-xl font-semibold text-white mb-1">Interview Practice</h2>
              <p className="text-gray-400 text-sm">Answer questions one by one and get AI feedback.</p>
            </div>
            {dueCount && (
              <div className="flex justify-center gap-6 text-sm">
                <Stat label="Due for review" value={dueCount.due}  color="text-orange-400" />
                <Stat label="New"            value={dueCount.new}  color="text-blue-400" />
              </div>
            )}
            {dueCount?.total_available === 0 && (
              <p className="text-gray-500 text-sm bg-gray-900 rounded-xl p-4">
                No questions yet. Use the <strong className="text-white">Coach</strong> to generate some first.
              </p>
            )}
            <div className="flex gap-2 justify-center">
              {['practice', 'mock'].map((t) => (
                <button key={t} onClick={() => setSessionType(t)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors ${
                    sessionType === t ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:text-white'
                  }`}>
                  {t}
                </button>
              ))}
            </div>
            <p className="text-gray-500 text-xs">
              {sessionType === 'practice'
                ? 'Practice: immediate feedback after each answer.'
                : `Mock: ${MOCK_DURATION_MINUTES}-minute timed session, all feedback at the end.`}
            </p>
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <button onClick={startSession} disabled={dueCount?.total_available === 0}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl py-3 font-medium transition-colors">
              Start Session
            </button>
          </div>
        )}

        {/* ── QUESTION ── */}
        {state === S.QUESTION && question && (
          <div className="w-full max-w-2xl space-y-5">
            {sessionType === 'mock' && (
              <p className="text-gray-500 text-xs text-right">
                {answeredRef.current} answered · no feedback until end
              </p>
            )}
            <QuestionCard question={question} />
            <textarea value={answer} onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer here…" rows={6}
              className="w-full bg-gray-800 text-white placeholder-gray-500 rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-blue-500 resize-none leading-relaxed" />
            {error && <p className="text-red-400 text-sm">{error}</p>}
            <div className="flex gap-3">
              <button onClick={submitAnswer} disabled={!answer.trim()}
                className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl py-3 font-medium transition-colors">
                Submit Answer
              </button>
              <button onClick={endEarly}
                className="px-4 py-3 text-gray-500 hover:text-gray-300 text-sm transition-colors">
                End session
              </button>
            </div>
          </div>
        )}

        {/* ── EVALUATING ── */}
        {state === S.EVALUATING && (
          <div className="text-center space-y-3">
            <div className="flex gap-1 justify-center">
              {[0, 150, 300].map((d) => (
                <span key={d} className="w-3 h-3 bg-blue-500 rounded-full animate-bounce"
                  style={{ animationDelay: `${d}ms` }} />
              ))}
            </div>
            <p className="text-gray-400 text-sm">Evaluating your answer…</p>
          </div>
        )}

        {/* ── FEEDBACK (practice only) ── */}
        {state === S.FEEDBACK && evaluation && (
          <div className="w-full max-w-2xl space-y-5">
            <QuestionCard question={question} />
            <div className="flex items-center gap-3 flex-wrap">
              <span className={`${GRADE_COLOR[evaluation.grade]} text-white text-sm font-semibold px-3 py-1 rounded-full`}>
                {evaluation.grade}/5 — {GRADE_LABEL[evaluation.grade]}
              </span>
              <span className="text-gray-500 text-sm">
                Next review in {evaluation.sm2.interval_days}d · {evaluation.sm2.status}
              </span>
            </div>
            <div className="bg-gray-800 rounded-xl p-5">
              <p className="text-gray-400 text-xs uppercase tracking-wide mb-3 font-medium">Feedback</p>
              <div className="prose prose-invert prose-sm max-w-none prose-p:my-1">
                <ReactMarkdown>{evaluation.feedback}</ReactMarkdown>
              </div>
            </div>
            {evaluation.explanation && (
              <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-5">
                <p className="text-blue-400 text-xs uppercase tracking-wide mb-3 font-medium">📖 Model Explanation</p>
                <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 text-gray-200">
                  <ReactMarkdown>{evaluation.explanation}</ReactMarkdown>
                </div>
              </div>
            )}
            {evaluation.awaiting_retry ? (
              <div className="space-y-3">
                <p className="text-yellow-400 text-sm font-medium">🔄 Give it another shot</p>
                <textarea value={retryAnswer} onChange={(e) => setRetryAnswer(e.target.value)}
                  placeholder="Try again with what you just learned…" rows={5}
                  className="w-full bg-gray-800 text-white placeholder-gray-500 rounded-xl px-4 py-3 text-sm outline-none focus:ring-2 focus:ring-yellow-500 resize-none leading-relaxed" />
                {error && <p className="text-red-400 text-sm">{error}</p>}
                <button onClick={submitRetry} disabled={!retryAnswer.trim()}
                  className="w-full bg-yellow-600 hover:bg-yellow-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl py-3 font-medium transition-colors">
                  Submit Retry
                </button>
              </div>
            ) : (
              <button onClick={nextQuestion}
                className="w-full bg-blue-600 hover:bg-blue-500 text-white rounded-xl py-3 font-medium transition-colors">
                {evaluation.next_question ? 'Next Question →' : 'Finish Session'}
              </button>
            )}
          </div>
        )}

        {/* ── REVIEWING (loading) ── */}
        {state === S.REVIEWING && (
          <div className="text-center space-y-3">
            <div className="flex gap-1 justify-center">
              {[0, 150, 300].map((d) => (
                <span key={d} className="w-3 h-3 bg-purple-500 rounded-full animate-bounce"
                  style={{ animationDelay: `${d}ms` }} />
              ))}
            </div>
            <p className="text-gray-400 text-sm">Loading session review…</p>
          </div>
        )}

        {/* ── REVIEW (mock end screen) ── */}
        {state === S.REVIEW && (
          <div className="w-full max-w-2xl space-y-6">
            <div className="text-center">
              <p className="text-2xl mb-2">📋</p>
              <h2 className="text-xl font-semibold text-white">Mock Interview Results</h2>
              {reviewItems.length > 0 && (
                <p className="text-gray-400 text-sm mt-1">
                  {reviewItems.length} questions · avg grade{' '}
                  {(reviewItems.reduce((s, i) => s + (i.answer.sm2_grade ?? 0), 0) / reviewItems.length).toFixed(1)}/5
                </p>
              )}
            </div>
            {reviewItems.map((item, i) => (
              <ReviewItem key={i} index={i + 1} item={item} />
            ))}
            <button onClick={restart}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white rounded-xl py-3 font-medium transition-colors">
              Back to lobby
            </button>
          </div>
        )}

        {/* ── DONE ── */}
        {state === S.DONE && (
          <div className="text-center space-y-4">
            <p className="text-3xl">✅</p>
            <h2 className="text-xl font-semibold text-white">Session complete!</h2>
            <p className="text-gray-400 text-sm">No more questions due. Come back later or add more via the Coach.</p>
            <button onClick={restart}
              className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-6 py-3 font-medium transition-colors">
              Back to lobby
            </button>
          </div>
        )}

      </div>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function QuestionCard({ question }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="text-gray-500 text-xs uppercase tracking-wide">{question.theme_name}</span>
        <span className="text-gray-700">·</span>
        <span className={`text-xs font-medium ${DIFFICULTY_COLOR[question.difficulty]}`}>
          {DIFFICULTY_LABEL[question.difficulty]}
        </span>
        <span className="text-gray-700">·</span>
        <span className="text-gray-500 text-xs capitalize">{question.type.replace('_', ' ')}</span>
      </div>
      <p className="text-white text-base leading-relaxed">{question.content}</p>
    </div>
  )
}

function ReviewItem({ index, item }) {
  const { question, answer } = item
  const grade = answer.sm2_grade ?? 0
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
      <div>
        <p className="text-gray-500 text-xs mb-1">Q{index} · {question.theme_name} · {DIFFICULTY_LABEL[question.difficulty]}</p>
        <p className="text-white text-sm leading-relaxed">{question.content}</p>
      </div>
      <div className="bg-gray-800/60 rounded-lg px-4 py-3">
        <p className="text-gray-400 text-xs mb-1">Your answer</p>
        <p className="text-gray-200 text-sm whitespace-pre-wrap">{answer.content}</p>
      </div>
      <div>
        <div className="flex items-center gap-2 mb-2">
          <span className={`${GRADE_COLOR[grade]} text-white text-xs font-semibold px-2 py-0.5 rounded-full`}>
            {grade}/5 — {GRADE_LABEL[grade]}
          </span>
        </div>
        <div className="prose prose-invert prose-sm max-w-none prose-p:my-1">
          <ReactMarkdown>{answer.ai_feedback}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, color }) {
  return (
    <div className="text-center">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-gray-500 text-xs">{label}</p>
    </div>
  )
}
