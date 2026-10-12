import { useEffect, useState } from 'react'
import { fetchRelatedProducts, type ProductSummary } from '../api.ts'
import ProductCard from './ProductCard.tsx'

// "You might also like": similar products chosen by the backend (same category, theme and colors).
export default function RelatedProducts({ productId }: { productId: string }) {
  const [related, setRelated] = useState<ProductSummary[]>([])

  useEffect(() => {
    let current = true
    fetchRelatedProducts(productId)
      .then((products) => current && setRelated(products))
      .catch(() => current && setRelated([]))
    return () => {
      current = false
    }
  }, [productId])

  if (related.length === 0) return null

  return (
    <section className="related" aria-labelledby="related-heading">
      <h2 id="related-heading">You might also like</h2>
      <div className="product-grid">
        {related.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </section>
  )
}
