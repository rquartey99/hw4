"""Pydantic types shared by the chat route (main.py), the agent (agent.py) and its tools (tools.py)."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

# ---------- Chat request (website -> FastAPI) ----------


MAX_TURN_CHARS = 4000


class ChatTurn(BaseModel):
    """One earlier message in the conversation (from the browser for guests, from the database for members)."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_TURN_CHARS)


PageType = Literal["home", "products", "chat_results", "product", "about", "login", "create_account", "account", "other"]


class PageContext(BaseModel):
    """Which page the customer is looking at when they send a message (sent by the website)."""

    path: str = Field(max_length=300, description='e.g. "/products/basic-hoodie-big-yale"')
    page_type: PageType = "other"
    product_id: str | None = Field(default=None, max_length=120, description="Set on a single-product page")
    results_title: str | None = Field(default=None, max_length=80, description="Set when chat search results are on screen")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Guests send their own recent turns; for logged-in customers the server loads them from the database.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext | None = None


# ---------- Who is chatting and where they are (agent deps -> tools) ----------


class CustomerProfile(BaseModel):
    """The logged-in customer, as returned by get_customer_profile. Never includes the password hash."""

    logged_in: Literal[True] = True
    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Date the account was created (YYYY-MM-DD)")
    saved_messages: int = Field(description="How many chat messages are saved for this customer")


class GuestProfile(BaseModel):
    """Returned by get_customer_profile when nobody is logged in."""

    logged_in: Literal[False] = False
    note: str = "The customer is a guest (not logged in). Their chat isn't saved; they can log in or create an account."


class CurrentPage(BaseModel):
    """What the customer is looking at, as returned by get_current_page."""

    path: str
    page_type: PageType
    product: "ProductInfo | None" = Field(
        default=None, description="The product on screen, when the customer is on a single-product page"
    )
    results_title: str | None = Field(default=None, description="Heading of chat search results on screen, if any")
    note: str


# ---------- Tool results (tools.py -> agent) ----------


class ProductMatch(BaseModel):
    """A catalogue product as returned by search_products."""

    product_id: str
    name: str
    category: str
    garment_type: str
    price: float
    colors: list[str]
    sizes_in_stock: list[str] = Field(description="Sizes with at least one unit in stock")


class SearchResults(BaseModel):
    """What search_products returns: the matching products plus a plain-language note."""

    total_matches: int = Field(description="How many products matched (0 = the shop doesn't carry this)")
    matches: list[ProductMatch]
    note: str = Field(description="How to read this result, e.g. that zero matches means the shop doesn't carry it")


StockStatus = Literal["in_stock", "low_stock", "sold_out"]


class ProductInfo(BaseModel):
    """Description and price for one product, as returned by get_product_info."""

    product_id: str
    name: str
    category: str
    garment_type: str
    description: str
    colors: list[str]
    price: float = Field(description="Price in US dollars")


class SizeStock(BaseModel):
    """Units in stock for one size of one product (one row of the inventory table)."""

    size: str = Field(description="XS, S, M, L, XL or XXL")
    quantity: int = Field(description="Units in stock right now")
    status: StockStatus = Field(description="sold_out = 0, low_stock = 1-5, in_stock = 6 or more")


class StockReport(BaseModel):
    """Stock for one product, as returned by check_stock."""

    product_id: str
    name: str
    requested_size: SizeStock | None = Field(
        default=None, description="The size the customer asked about, if any"
    )
    sizes: list[SizeStock] = Field(description="Every size, XS to XXL")
    sizes_available: list[str] = Field(description="Sizes with at least one unit in stock")
    total_in_stock: int = Field(description="Units in stock across all sizes")


class LookupFailed(BaseModel):
    """Returned instead of a result when a product or size can't be found. Never guess past this."""

    reason: Literal["product_not_found", "unknown_size"]
    message: str
    suggestions: list[str] = Field(
        default_factory=list, description="'product_id: name' pairs of similar products, or the valid sizes"
    )


class CategorySummary(BaseModel):
    category: str
    product_count: int
    min_price: float
    max_price: float


# ---------- Agent output (agent -> FastAPI) ----------


MAX_PAGE_RESULTS = 30


class PageResultsRequest(BaseModel):
    """Search matches the agent wants shown on the website's Products page (ids only; FastAPI fills in the rest)."""

    title: str = Field(max_length=80, description='Short heading for the results, e.g. "Navy hoodies" or "Bulldog designs"')
    query: str = Field(max_length=200, description="The search_products query (and filters) that found these products")
    product_ids: list[str] = Field(
        min_length=1,
        max_length=MAX_PAGE_RESULTS,
        description="product_id of every matching product from search_products, in the order returned",
    )


class AgentReply(BaseModel):
    """What the model must return. FastAPI turns ids into product cards from the database."""

    reply: str = Field(description="Your message to the customer, in short Markdown")
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=6,
        description="Up to 6 top picks (from tool results only) to show as cards inside the chat; empty if none",
    )
    page_results: PageResultsRequest | None = Field(
        default=None,
        description="Set when the customer asks about a type of item: all search matches to show on the Products page",
    )


# ---------- Chat reply (FastAPI -> website) ----------


class ProductCard(BaseModel):
    """A product shown as a clickable card (in the chat or on the Products page)."""

    product_id: str
    name: str
    category: str
    price: float
    image_url: str
    in_stock: bool


class PageResults(BaseModel):
    """Search results for the website to render as product cards on the Products page."""

    title: str
    query: str
    products: list[ProductCard]


class HistoryMessage(BaseModel):
    """A saved chat message, sent to the website when a logged-in customer comes back."""

    id: int
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    page_results: PageResults | None = None
    created_at: str


class ChatReply(BaseModel):
    reply: str
    products: list[ProductCard] = Field(default_factory=list, description="Cards shown inside the chat")
    page_results: PageResults | None = Field(default=None, description="Cards shown on the Products page")


CurrentPage.model_rebuild()


@dataclass
class ChatDeps:
    """Per-message context the agent and its tools can read (PydanticAI deps). Built by main.py."""

    customer: CustomerProfile | None = None  # None = guest
    page: CurrentPage | None = None


# ---------- Audit trail (output/audit_trail.json) ----------


class AuditToolCall(BaseModel):
    """One tool the agent called during a run: what it asked for and a short summary of what came back."""

    tool_name: str
    args: dict
    result_summary: str = Field(description='e.g. "SearchResults: 11 matches" or "StockReport: M=20 (in_stock)"')


AuditStatus = Literal["success", "content_filtered", "rate_limited", "error"]


class AuditEntry(BaseModel):
    """One agent-loop run (one chat message). Stores hashes instead of message text, so guest chats stay unsaved."""

    run_id: str
    started_at: str
    finished_at: str
    duration_s: float
    status: AuditStatus
    error: str | None = None
    # Who and where (no names or emails)
    customer: Literal["member", "guest"]
    user_id: int | None = None
    page_type: str | None = None
    page_product_id: str | None = None
    # What was asked (hash and length only, never the text)
    message_sha256: str
    message_chars: int
    history_turns: int = Field(description="Earlier messages sent to the model for context")
    # What the agent did
    tool_calls: list[AuditToolCall] = Field(default_factory=list)
    model_configured: str
    model_served: str | None = None
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    system_prompt_sha256: str = Field(description="Which version of prompts/prompt.md (instructions + safety rules) was used")
    # What came back
    reply_sha256: str | None = None
    reply_chars: int | None = None
    chat_card_ids: list[str] = Field(default_factory=list)
    page_results_title: str | None = None
    page_results_count: int = 0
    # Safety events, e.g. "redacted: card number", "content_filter_block", "dropped 2 unsearched page ids"
    safety_events: list[str] = Field(default_factory=list)
    # Hash chain: any edit, deletion or reordering is detectable (audit.verify_audit_trail)
    previous_entry_hash: str | None = None
    entry_hash: str = ""
