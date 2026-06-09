// components/ProtectedRoute.jsx — Auth Guard
// Unauthenticated users ko login page pe redirect karta hai

import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()

  // Jab tak session check ho raha hai, loading dikhao
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        color: 'var(--text-secondary)',
        fontSize: 'var(--font-size-lg)',
      }}>
        <div className="skeleton" style={{ width: 200, height: 20 }} />
      </div>
    )
  }

  // Agar user logged in nahi hai toh login pe bhejo
  if (!user) {
    return <Navigate to="/login" replace />
  }

  return children
}
