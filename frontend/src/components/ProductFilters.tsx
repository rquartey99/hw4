import { COLORS, PRICE_RANGES, SIZES, type Filters } from '../filters.ts'

interface Props {
  filters: Filters
  categories: string[]
  onChange: (next: Filters) => void
}

const toggle = (values: string[], value: string) =>
  values.includes(value) ? values.filter((v) => v !== value) : [...values, value]

// Sidebar with category, size, color, price and availability filters.
export default function ProductFilters({ filters, categories, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...filters, ...patch })

  return (
    <div className="filters">
      <fieldset className="filter-group">
        <legend>Category</legend>
        <div className="filter-options">
          {[null, ...categories].map((c) => (
            <label key={c ?? 'all'} className="filter-radio">
              <input
                type="radio"
                name="category"
                checked={filters.category === c}
                onChange={() => set({ category: c })}
              />
              {c ?? 'All products'}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="filter-group">
        <legend>Size in stock</legend>
        <div className="size-options">
          {SIZES.map((s) => (
            <button
              key={s}
              type="button"
              className={filters.sizes.includes(s) ? 'size-option active' : 'size-option'}
              aria-pressed={filters.sizes.includes(s)}
              onClick={() => set({ sizes: toggle(filters.sizes, s) })}
            >
              {s}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="filter-group">
        <legend>Color</legend>
        <div className="color-options">
          {COLORS.map((c) => (
            <button
              key={c.name}
              type="button"
              className={filters.colors.includes(c.name) ? 'color-option active' : 'color-option'}
              aria-pressed={filters.colors.includes(c.name)}
              onClick={() => set({ colors: toggle(filters.colors, c.name) })}
            >
              <span className="swatch" style={{ background: c.swatch }} aria-hidden="true" />
              {c.name}
            </button>
          ))}
        </div>
      </fieldset>

      <fieldset className="filter-group">
        <legend>Price</legend>
        <div className="filter-options">
          {PRICE_RANGES.map((r) => (
            <label key={r.id} className="filter-check">
              <input
                type="checkbox"
                checked={filters.prices.includes(r.id)}
                onChange={() => set({ prices: toggle(filters.prices, r.id) })}
              />
              {r.label}
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="filter-group">
        <legend>Availability</legend>
        <label className="filter-check">
          <input type="checkbox" checked={filters.inStock} onChange={() => set({ inStock: !filters.inStock })} />
          Hide sold-out items
        </label>
      </fieldset>
    </div>
  )
}
