import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../authContext.ts'
import Dan from './Dan.tsx'

const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products', end: false },
  { to: '/about', label: 'About Us', end: false },
]

export default function Navbar() {
  const { user, loading } = useAuth()
  const linkClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'nav-link active' : 'nav-link')
  const buttonClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'btn btn-primary btn-sm active' : 'btn btn-primary btn-sm'

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <Link to="/" className="brand" aria-label="Campus Customs home">
          <Dan size={40} mood="wink" badge className="brand-dan" />
          <span className="brand-text">
            Campus Customs
            <small>Bulldog-approved Yale gear</small>
          </span>
        </Link>
        <nav className="nav-links" aria-label="Main">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.end} className={linkClass}>
              {l.label}
            </NavLink>
          ))}
          {/* Hide account links until we know whether someone is logged in, so they don't flicker. */}
          {!loading &&
            (user ? (
              <NavLink to="/account" className={buttonClass}>
                Hi, {user.first_name}
              </NavLink>
            ) : (
              <>
                <NavLink to="/login" className={linkClass}>
                  Log in
                </NavLink>
                <NavLink to="/create-account" className={buttonClass}>
                  Create Account
                </NavLink>
              </>
            ))}
        </nav>
      </div>
    </header>
  )
}
