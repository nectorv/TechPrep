import { useState, useEffect } from 'react'
import { authApi } from '../api/auth'

export default function TelegramLinkModal({ onClose }) {
  const [code, setCode]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [secondsLeft, setSecondsLeft] = useState(600)

  useEffect(() => {
    authApi.generateTelegramCode()
      .then((data) => {
        setCode(data.code)
        setSecondsLeft(data.expires_in)
      })
      .catch(() => setError('Failed to generate code. Try again.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!code) return
    const interval = setInterval(() => {
      setSecondsLeft((s) => {
        if (s <= 1) { clearInterval(interval); return 0 }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(interval)
  }, [code])

  const minutes = Math.floor(secondsLeft / 60)
  const seconds = String(secondsLeft % 60).padStart(2, '0')
  const expired = secondsLeft === 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-sm p-6 space-y-5 shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-white font-semibold text-lg">Connect Telegram</h2>
            <p className="text-gray-400 text-sm mt-0.5">Practice on your phone, track progress everywhere</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-300 transition-colors text-xl leading-none ml-4"
          >
            ×
          </button>
        </div>

        {/* Steps */}
        <ol className="space-y-3 text-sm text-gray-300">
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">1</span>
            <span>Open <strong className="text-white">Telegram</strong> on your phone and find your TechPrep bot</span>
          </li>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">2</span>
            <span>Send this command:</span>
          </li>
        </ol>

        {/* Code display */}
        {loading && (
          <div className="h-16 flex items-center justify-center">
            <span className="text-gray-500 text-sm">Generating code…</span>
          </div>
        )}
        {error && (
          <p className="text-red-400 text-sm text-center">{error}</p>
        )}
        {code && !error && (
          <div className="bg-gray-800 rounded-xl px-4 py-3 text-center space-y-1">
            <p className="text-gray-400 text-xs font-mono">/link</p>
            <p className={`text-3xl font-mono font-bold tracking-widest ${expired ? 'text-gray-600' : 'text-white'}`}>
              {code}
            </p>
            {expired ? (
              <p className="text-red-400 text-xs">Expired — refresh to get a new code</p>
            ) : (
              <p className="text-gray-500 text-xs">Expires in {minutes}:{seconds}</p>
            )}
          </div>
        )}

        <ol className="space-y-3 text-sm text-gray-300" start={3}>
          <li className="flex gap-3">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center font-bold">3</span>
            <span>The bot will confirm and your accounts will be linked</span>
          </li>
        </ol>

        <div className="flex gap-3 pt-1">
          {expired && (
            <button
              onClick={() => {
                setLoading(true); setError(''); setCode(null)
                authApi.generateTelegramCode()
                  .then((data) => { setCode(data.code); setSecondsLeft(data.expires_in) })
                  .catch(() => setError('Failed to generate code.'))
                  .finally(() => setLoading(false))
              }}
              className="flex-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg py-2.5 text-sm font-medium transition-colors"
            >
              Get new code
            </button>
          )}
          <button
            onClick={onClose}
            className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg py-2.5 text-sm font-medium transition-colors"
          >
            {expired ? 'Close' : 'Done'}
          </button>
        </div>
      </div>
    </div>
  )
}
