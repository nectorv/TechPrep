import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { usePlan } from '../context/PlanContext'
import TelegramLinkModal from './TelegramLinkModal'

const links = [
  { to: '/coach',     label: 'Coach' },
  { to: '/interview', label: 'Interview' },
  { to: '/dashboard', label: 'Dashboard' },
]

export default function Navbar() {
  const navigate = useNavigate()
  const { activePlan, clearPlan } = usePlan()
  const [showTelegramModal, setShowTelegramModal] = useState(false)

  function signOut() {
    clearPlan()
    localStorage.removeItem('token')
    navigate('/')
  }

  return (
    <>
    {showTelegramModal && <TelegramLinkModal onClose={() => setShowTelegramModal(false)} />}
    <header className="border-b border-gray-800 bg-gray-950 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <span className="text-white font-bold text-lg tracking-tight">TechPrep</span>
        <nav className="flex gap-1">
          {links.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-gray-800 text-white'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        {activePlan && (
          <button
            onClick={() => navigate('/plans')}
            className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white bg-gray-800/60 hover:bg-gray-800 px-3 py-1.5 rounded-lg transition-colors"
            title="Switch plan"
          >
            <span className="text-gray-500">📋</span>
            <span className="max-w-[140px] truncate">{activePlan.name}</span>
            <span className="text-gray-600 text-xs">↕</span>
          </button>
        )}
        <button
          onClick={() => setShowTelegramModal(true)}
          className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
          title="Connect Telegram"
        >
          Telegram
        </button>
        <button
          onClick={signOut}
          className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
    </>
  )
}
