import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { plansApi } from '../api/plans'
import { usePlan } from '../context/PlanContext'

export default function Plans() {
  const [plans, setPlans]       = useState([])
  const [loading, setLoading]   = useState(true)
  const [creating, setCreating] = useState(false)
  const [name, setName]         = useState('')
  const [description, setDescription] = useState('')
  const [error, setError]       = useState('')
  const [deleting, setDeleting] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null) // plan to confirm
  const { selectPlan }          = usePlan()
  const navigate                = useNavigate()

  function load() {
    return plansApi.list()
      .then(setPlans)
      .catch(() => navigate('/'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  async function handleCreate(e) {
    e.preventDefault()
    if (!name.trim()) return
    setError('')
    try {
      const plan = await plansApi.create(name.trim(), description.trim() || null)
      setPlans(prev => [...prev, plan])
      setName(''); setDescription(''); setCreating(false)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleDelete(plan) {
    setConfirmDelete(plan)
  }

  async function confirmDeletePlan() {
    const id = confirmDelete.id
    setConfirmDelete(null)
    setDeleting(id)
    try {
      await plansApi.delete(id)
      setPlans(prev => prev.filter(p => p.id !== id))
    } catch (err) {
      setError(err.message)
    } finally {
      setDeleting(null)
    }
  }

  function handleSelect(plan) {
    selectPlan(plan)
    navigate('/coach')
  }

  function signOut() {
    localStorage.removeItem('token')
    localStorage.removeItem('activePlanId')
    navigate('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <span className="text-gray-400 text-sm">Loading…</span>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950">

      {/* Delete confirmation modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-sm p-6 space-y-4 shadow-2xl">
            <h2 className="text-white font-semibold text-lg">Delete plan?</h2>
            <p className="text-gray-400 text-sm">
              <span className="text-white font-medium">"{confirmDelete.name}"</span> and all its themes,
              questions, and progress will be permanently deleted. This cannot be undone.
            </p>
            <div className="flex gap-3 pt-1">
              <button
                onClick={confirmDeletePlan}
                className="flex-1 bg-red-600 hover:bg-red-500 text-white rounded-lg py-2.5 text-sm font-medium transition-colors"
              >
                Delete
              </button>
              <button
                onClick={() => setConfirmDelete(null)}
                className="flex-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg py-2.5 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <span className="text-white font-bold text-lg tracking-tight">TechPrep</span>
        <button onClick={signOut} className="text-sm text-gray-500 hover:text-gray-300 transition-colors">
          Sign out
        </button>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-12 space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">Your Study Plans</h1>
          <p className="text-gray-400 text-sm">
            Each plan has its own themes, questions, and SM-2 progress. Select one to start.
          </p>
        </div>

        {error && (
          <p className="text-red-400 text-sm bg-red-400/10 rounded-lg px-4 py-2">{error}</p>
        )}

        {/* Plan list */}
        {plans.length === 0 && !creating && (
          <div className="text-center py-16 bg-gray-900 border border-gray-800 rounded-2xl">
            <p className="text-3xl mb-3">📚</p>
            <p className="text-white font-medium mb-1">No plans yet</p>
            <p className="text-gray-400 text-sm mb-6">Create your first study plan to get started.</p>
            <button
              onClick={() => setCreating(true)}
              className="bg-blue-600 hover:bg-blue-500 text-white px-5 py-2.5 rounded-lg text-sm font-medium transition-colors"
            >
              Create a plan
            </button>
          </div>
        )}

        <div className="space-y-3">
          {plans.map((plan) => (
            <div key={plan.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-center justify-between gap-4">
              <div className="flex-1 min-w-0">
                <p className="text-white font-medium truncate">{plan.name}</p>
                {plan.description && (
                  <p className="text-gray-400 text-sm mt-0.5 truncate">{plan.description}</p>
                )}
                <div className="flex gap-3 mt-2 text-xs text-gray-500">
                  <span>{plan.theme_count} theme{plan.theme_count !== 1 ? 's' : ''}</span>
                  <span>·</span>
                  <span>{plan.question_count} question{plan.question_count !== 1 ? 's' : ''}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  onClick={() => handleDelete(plan)}
                  disabled={deleting === plan.id}
                  className="text-gray-600 hover:text-red-400 text-xs transition-colors disabled:opacity-40 px-2 py-1"
                >
                  {deleting === plan.id ? '…' : 'Delete'}
                </button>
                <button
                  onClick={() => handleSelect(plan)}
                  className="bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg font-medium transition-colors"
                >
                  Select →
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Create form */}
        {creating ? (
          <form onSubmit={handleCreate} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
            <p className="text-white font-medium">New plan</p>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Plan name (e.g. Google SWE Prep)"
              required
              autoFocus
              className="w-full bg-gray-800 text-white placeholder-gray-500 rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
              className="w-full bg-gray-800 text-white placeholder-gray-500 rounded-lg px-4 py-2.5 text-sm outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-3">
              <button type="submit"
                className="flex-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg py-2.5 text-sm font-medium transition-colors">
                Create
              </button>
              <button type="button" onClick={() => { setCreating(false); setName(''); setDescription('') }}
                className="px-4 py-2.5 text-gray-400 hover:text-gray-200 text-sm transition-colors">
                Cancel
              </button>
            </div>
          </form>
        ) : (
          plans.length > 0 && (
            <button
              onClick={() => setCreating(true)}
              className="w-full border border-dashed border-gray-700 hover:border-gray-500 text-gray-500 hover:text-gray-300 rounded-xl py-4 text-sm transition-colors"
            >
              + New plan
            </button>
          )
        )}
      </main>
    </div>
  )
}
