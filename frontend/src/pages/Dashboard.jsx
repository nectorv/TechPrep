import { useState, useEffect } from 'react'
import Navbar from '../components/Navbar'
import { dashboardApi } from '../api/dashboard'
import { usePlan } from '../context/PlanContext'

export default function Dashboard() {
  const { activePlan } = usePlan()
  const [overview, setOverview]   = useState(null)
  const [themes, setThemes]       = useState([])
  const [heatmap, setHeatmap]     = useState([])
  const [sessions, setSessions]   = useState([])
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    Promise.all([
      dashboardApi.getOverview(activePlan.id),
      dashboardApi.getThemes(activePlan.id),
      dashboardApi.getHeatmap(activePlan.id),
      dashboardApi.getRecentSessions(activePlan.id),
    ]).then(([ov, th, hm, se]) => {
      setOverview(ov)
      setThemes(th)
      setHeatmap(hm.days)
      setSessions(se)
    }).finally(() => setLoading(false))
  }, [activePlan.id])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex flex-col">
        <Navbar />
        <div className="flex-1 flex items-center justify-center">
          <span className="text-gray-400 text-sm">Loading…</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-10 space-y-10">

        {/* ── Stats row ── */}
        {overview && (
          <section>
            <h2 className="text-white font-semibold mb-4">Overview</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard label="Total questions" value={overview.total_questions} />
              <StatCard label="Acquired"        value={overview.by_status.acquired} color="text-green-400" />
              <StatCard label="Due today"       value={overview.due_today}          color="text-orange-400" />
              <StatCard label="Day streak"      value={`${overview.streak_days}🔥`} color="text-yellow-400" />
              <StatCard label="Total answers"   value={overview.total_answers} />
              <StatCard label="Sessions"        value={overview.sessions_count} />
              <StatCard label="Learning"        value={overview.by_status.learning} color="text-blue-400" />
              <StatCard label="New"             value={overview.by_status.new}      color="text-gray-400" />
            </div>
          </section>
        )}

        {/* ── Activity heatmap ── */}
        {heatmap.length > 0 && (
          <section>
            <h2 className="text-white font-semibold mb-4">Activity — last 90 days</h2>
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
              <Heatmap days={heatmap} />
              <div className="flex items-center gap-2 mt-4 justify-end">
                <span className="text-gray-600 text-xs">Less</span>
                {['bg-gray-800', 'bg-green-900', 'bg-green-700', 'bg-green-500', 'bg-green-400'].map((c) => (
                  <span key={c} className={`w-3 h-3 rounded-sm ${c}`} />
                ))}
                <span className="text-gray-600 text-xs">More</span>
              </div>
            </div>
          </section>
        )}

        {/* ── Themes ── */}
        {themes.length > 0 && (
          <section>
            <h2 className="text-white font-semibold mb-4">Progress by theme</h2>
            <div className="space-y-3">
              {themes.map((t) => <ThemeRow key={t.id} theme={t} />)}
            </div>
          </section>
        )}

        {themes.length === 0 && (
          <div className="text-center py-20">
            <p className="text-2xl mb-2">📚</p>
            <p className="text-white font-medium mb-1">Nothing here yet</p>
            <p className="text-gray-400 text-sm">Use the Coach to create themes and generate questions.</p>
          </div>
        )}

        {/* ── Recent sessions ── */}
        {sessions.length > 0 && (
          <section>
            <h2 className="text-white font-semibold mb-4">Recent sessions</h2>
            <div className="bg-gray-900 border border-gray-800 rounded-xl divide-y divide-gray-800">
              {sessions.map((s) => <SessionRow key={s.id} session={s} />)}
            </div>
          </section>
        )}

      </main>
    </div>
  )
}

// ── Heatmap ───────────────────────────────────────────────────────────────────

function heatColor(count) {
  if (count === 0)  return 'bg-gray-800'
  if (count <= 2)   return 'bg-green-900'
  if (count <= 5)   return 'bg-green-700'
  if (count <= 9)   return 'bg-green-500'
  return 'bg-green-400'
}

function Heatmap({ days }) {
  // Split into 13 columns of 7
  const weeks = []
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7))
  }

  // Month labels: find weeks where the month changes
  const monthLabels = weeks.map((week) => {
    const first = week[0]
    const d = new Date(first.date)
    // Show label on the first week of each month
    const prev = new Date(first.date)
    prev.setDate(prev.getDate() - 7)
    if (d.getMonth() !== prev.getMonth()) {
      return d.toLocaleDateString('en', { month: 'short' })
    }
    return ''
  })

  return (
    <div className="overflow-x-auto">
      <div className="inline-flex flex-col gap-1 min-w-full">
        {/* Month labels */}
        <div className="flex gap-1 mb-1">
          {monthLabels.map((label, i) => (
            <div key={i} className="w-3 text-gray-500 text-[10px] leading-none" style={{ minWidth: 12 }}>
              {label}
            </div>
          ))}
        </div>
        {/* Grid: 7 rows × 13 cols */}
        {Array.from({ length: 7 }).map((_, row) => (
          <div key={row} className="flex gap-1">
            {weeks.map((week, col) => {
              const day = week[row]
              if (!day) return <div key={col} className="w-3 h-3" />
              return (
                <div
                  key={col}
                  title={`${day.date}: ${day.count} answer${day.count !== 1 ? 's' : ''}`}
                  className={`w-3 h-3 rounded-sm ${heatColor(day.count)} cursor-default transition-opacity hover:opacity-70`}
                />
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Theme row ─────────────────────────────────────────────────────────────────

function ThemeRow({ theme }) {
  const { name, total, new: newQ, learning, acquired, due } = theme
  if (total === 0) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4 flex items-center justify-between">
        <span className="text-white text-sm font-medium">{name}</span>
        <span className="text-gray-600 text-xs">No questions yet</span>
      </div>
    )
  }

  const pct = (n) => `${((n / total) * 100).toFixed(1)}%`

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-white text-sm font-medium">{name}</span>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          {due > 0 && <span className="text-orange-400 font-medium">{due} due</span>}
          <span>{total} questions</span>
        </div>
      </div>

      {/* Stacked progress bar */}
      <div className="h-2 rounded-full overflow-hidden flex bg-gray-800">
        {acquired > 0 && (
          <div className="bg-green-500 h-full transition-all" style={{ width: pct(acquired) }} />
        )}
        {learning > 0 && (
          <div className="bg-blue-500 h-full transition-all" style={{ width: pct(learning) }} />
        )}
        {newQ > 0 && (
          <div className="bg-gray-600 h-full transition-all" style={{ width: pct(newQ) }} />
        )}
      </div>

      <div className="flex gap-4 text-xs">
        <Legend color="bg-green-500" label="Acquired" count={acquired} />
        <Legend color="bg-blue-500"  label="Learning" count={learning} />
        <Legend color="bg-gray-600"  label="New"      count={newQ} />
      </div>
    </div>
  )
}

function Legend({ color, label, count }) {
  return (
    <div className="flex items-center gap-1.5 text-gray-400">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      <span>{label}</span>
      <span className="text-gray-500">({count})</span>
    </div>
  )
}

// ── Session row ───────────────────────────────────────────────────────────────

function SessionRow({ session }) {
  const date = new Date(session.started_at).toLocaleDateString('en', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  })
  const duration = session.ended_at
    ? Math.round((new Date(session.ended_at) - new Date(session.started_at)) / 60000)
    : null

  return (
    <div className="flex items-center justify-between px-5 py-3">
      <div className="flex items-center gap-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium capitalize ${
          session.type === 'mock' ? 'bg-purple-500/20 text-purple-300' : 'bg-blue-500/20 text-blue-300'
        }`}>
          {session.type}
        </span>
        <span className="text-gray-300 text-sm">{date}</span>
        {duration !== null && (
          <span className="text-gray-500 text-xs">{duration}m</span>
        )}
      </div>
      <div className="flex items-center gap-4 text-sm text-gray-400">
        <span>{session.answer_count} answers</span>
        {session.avg_grade !== null && (
          <span className="text-gray-500">avg {session.avg_grade}/5</span>
        )}
      </div>
    </div>
  )
}

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, color = 'text-white' }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl px-5 py-4">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-gray-500 text-xs mt-1">{label}</p>
    </div>
  )
}
