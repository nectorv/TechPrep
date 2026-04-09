import { createContext, useContext, useState, useEffect } from 'react'
import { plansApi } from '../api/plans'

const PlanContext = createContext(null)

export function PlanProvider({ children }) {
  const [activePlan, setActivePlanState] = useState(null)
  const [loading, setLoading] = useState(true)

  // On mount, restore active plan from localStorage
  useEffect(() => {
    const token = localStorage.getItem('token')
    const savedId = localStorage.getItem('activePlanId')
    if (!token || !savedId) { setLoading(false); return }

    plansApi.get(savedId)
      .then(setActivePlanState)
      .catch(() => localStorage.removeItem('activePlanId'))
      .finally(() => setLoading(false))
  }, [])

  function selectPlan(plan) {
    setActivePlanState(plan)
    localStorage.setItem('activePlanId', plan.id)
  }

  function clearPlan() {
    setActivePlanState(null)
    localStorage.removeItem('activePlanId')
  }

  return (
    <PlanContext.Provider value={{ activePlan, selectPlan, clearPlan, loading }}>
      {children}
    </PlanContext.Provider>
  )
}

export function usePlan() {
  return useContext(PlanContext)
}
