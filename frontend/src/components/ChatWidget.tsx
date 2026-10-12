import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate, type Location } from 'react-router-dom'
import {
  clearChatHistory,
  fetchChatHistory,
  formatPrice,
  sendChat,
  type ChatTurn,
  type HistoryMessage,
  type PageContext,
  type PageResults,
  type ProductCardData,
} from '../api.ts'
import { useAuth } from '../authContext.ts'
import { useChatResults, type ChatResults } from '../chatResultsContext.ts'
import ChatMarkdown from './ChatMarkdown.tsx'
import Dan from './Dan.tsx'

interface ChatMessage {
  key: string
  role: 'user' | 'assistant'
  content: string
  products?: ProductCardData[]
  pageResults?: PageResults // search matches that were shown on the Products page
  error?: boolean
  greeting?: boolean
}

const MAX_HISTORY = 12 // earlier messages guests send along for context
const CHAT_RESULTS_PATH = '/products?from=chat'

const PAGE_TYPES: Record<string, PageContext['page_type']> = {
  '/': 'home',
  '/products': 'products',
  '/about': 'about',
  '/login': 'login',
  '/create-account': 'create_account',
  '/account': 'account',
}

// Describes the page the customer is on, sent with every chat message.
function pageContext(location: Location, results: ChatResults | null): PageContext {
  const path = location.pathname + location.search
  const product = location.pathname.match(/^\/products\/([^/]+)$/)
  if (product) return { path, page_type: 'product', product_id: decodeURIComponent(product[1]) }
  if (location.pathname === '/products' && new URLSearchParams(location.search).get('from') === 'chat') {
    return { path, page_type: 'chat_results', results_title: results?.title }
  }
  return { path, page_type: PAGE_TYPES[location.pathname] ?? 'other' }
}

function greeting(firstName?: string): ChatMessage {
  return {
    key: 'greeting',
    role: 'assistant',
    greeting: true,
    content: firstName
      ? `Woof, hi ${firstName}! I'm Handsome Dan, the Campus Customs shop assistant. Your chat is saved to your account, so we can pick up where you left off.`
      : "Woof! I'm Handsome Dan, the Campus Customs shop assistant. Ask me about products, sizes, or stock.",
  }
}

const fromHistory = (m: HistoryMessage): ChatMessage => ({
  key: `db-${m.id}`,
  role: m.role,
  content: m.content,
  products: m.products,
  pageResults: m.page_results ?? undefined,
})

// App remounts this component when the logged-in user changes, so one person's chat never shows for another.
export default function ChatWidget() {
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>(() => [greeting(user?.first_name)])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [historyNote, setHistoryNote] = useState<string | null>(null)
  const { results, showResults } = useChatResults()
  const location = useLocation()
  const navigate = useNavigate()
  const nextId = useRef(1)
  const listRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Logged-in customers: reload their saved chat from the database.
  useEffect(() => {
    if (!user) return
    let current = true
    fetchChatHistory()
      .then((saved) => {
        if (!current || saved.length === 0) return
        setMessages([greeting(user.first_name), ...saved.map(fromHistory)])
        setHistoryNote(`${saved.length} saved ${saved.length === 1 ? 'message' : 'messages'} loaded`)
      })
      .catch(() => current && setHistoryNote("Couldn't load your saved chat."))
    return () => {
      current = false
    }
  }, [user])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending, open])

  useEffect(() => {
    if (open && !sending) inputRef.current?.focus()
  }, [open, sending])

  function openOnPage(pageResults: PageResults) {
    showResults(pageResults)
    navigate(CHAT_RESULTS_PATH)
  }

  async function clearSaved() {
    if (!window.confirm('Clear your saved chat history? This deletes it from your account.')) return
    try {
      await clearChatHistory()
      setMessages([greeting(user?.first_name)])
      setHistoryNote('Saved chat cleared')
    } catch {
      setHistoryNote("Couldn't clear your chat. Please try again.")
    }
  }

  async function send(e: FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text || sending) return

    // Guests send their recent turns for context. Logged-in customers don't need to: the server loads
    // their saved history from the database.
    const history: ChatTurn[] = user
      ? []
      : messages
          .filter((m) => !m.greeting && !m.error)
          .slice(-MAX_HISTORY)
          .map(({ role, content }) => ({ role, content }))

    setMessages((prev) => [...prev, { key: `local-${nextId.current++}`, role: 'user', content: text }])
    setDraft('')
    setSending(true)
    try {
      const reply = await sendChat(text, history, pageContext(location, results))
      const pageResults = reply.page_results ?? undefined
      setMessages((prev) => [
        ...prev,
        { key: `local-${nextId.current++}`, role: 'assistant', content: reply.reply, products: reply.products, pageResults },
      ])
      // Search results go to the Products page, which renders them as product cards.
      if (pageResults) openOnPage(pageResults)
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          key: `local-${nextId.current++}`,
          role: 'assistant',
          content: err instanceof Error ? err.message : 'Something went wrong. Please try again.',
          error: true,
        },
      ])
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="chat">
      {open && (
        <section className="chat-panel" aria-label="Chat with Handsome Dan">
          <header className="chat-header">
            <Dan size={38} mood="wink" badge className="chat-header-dan" />
            <div className="chat-header-text">
              <strong>Handsome Dan</strong>
              <span className="chat-status">
                {user ? `Saved to ${user.email}` : "Guest · this chat isn't saved"}
              </span>
            </div>
            <div className="chat-header-actions">
              {user && (
                <button type="button" className="chat-clear" onClick={clearSaved}>
                  Clear
                </button>
              )}
              <button type="button" className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
                ×
              </button>
            </div>
          </header>
          <div className="chat-messages" ref={listRef} aria-live="polite">
            {historyNote && <p className="chat-note">{historyNote}</p>}
            {messages.map((m) => (
              <div key={m.key} className={`chat-row ${m.role}`}>
                <div className="chat-line">
                  {m.role === 'assistant' && <Dan size={28} mood={m.error ? 'sleepy' : 'happy'} badge className="chat-avatar" />}
                  <div className={`chat-bubble ${m.role}${m.error ? ' error' : ''}`}>
                    {m.role === 'assistant' ? <ChatMarkdown text={m.content} /> : m.content}
                  </div>
                </div>
                {m.pageResults && (
                  <button type="button" className="chat-page-link" onClick={() => m.pageResults && openOnPage(m.pageResults)}>
                    View {m.pageResults.products.length} results on the page →
                  </button>
                )}
                {m.products && m.products.length > 0 && (
                  <div className="chat-products">
                    {m.products.map((p) => (
                      <Link key={p.product_id} to={`/products/${p.product_id}`} className="chat-product">
                        <img src={p.image_url} alt="" loading="lazy" />
                        <span className="chat-product-name">{p.name}</span>
                        <span className="chat-product-price">
                          {formatPrice(p.price)}
                          {!p.in_stock && ' · Sold out'}
                        </span>
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {sending && (
              <div className="chat-row assistant">
                <div className="chat-line">
                  <Dan size={28} mood="thinking" badge className="chat-avatar" />
                  <div className="chat-bubble assistant typing" aria-label="Handsome Dan is typing">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
            )}
          </div>
          <form className="chat-input" onSubmit={send}>
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder={sending ? 'Waiting for a reply…' : 'Type a message…'}
              aria-label="Message"
              maxLength={1000}
              disabled={sending}
            />
            <button type="submit" className="btn btn-primary btn-sm" disabled={!draft.trim() || sending}>
              Send
            </button>
          </form>
        </section>
      )}
      <button
        type="button"
        className="chat-toggle"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? 'Close chat' : 'Chat with Handsome Dan'}
        aria-expanded={open}
      >
        {open ? '×' : <Dan size={60} mood="wink" badge />}
      </button>
    </div>
  )
}
