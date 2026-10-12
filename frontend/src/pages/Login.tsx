import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../authContext.ts'
import Dan from '../components/Dan.tsx'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/account" replace />

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    setError(null)
    setSubmitting(true)
    try {
      await login(String(data.get('email')), String(data.get('password')))
      navigate('/account')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not log in.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-card">
      <Dan size={72} mood="wink" className="auth-dan" />
      <h1>Log in</h1>
      <p className="muted">Welcome back to Campus Customs.</p>
      <form onSubmit={handleSubmit} className="form">
        <label>
          Email
          <input type="email" name="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input type="password" name="password" autoComplete="current-password" required />
        </label>
        <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      <p className="muted small">
        New here? <Link to="/create-account" className="text-link">Create an account</Link>
      </p>
    </div>
  )
}
