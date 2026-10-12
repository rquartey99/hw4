import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../authContext.ts'
import Dan from '../components/Dan.tsx'

export default function Account() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  if (loading) return <p className="muted">Loading…</p>
  if (!user) return <Navigate to="/login" replace />

  async function handleLogout() {
    try {
      await logout()
      navigate('/login')
    } catch {
      setError('Could not log out. Please try again.')
    }
  }

  const memberSince = new Date(user.created_at.replace(' ', 'T') + 'Z').toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  return (
    <div className="auth-card">
      <Dan size={72} mood="happy" className="auth-dan" />
      <span className="eyebrow">My Account</span>
      <h1>Hi, {user.first_name}!</h1>
      <p className="muted">You're logged in to Campus Customs.</p>

      <dl className="account-details">
        <div>
          <dt>Name</dt>
          <dd>
            {user.first_name} {user.last_name}
          </dd>
        </div>
        <div>
          <dt>Email</dt>
          <dd>{user.email}</dd>
        </div>
        <div>
          <dt>Member since</dt>
          <dd>{memberSince}</dd>
        </div>
      </dl>

      <div className="account-actions">
        <Link to="/products" className="btn btn-primary">
          Shop products
        </Link>
        <button type="button" className="btn btn-outline" onClick={handleLogout}>
          Log out
        </button>
      </div>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
