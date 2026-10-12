import { Link } from 'react-router-dom'
import { formatPrice, type ProductCardData, type ProductSummary } from '../api.ts'

// Accepts a catalogue product (Products/Home pages) or a chat search result (ProductCardData).
type CardProduct = Pick<ProductSummary, 'product_id' | 'name' | 'category' | 'price' | 'image_url'> &
  (Pick<ProductSummary, 'total_stock'> | Pick<ProductCardData, 'in_stock'>)

export default function ProductCard({ product }: { product: CardProduct }) {
  const soldOut = 'total_stock' in product ? product.total_stock === 0 : !product.in_stock

  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card-image">
        <img src={product.image_url} alt={product.name} loading="lazy" />
      </div>
      <div className="product-card-body">
        <span className="product-card-category">{product.category}</span>
        <h3 className="product-card-name">{product.name}</h3>
        <div className="product-card-footer">
          <span className="price">{formatPrice(product.price)}</span>
          {soldOut && <span className="badge badge-muted">Sold out</span>}
        </div>
      </div>
    </Link>
  )
}
