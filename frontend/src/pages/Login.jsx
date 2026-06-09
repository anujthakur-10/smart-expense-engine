import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Mail, Lock, ArrowRight, UserPlus } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Login() {
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { signIn, signUp } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      if (isRegister) {
        const { error } = await signUp(email, password)
        if (error) throw error
        toast.success('Account created! Check email for verification.')
      } else {
        const { error } = await signIn(email, password)
        if (error) throw error
        toast.success('Welcome back!')
        navigate('/')
      }
    } catch (err) {
      toast.error(err.message || 'Authentication failed')
    }
    setLoading(false)
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#f5f6f8',
    }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 48, height: 48,
            borderRadius: 'var(--radius-md)',
            background: 'var(--accent)',
            display: 'inline-flex',
            alignItems: 'center', justifyContent: 'center',
            marginBottom: 12,
          }}>
            <span style={{ fontSize: 22, color: 'white' }}>⚡</span>
          </div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--text-primary)' }}>
            ExpenseAI
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 14, marginTop: 4 }}>
            Smart Expense Engine for Indian SMEs
          </p>
        </div>

        {/* Form Card */}
        <div className="card" style={{ padding: 32 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 24 }}>
            {isRegister ? 'Create Account' : 'Sign In'}
          </h2>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label>Email</label>
              <div style={{ position: 'relative' }}>
                <Mail size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input id="auth-email" className="input-field" type="email" value={email}
                  onChange={e => setEmail(e.target.value)} placeholder="you@example.com"
                  required style={{ paddingLeft: 34 }} />
              </div>
            </div>

            <div style={{ marginBottom: 24 }}>
              <label>Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={15} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input id="auth-password" className="input-field" type="password" value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder={isRegister ? 'Min 6 characters' : 'Your password'}
                  required minLength={6} style={{ paddingLeft: 34 }} />
              </div>
            </div>

            <button id="auth-submit" type="submit" className="btn btn-primary" disabled={loading}
              style={{ width: '100%', padding: '10px', fontSize: 14 }}>
              {loading ? 'Processing...' : (
                <>{isRegister ? <UserPlus size={16} /> : <ArrowRight size={16} />} {isRegister ? 'Create Account' : 'Sign In'}</>
              )}
            </button>
          </form>

          <p style={{ textAlign: 'center', marginTop: 20, fontSize: 13, color: 'var(--text-secondary)' }}>
            {isRegister ? 'Already have an account?' : "Don't have an account?"}{' '}
            <button onClick={() => setIsRegister(!isRegister)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--accent)', fontWeight: 600, fontSize: 13 }}>
              {isRegister ? 'Sign In' : 'Register'}
            </button>
          </p>
        </div>
      </div>
    </div>
  )
}
