import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { PlanProvider } from './context/PlanContext'
import Login from './pages/Login'
import Plans from './pages/Plans'
import Coach from './pages/Coach'
import Interview from './pages/Interview'
import Dashboard from './pages/Dashboard'
import ProtectedRoute from './components/ProtectedRoute'

export default function App() {
  return (
    <BrowserRouter>
      <PlanProvider>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/plans" element={<ProtectedRoute requirePlan={false}><Plans /></ProtectedRoute>} />
          <Route path="/coach"     element={<ProtectedRoute><Coach /></ProtectedRoute>} />
          <Route path="/interview" element={<ProtectedRoute><Interview /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </PlanProvider>
    </BrowserRouter>
  )
}
