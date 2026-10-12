import { Link } from 'react-router-dom'
import Dan from './Dan.tsx'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Dan size={64} mood="happy" />
          <div>
            <strong>Campus Customs</strong>
            <p>Yale apparel for students, families and fans. New Haven, CT.</p>
          </div>
        </div>
        <nav className="footer-links" aria-label="Footer">
          <Link to="/products">Shop all</Link>
          <Link to="/products?category=Hoodies">Hoodies</Link>
          <Link to="/products?category=Sweatshirts">Sweatshirts</Link>
          <Link to="/about">About us</Link>
        </nav>
        <p className="footer-motto">Boola Boola! · For God, for Country, and for Yale</p>
      </div>
      <p className="footer-copy">© {new Date().getFullYear()} Campus Customs · Handsome Dan artwork is an original tribute, not an official Yale logo.</p>
    </footer>
  )
}
