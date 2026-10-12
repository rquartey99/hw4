import type { ProductSummary } from './api.ts'

// Product filters for the Products page. They live in the URL (?category=Hoodies&size=M,L&color=Navy&price=40-60)
// so Back from a product page, refreshing, or sharing the link keeps the same filtered list.

export const SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL']

export const COLORS: { name: string; swatch: string }[] = [
  { name: 'Navy', swatch: '#1f2f5c' },
  { name: 'Blue', swatch: '#3b73c4' },
  { name: 'Gray', swatch: '#9aa0a6' },
  { name: 'White', swatch: '#ffffff' },
  { name: 'Black', swatch: '#1d1d1d' },
  { name: 'Red', swatch: '#c0392b' },
  { name: 'Yellow & Gold', swatch: '#e2b93b' },
  { name: 'Green', swatch: '#3c8d4f' },
  { name: 'Multicolor', swatch: 'conic-gradient(#c0392b, #e2b93b, #3c8d4f, #3b73c4, #c0392b)' },
]

export const PRICE_RANGES: { id: string; label: string; min: number; max: number }[] = [
  { id: 'under-40', label: 'Under $40', min: 0, max: 39.99 },
  { id: '40-60', label: '$40 – $60', min: 40, max: 60 },
  { id: '60-80', label: '$60 – $80', min: 60.01, max: 80 },
  { id: '80-plus', label: '$80 and up', min: 80.01, max: Infinity },
]

export const SORTS: { id: string; label: string }[] = [
  { id: 'name', label: 'Name (A–Z)' },
  { id: 'price-asc', label: 'Price: low to high' },
  { id: 'price-desc', label: 'Price: high to low' },
]

export interface Filters {
  category: string | null
  sizes: string[]
  colors: string[]
  prices: string[]
  inStock: boolean
  sort: string
}

const list = (params: URLSearchParams, key: string) => params.get(key)?.split(',').filter(Boolean) ?? []

export function readFilters(params: URLSearchParams): Filters {
  return {
    category: params.get('category'),
    sizes: list(params, 'size'),
    colors: list(params, 'color'),
    prices: list(params, 'price'),
    inStock: params.get('instock') === '1',
    sort: params.get('sort') ?? 'name',
  }
}

export function writeFilters(f: Filters): URLSearchParams {
  const params = new URLSearchParams()
  if (f.category) params.set('category', f.category)
  if (f.sizes.length) params.set('size', f.sizes.join(','))
  if (f.colors.length) params.set('color', f.colors.join(','))
  if (f.prices.length) params.set('price', f.prices.join(','))
  if (f.inStock) params.set('instock', '1')
  if (f.sort !== 'name') params.set('sort', f.sort)
  return params
}

export const activeFilterCount = (f: Filters) =>
  (f.category ? 1 : 0) + f.sizes.length + f.colors.length + f.prices.length + (f.inStock ? 1 : 0)

// Within one filter, any selected option matches (Navy OR Gray); across filters, all must match.
export function applyFilters(products: ProductSummary[], f: Filters): ProductSummary[] {
  const ranges = PRICE_RANGES.filter((r) => f.prices.includes(r.id))
  const shown = products.filter(
    (p) =>
      (!f.category || p.category === f.category) &&
      // Size means "in stock in that size".
      (f.sizes.length === 0 || f.sizes.some((s) => p.sizes_in_stock.includes(s))) &&
      (f.colors.length === 0 || f.colors.some((c) => p.color_families.includes(c))) &&
      (ranges.length === 0 || ranges.some((r) => p.price >= r.min && p.price <= r.max)) &&
      (!f.inStock || p.total_stock > 0),
  )
  const byName = (a: ProductSummary, b: ProductSummary) => a.name.localeCompare(b.name)
  if (f.sort === 'price-asc') return shown.sort((a, b) => a.price - b.price || byName(a, b))
  if (f.sort === 'price-desc') return shown.sort((a, b) => b.price - a.price || byName(a, b))
  return shown.sort(byName)
}
