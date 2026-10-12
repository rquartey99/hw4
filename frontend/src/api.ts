// Types and fetch helpers for the FastAPI backend (backend/main.py).
// Requests go to /api/..., which Vite proxies to http://127.0.0.1:8000 in development.

export interface ProductSummary {
  product_id: string
  name: string
  garment_type: string
  category: string
  price: number
  colors: string[]
  color_families: string[] // e.g. ["Navy", "Gray"], for the color filter
  sizes_in_stock: string[] // e.g. ["S", "M", "L"], for the size filter
  image_url: string
  total_stock: number
}

// Shop categories in display order (the backend groups garment types into these).
export const CATEGORY_ORDER = ['Hoodies', 'Sweatshirts', 'T-shirts', 'Quarter-zips', 'Jackets & Fleece', 'Long Sleeves']

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductDetail extends ProductSummary {
  description: string
  search_tags: string[]
  sizes: SizeStock[]
}

export class NotFoundError extends Error {}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (res.status === 404) throw new NotFoundError('Not found')
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export const fetchProducts = () => getJson<ProductSummary[]>('/api/products')

export const fetchProduct = (productId: string) =>
  getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)

export const fetchRelatedProducts = (productId: string, limit = 4) =>
  getJson<ProductSummary[]>(`/api/products/${encodeURIComponent(productId)}/related?limit=${limit}`)

export const formatPrice = (price: number) => `$${price.toFixed(2)}`

// ---------- Chat ----------

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ProductCardData {
  product_id: string
  name: string
  category: string
  price: number
  image_url: string
  in_stock: boolean
}

// Search matches the agent found for a "type of item" question, to render on the Products page.
export interface PageResults {
  title: string
  query: string
  products: ProductCardData[]
}

export interface ChatReply {
  reply: string
  products: ProductCardData[] // cards inside the chat
  page_results: PageResults | null // cards on the Products page
}

export type PageType =
  | 'home'
  | 'products'
  | 'chat_results'
  | 'product'
  | 'about'
  | 'login'
  | 'create_account'
  | 'account'
  | 'other'

// Which page the customer is on, so "do you have that in blue?" on a product page means that product.
export interface PageContext {
  path: string
  page_type: PageType
  product_id?: string
  results_title?: string
}

// A saved message, loaded when a logged-in customer comes back.
export interface HistoryMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  products: ProductCardData[]
  page_results: PageResults | null
  created_at: string
}

// Sends one message to the agent with the current page. Guests also send their recent turns;
// for logged-in customers the server reads history from the database instead.
export const sendChat = (message: string, history: ChatTurn[], page: PageContext) =>
  postJson<ChatReply>('/api/chat', { message, history, page })

export async function fetchChatHistory(): Promise<HistoryMessage[]> {
  const res = await fetch('/api/chat/history')
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json() as Promise<HistoryMessage[]>
}

export async function clearChatHistory(): Promise<void> {
  const res = await fetch('/api/chat/history', { method: 'DELETE' })
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
}

// ---------- Accounts ----------

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
  created_at: string
}

export interface RegisterInput {
  first_name: string
  last_name: string
  email: string
  password: string
}

// Turns FastAPI error bodies (a string, or a list of validation errors) into one readable message.
function errorMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0] as { loc?: unknown[]; msg?: string }
    const field = String(first.loc?.at(-1) ?? '').replace('_', ' ')
    return `${field ? `${field[0].toUpperCase()}${field.slice(1)}: ` : ''}${first.msg ?? 'Invalid value'}`
  }
  return `Request failed (${status})`
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (res.status === 204) return undefined as T
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new Error(errorMessage(data, res.status))
  return data as T
}

export const registerAccount = (input: RegisterInput) => postJson<User>('/api/auth/register', input)

export const loginAccount = (email: string, password: string) =>
  postJson<User>('/api/auth/login', { email, password })

export const logoutAccount = () => postJson<void>('/api/auth/logout')

// Returns the logged-in user, or null if there is no valid session cookie.
export async function fetchCurrentUser(): Promise<User | null> {
  const res = await fetch('/api/auth/me')
  if (res.status === 401) return null
  if (!res.ok) throw new Error(`Request failed (${res.status})`)
  return res.json() as Promise<User>
}
