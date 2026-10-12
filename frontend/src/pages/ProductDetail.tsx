import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchProduct, formatPrice, NotFoundError, type ProductDetail as Product } from '../api.ts'
import RelatedProducts from '../components/RelatedProducts.tsx'
import Dan from '../components/Dan.tsx'

const LOW_STOCK = 5

export default function ProductDetail() {
  const { productId = '' } = useParams()
  // Results are tagged with the id they belong to, so a stale page never flashes while the next one loads.
  const [result, setResult] = useState<{ id: string; product?: Product; error?: string } | null>(null)

  useEffect(() => {
    // Opening another product (e.g. from "You might also like") starts at the top of the page.
    window.scrollTo({ top: 0 })
    let current = true
    fetchProduct(productId)
      .then((product) => current && setResult({ id: productId, product }))
      .catch((e) => {
        if (!current) return
        const error = e instanceof NotFoundError ? "We couldn't find that product." : 'Could not load this product.'
        setResult({ id: productId, error })
      })
    return () => {
      current = false
    }
  }, [productId])

  const loaded = result?.id === productId ? result : null
  const product = loaded?.product
  const error = loaded?.error

  if (error) {
    return (
      <div className="empty-state">
        <Dan size={120} mood="sleepy" />
        <p className="alert">{error}</p>
        <Link to="/products" className="btn btn-outline">
          Back to products
        </Link>
      </div>
    )
  }
  if (!product) {
    return (
      <p className="muted loading">
        <Dan size={32} mood="thinking" /> Fetching this product…
      </p>
    )
  }

  const available = product.sizes.filter((s) => s.quantity > 0)

  return (
    <>
      <Link to="/products" className="text-link back-link">
        ← All products
      </Link>
      <article className="detail">
        <div className="detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>

        <div className="detail-info">
          <span className="eyebrow">{product.category}</span>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p className="detail-description">{product.description}</p>

          <dl className="detail-meta">
            <div>
              <dt>Style</dt>
              <dd className="capitalize">{product.garment_type}</dd>
            </div>
            <div>
              <dt>Colors</dt>
              <dd className="capitalize">{product.colors.join(', ')}</dd>
            </div>
          </dl>

          <h2 className="detail-subheading">Sizes &amp; stock</h2>
          {product.sizes.length === 0 ? (
            <p className="muted">Size information isn't available for this item.</p>
          ) : (
            <>
              <ul className="size-grid">
                {product.sizes.map((s) => (
                  <li key={s.size} className={s.quantity === 0 ? 'size sold-out' : 'size'}>
                    <span className="size-label">{s.size}</span>
                    <span className="size-stock">
                      {s.quantity === 0 ? 'Sold out' : s.quantity <= LOW_STOCK ? `Only ${s.quantity} left` : `${s.quantity} in stock`}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="muted small">
                {available.length === 0
                  ? 'Currently sold out in all sizes.'
                  : `${product.total_stock} in stock across ${available.length} of ${product.sizes.length} sizes.`}
              </p>
            </>
          )}
        </div>
      </article>
      {/* Keyed so the list resets when you move from one product to another. */}
      <RelatedProducts key={product.product_id} productId={product.product_id} />
    </>
  )
}
