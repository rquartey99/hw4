import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchProducts, type ProductSummary } from '../api.ts'
import Dan from '../components/Dan.tsx'
import ProductCard from '../components/ProductCard.tsx'

export default function Home() {
  const [featured, setFeatured] = useState<ProductSummary[]>([])

  useEffect(() => {
    // Feature one in-stock product from each category.
    fetchProducts()
      .then((products) => {
        const seen = new Set<string>()
        setFeatured(
          products.filter((p) => {
            if (p.total_stock === 0 || seen.has(p.category)) return false
            seen.add(p.category)
            return true
          }).slice(0, 4),
        )
      })
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        <div className="hero-art" aria-hidden="true">
          <span className="hero-bubble">Boola Boola!</span>
          <Dan size={220} mood="happy" />
        </div>
        <div className="hero-text">
          <span className="eyebrow">Yale apparel · New Haven</span>
          <h1>Wear your Yale pride.</h1>
          <p>
            Hoodies, crewnecks, tees and quarter-zips for students, families and fans — plus a shop assistant
            ready to help you find the right fit.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="btn btn-primary">
              Shop all products
            </Link>
            <Link to="/about" className="btn btn-outline">
              About us
            </Link>
          </div>
        </div>
      </section>

      {featured.length > 0 && (
        <section>
          <div className="section-heading">
            <h2>
              <Dan size={34} mood="wink" /> Dan&apos;s picks
            </h2>
            <Link to="/products" className="text-link">
              View all →
            </Link>
          </div>
          <div className="product-grid">
            {featured.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      )}
    </>
  )
}
