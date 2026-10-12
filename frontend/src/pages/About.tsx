import { Link } from 'react-router-dom'

export default function About() {
  return (
    <div className="prose">
      <h1>About Us</h1>
      <p>
        Campus Customs is a Yale apparel shop based in New Haven. We carry hoodies, crewnecks, T-shirts,
        quarter-zips, fleeces and jackets for students, alumni, families and fans.
      </p>
      <p>
        Our collection covers classic Yale wordmarks, bulldog designs, varsity sports,
        family pieces like “Yale Mom” and “Yale Grandpa,” and gear for The Game.
      </p>
      <h2>Need help choosing?</h2>
      <p>
        Open the chat in the bottom-right corner to ask our shop assistant about styles, sizes, or what's in
        stock.
      </p>
      <Link to="/products" className="btn btn-primary">
        Browse products
      </Link>
    </div>
  )
}
