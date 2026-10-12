import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { CATEGORY_ORDER, fetchProducts, type ProductSummary } from '../api.ts'
import { useChatResults } from '../chatResultsContext.ts'
import Dan from '../components/Dan.tsx'
import ProductCard from '../components/ProductCard.tsx'
import ProductFilters from '../components/ProductFilters.tsx'
import {
  COLORS,
  PRICE_RANGES,
  SORTS,
  activeFilterCount,
  applyFilters,
  readFilters,
  writeFilters,
  type Filters,
} from '../filters.ts'

export default function Products() {
  const [params] = useSearchParams()
  const { results } = useChatResults()

  // /products?from=chat shows the latest search results from the chat assistant.
  if (params.get('from') === 'chat') {
    return results ? <ChatResultsView /> : <NoChatResults />
  }
  return <Catalogue />
}

function ChatResultsView() {
  const { results, clearResults } = useChatResults()
  if (!results) return null

  return (
    // Keyed by arrival time so new results replay the fade-in, even when the page is already open.
    <section key={results.receivedAt} className="chat-results">
      <div className="chat-results-banner">
        <div>
          <span className="eyebrow">From the shop assistant</span>
          <h1>{results.title}</h1>
          <p className="muted small">
            {results.products.length} {results.products.length === 1 ? 'match' : 'matches'} · searched for “{results.query}”
          </p>
        </div>
        <Link to="/products" className="btn btn-outline btn-sm" onClick={clearResults}>
          Show all products
        </Link>
      </div>
      <div className="product-grid">
        {results.products.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </section>
  )
}

function NoChatResults() {
  return (
    <div className="empty-state">
      <Dan size={120} mood="sleepy" />
      <h1>No chat results yet</h1>
      <p className="muted">Ask the shop assistant about a type of item, like “what hoodies do you have?”</p>
      <Link to="/products" className="btn btn-outline">
        Browse all products
      </Link>
    </div>
  )
}

function Catalogue() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showFilters, setShowFilters] = useState(false) // small screens: filters open/closed
  const [params, setParams] = useSearchParams()
  const filters = readFilters(params)

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch(() => setError('Could not load products. Is the backend running on port 8000?'))
  }, [])

  const categories = useMemo(() => {
    const present = new Set((products ?? []).map((p) => p.category))
    return CATEGORY_ORDER.filter((c) => present.has(c))
  }, [products])
  const shown = products ? applyFilters(products, filters) : []
  const active = activeFilterCount(filters)

  // replace: true so each click doesn't add a Back-button step; Back still returns here from a product page.
  const update = (next: Filters) => setParams(writeFilters(next), { replace: true })
  const clearAll = () => update({ ...readFilters(new URLSearchParams()), sort: filters.sort })

  // Removable chips summarizing the active filters.
  const chips: { label: string; remove: Partial<Filters> }[] = [
    ...(filters.category ? [{ label: filters.category, remove: { category: null } }] : []),
    ...filters.sizes.map((s) => ({ label: `Size ${s}`, remove: { sizes: filters.sizes.filter((x) => x !== s) } })),
    ...filters.colors
      .filter((c) => COLORS.some((x) => x.name === c))
      .map((c) => ({ label: c, remove: { colors: filters.colors.filter((x) => x !== c) } })),
    ...filters.prices.map((id) => ({
      label: PRICE_RANGES.find((r) => r.id === id)?.label ?? id,
      remove: { prices: filters.prices.filter((x) => x !== id) },
    })),
    ...(filters.inStock ? [{ label: 'In stock', remove: { inStock: false } }] : []),
  ]

  return (
    <>
      <div className="page-heading">
        <h1>{filters.category ?? 'Products'}</h1>
        {products && (
          <p className="muted">
            {shown.length} of {products.length} items
          </p>
        )}
      </div>

      {error && <p className="alert">{error}</p>}
      {!products && !error && (
        <p className="muted loading">
          <Dan size={32} mood="thinking" /> Fetching products…
        </p>
      )}

      {products && (
        <div className="catalogue">
          <aside className={showFilters ? 'catalogue-filters open' : 'catalogue-filters'} aria-label="Filters">
            <div className="filters-heading">
              <h2>Filters</h2>
              {active > 0 && (
                <button type="button" className="text-link link-button" onClick={clearAll}>
                  Clear all
                </button>
              )}
            </div>
            <ProductFilters filters={filters} categories={categories} onChange={update} />
          </aside>

          <section className="catalogue-results">
            <div className="results-toolbar">
              <button
                type="button"
                className="btn btn-outline btn-sm filters-toggle"
                aria-expanded={showFilters}
                onClick={() => setShowFilters((o) => !o)}
              >
                Filters{active > 0 ? ` (${active})` : ''}
              </button>
              <div className="active-filters">
                {chips.map((chip) => (
                  <button
                    key={chip.label}
                    type="button"
                    className="filter-chip"
                    onClick={() => update({ ...filters, ...chip.remove })}
                    aria-label={`Remove filter ${chip.label}`}
                  >
                    {chip.label} <span aria-hidden="true">×</span>
                  </button>
                ))}
              </div>
              <label className="sort">
                Sort
                <select value={filters.sort} onChange={(e) => update({ ...filters, sort: e.target.value })}>
                  {SORTS.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            {shown.length === 0 ? (
              <div className="empty-state">
                <Dan size={110} mood="thinking" />
                <p className="muted">Dan couldn't sniff out anything matching these filters.</p>
                <button type="button" className="btn btn-outline btn-sm" onClick={clearAll}>
                  Clear filters
                </button>
              </div>
            ) : (
              <div className="product-grid">
                {shown.map((p) => (
                  <ProductCard key={p.product_id} product={p} />
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </>
  )
}
