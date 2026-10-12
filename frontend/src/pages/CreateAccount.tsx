import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../authContext.ts'
import Dan from '../components/Dan.tsx'

const MIN_PASSWORD = 8

export default function CreateAccount() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) return <Navigate to="/account" replace />

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const data = new FormData(e.currentTarget)
    const password = String(data.get('password'))
    if (password !== data.get('confirm')) {
      setError("Passwords don't match.")
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      await register({
        first_name: String(data.get('first_name')).trim(),
        last_name: String(data.get('last_name')).trim(),
        email: String(data.get('email')).trim(),
        password,
      })
      navigate('/account')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create your account.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-card">
      <Dan size={72} mood="happy" className="auth-dan" />
      <h1>Create Account</h1>
      <p className="muted">Save your chats with the shop assistant.</p>
      <form onSubmit={handleSubmit} className="form">
        <div className="form-row">
          <label>
            First name
            <input name="first_name" autoComplete="given-name" maxLength={50} required />
          </label>
          <label>
            Last name
            <input name="last_name" autoComplete="family-name" maxLength={50} required />
          </label>
        </div>
        <label>
          Email
          <input type="email" name="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input
            type="password"
            name="password"
            autoComplete="new-password"
            minLength={MIN_PASSWORD}
            maxLength={128}
            required
          />
          <span className="hint">At least {MIN_PASSWORD} characters.</span>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            name="confirm"
            autoComplete="new-password"
            minLength={MIN_PASSWORD}
            maxLength={128}
            required
          />
        </label>
        <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}
      <p className="muted small">
        Already have an account? <Link to="/login" className="text-link">Log in</Link>
      </p>
    </div>
  )
}
