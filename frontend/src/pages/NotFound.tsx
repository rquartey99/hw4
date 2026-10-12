import { Link } from 'react-router-dom'
import Dan from '../components/Dan.tsx'

export default function NotFound() {
  return (
    <div className="empty-state">
      <Dan size={140} mood="sleepy" />
      <h1>Page not found</h1>
      <p className="muted">Dan searched everywhere, but that page doesn't exist.</p>
      <Link to="/" className="btn btn-outline">
        Go home
      </Link>
    </div>
  )
}
