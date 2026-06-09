import { useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LayoutDashboard, Upload, FileText, TrendingUp, LogOut, Moon, Sun } from 'lucide-react'

export default function Navbar() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()

  const [isDark, setIsDark] = useState(false)

  useEffect(() => {
    // Check local storage or system preference
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setIsDark(true)
      document.documentElement.classList.add('dark')
    }
  }, [])

  const toggleTheme = () => {
    if (isDark) {
      document.documentElement.classList.remove('dark')
      localStorage.theme = 'light'
      setIsDark(false)
    } else {
      document.documentElement.classList.add('dark')
      localStorage.theme = 'dark'
      setIsDark(true)
    }
  }

  const handleLogout = async () => {
    await signOut()
    navigate('/login')
  }

  const navItems = [
    { path: '/', icon: <LayoutDashboard size={16} />, label: 'Dashboard' },
    { path: '/upload', icon: <Upload size={16} />, label: 'Upload' },
    { path: '/invoices', icon: <FileText size={16} />, label: 'Invoices' },
    { path: '/predictions', icon: <TrendingUp size={16} />, label: 'Predictions' },
  ]

  return (
    <nav className="navbar-container" style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      height: 56,
      background: '#ffffff',
      borderBottom: '1px solid var(--border)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
        <span style={{ fontSize: 16, fontWeight: 700, color: 'var(--accent)', letterSpacing: '-0.3px' }}>
          ⚡ ExpenseAI
        </span>

        <div className="nav-links" style={{ display: 'flex', gap: 2 }}>
          {navItems.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className="nav-link-item"
              style={({ isActive }) => ({
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '6px 14px',
                borderRadius: 'var(--radius-sm)',
                fontSize: 13, fontWeight: 500,
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-light)' : 'transparent',
                textDecoration: 'none',
                transition: 'all 0.15s',
              })}
            >
              {item.icon}
              <span className="nav-label">{item.label}</span>
            </NavLink>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button onClick={toggleTheme} className="btn btn-secondary" style={{ padding: '4px', borderRadius: '50%' }}>
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <span className="user-email" style={{ fontSize: 13, color: 'var(--text-muted)' }}>{user?.email}</span>
        <button onClick={handleLogout} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: 12 }}>
          <LogOut size={13} /> <span className="nav-label">Logout</span>
        </button>
      </div>
    </nav>
  )
}
