import { Navigate } from 'react-router-dom'
import { usePlan } from '../context/PlanContext'

export default function ProtectedRoute({ children, requirePlan = true }) {
  const token = localStorage.getItem('token')
  const { activePlan, loading } = usePlan()

  if (!token) return <Navigate to="/" replace />

  // Wait for PlanContext to finish restoring from localStorage
  if (loading) {
    return <div className="min-h-screen bg-gray-950" />
  }

  // Pages that need an active plan (coach, interview, dashboard)
  if (requirePlan && !activePlan) {
    return <Navigate to="/plans" replace />
  }

  return children
}
