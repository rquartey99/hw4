"""Catalogue helpers and the tools the shop agent can call.

Everything here reads campus_customs.db read-only. main.py reuses the helpers for its product routes,
so the website and the chatbot always see the same data.
"""

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

from pydantic_ai import RunContext

from models import (
    MAX_PAGE_RESULTS,
    CategorySummary,
    ChatDeps,
    CurrentPage,
    CustomerProfile,
    GuestProfile,
    LookupFailed,
    PageContext,
    ProductCard,
    ProductInfo,
    ProductMatch,
    SearchResults,
    SizeStock,
    StockReport,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
IMAGES_DIR = DATA_DIR / "products"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
LOW_STOCK = 5  # 1-5 units counts as "low stock" (the product page uses the same number)
DEFAULT_RESULTS = 12

# How customers say sizes -> the size codes stored in inventory.size.
SIZE_ALIASES = {
    "xs": "XS", "extra small": "XS", "x-small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "double xl": "XXL", "extra extra large": "XXL",
}

# Everyday words customers use -> words that appear in the catalogue.
SYNONYMS = {
    "tee": "t-shirt",
    "tees": "t-shirt",
    "tshirt": "t-shirt",
    "tshirts": "t-shirt",
    "sweater": "sweatshirt",
    "hoody": "hoodie",
    "quarterzip": "quarter-zip",
    "fleeces": "fleece",
    "grey": "gray",
}
STOP_WORDS = {"a", "an", "the", "any", "some", "with", "on", "in", "for", "and", "or", "of", "it", "yale"}
# Parts of hyphenated words that shouldn't match alone ("shorts" must not find "short-sleeve").
DESCRIPTOR_PARTS = {"short", "long", "sleeve", "left", "right", "full", "half"}


# ---------- Shared catalogue helpers ----------


def connect() -> sqlite3.Connection:
    """Open the shop database read-only."""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def category_for(garment_type: str) -> str:
    """Group the catalogue's 22 inconsistent garment_type labels into shop categories."""
    g = garment_type.lower()
    if "quarter-zip" in g:
        return "Quarter-zips"
    if "jacket" in g or "fleece" in g:
        return "Jackets & Fleece"
    if "hood" in g:
        return "Hoodies"
    if "t-shirt" in g:
        return "T-shirts"
    if "crewneck" in g or "mockneck" in g:
        return "Sweatshirts"
    if "long-sleeve" in g:
        return "Long Sleeves"
    return "Other"


# ---------- Display names ----------
# The catalogue's names lost their punctuation ("Benjamin Franklin 1 4 Zip"). These rules restore it for
# display everywhere (website, chat cards, agent) without changing the database.

NAME_OVERRIDES = {
    "Champion Reverse Weave Hoodie 1": "Champion Reverse Weave Hoodie",
    "T Felt Y Heavyweight": "Felt Y Heavyweight T-Shirt",
}
NAME_RULES = [
    (r"\b1 4 Zip\b", "1/4 Zip"),
    (r"\bT Shirt\b", "T-Shirt"),
    (r"\bL S\b", "L/S"),
    (r"\b(\d) (\d)$", r"\1.\2"),  # "Tech L S 2 0" -> "2.0"
    (r"\bVs\b", "vs."),
    (r"\bUa\b", "UA"),
    (r"\bVit\b", "VIT"),
    (r"\bMens\b", "Men's"),
    (r"\bCreqneck\b", "Crewneck"),  # typo in the catalogue
    (r"\bTri Blend\b", "Tri-Blend"),
    (r"\bFull Zip\b", "Full-Zip"),
    (r"\bHype And Vice\b", "Hype & Vice"),
    (r"\bTrack (?:And )?Field\b", "Track & Field"),
    (r"(?<=\w) (Of|And|The) (?=\w)", lambda m: f" {m.group(1).lower()} "),  # "School Of Art" -> "School of Art"
]


def display_name(raw_name: str) -> str:
    """'Benjamin Franklin 1 4 Zip' -> 'Benjamin Franklin 1/4 Zip'."""
    name = NAME_OVERRIDES.get(raw_name, raw_name)
    for pattern, replacement in NAME_RULES:
        name = re.sub(pattern, replacement, name)
    return name


# ---------- Color families (for the Products page filter) ----------

COLOR_FAMILIES = {
    "Navy": ["navy"],
    "Blue": ["blue"],  # checked after Navy, so "navy blue" counts as Navy
    "Gray": ["gray", "grey", "charcoal"],
    "White": ["white", "cream", "ivory"],
    "Black": ["black"],
    "Red": ["red", "coral"],
    "Yellow & Gold": ["yellow", "gold"],
    "Green": ["green"],
    "Multicolor": ["multicolor"],
}


def color_families(colors: list[str]) -> list[str]:
    """['navy blue', 'heather gray'] -> ['Navy', 'Gray'] (in COLOR_FAMILIES order)."""
    found: set[str] = set()
    for color in colors:
        c = color.lower()
        for family, words in COLOR_FAMILIES.items():
            if any(w in c for w in words):
                found.add(family)
                break
    return [f for f in COLOR_FAMILIES if f in found]


def image_url(image_file_path: str) -> str:
    # image_file_path looks like "products/<file>.jpg"; main.py mounts that folder at /images.
    return f"/images/{Path(image_file_path).name}"


def sort_sizes(sizes: list[dict]) -> list[dict]:
    return sorted(sizes, key=lambda s: SIZE_ORDER.index(s["size"]) if s["size"] in SIZE_ORDER else len(SIZE_ORDER))


def _load_catalogue() -> list[dict]:
    """Every product with its stock by size (102 rows, so reading them all is quick)."""
    with closing(connect()) as conn:
        products = [dict(r) for r in conn.execute("SELECT * FROM catalogue")]
        stock: dict[str, list[dict]] = {}
        for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(r["product_id"], []).append({"size": r["size"], "quantity": r["quantity"]})
    for p in products:
        p["raw_name"] = p["name"]
        p["name"] = display_name(p["name"])
        p["colors"] = json.loads(p["colors"])
        p["search_tags"] = json.loads(p["search_tags"])
        p["category"] = category_for(p["garment_type"])
        p["stock"] = sort_sizes(stock.get(p["product_id"], []))
    return products


def _to_match(p: dict) -> ProductMatch:
    return ProductMatch(
        product_id=p["product_id"],
        name=p["name"],
        category=p["category"],
        garment_type=p["garment_type"],
        price=p["price"],
        colors=p["colors"],
        sizes_in_stock=[s["size"] for s in p["stock"] if s["quantity"] > 0],
    )


def _normalize(word: str) -> str:
    word = SYNONYMS.get(word, word)
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _tokens(text: str) -> list[str]:
    # Treat "short sleeve" / "long sleeve" as one word, whether written with a space or a hyphen.
    text = re.sub(r"\b(short|long) sleeve", r"\1-sleeve", text.lower())
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text)


def _words(text: str) -> set[str]:
    """Normalized words in a product's text; hyphenated words count whole and by their meaningful parts."""
    out: set[str] = set()
    for token in _tokens(text):
        out.add(_normalize(token))
        if "-" in token:
            out.update(_normalize(part) for part in token.split("-") if part not in DESCRIPTOR_PARTS)
    return out


# ---------- Agent tools ----------


def search_products(
    query: str = "",
    category: str | None = None,
    max_price: float | None = None,
    size: str | None = None,
    limit: int = DEFAULT_RESULTS,
) -> SearchResults:
    """Search the Campus Customs catalogue.

    Args:
        query: Keywords to match against product names, descriptions, colors and tags, e.g. "navy hoodie",
            "bulldog", "field hockey", "mom". Leave empty to browse by the other filters only.
        category: Optional exact category: Hoodies, Sweatshirts, T-shirts, Quarter-zips, Jackets & Fleece,
            or Long Sleeves.
        max_price: Optional highest price in dollars.
        size: Optional size (XS, S, M, L, XL, XXL, or words like "medium"); keeps only products with that
            size in stock.
        limit: Most results to return (default 12, max 30). Use 30 when the customer is browsing a whole
            type of item (e.g. "show me your hoodies") so the Products page can show every match.

    Returns the best matches, cheapest first. total_matches == 0 means the shop doesn't carry anything
    matching (the search itself worked).
    """
    words = [_normalize(w) for w in _tokens(query) if w not in STOP_WORDS]
    size = (normalize_size(size) or size.upper().strip()) if size else None
    scored: list[tuple[int, dict]] = []

    for p in _load_catalogue():
        if category and p["category"].lower() != category.lower():
            continue
        if max_price is not None and p["price"] > max_price:
            continue
        if size and not any(s["size"] == size and s["quantity"] > 0 for s in p["stock"]):
            continue
        product_words = _words(" ".join([p["name"], p["raw_name"], p["garment_type"], p["category"], p["description"], *p["colors"], *p["search_tags"]]))
        score = sum(1 for w in words if w in product_words)
        if words and score == 0:
            continue
        scored.append((score, p))

    if not scored:
        return SearchResults(
            total_matches=0,
            matches=[],
            note="The search worked and found no matching products: the shop doesn't carry this. Say so honestly.",
        )
    # Keep only the products that match the most keywords, so "navy hoodie" beats "any hoodie".
    best = max(score for score, _ in scored)
    top = sorted((p for score, p in scored if score == best), key=lambda p: (p["price"], p["name"]))
    shown = top[: max(1, min(limit, MAX_PAGE_RESULTS))]
    note = f"Showing {len(shown)} of {len(top)} matches, cheapest first."
    if len(shown) < len(top):
        note += " Search again with a higher limit (max 30) or more filters to see the rest."
    return SearchResults(total_matches=len(top), matches=[_to_match(p) for p in shown], note=note)


def _stock_status(quantity: int) -> str:
    if quantity == 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK else "in_stock"


def normalize_size(size: str) -> str | None:
    """'medium', 'M', 'm ' -> 'M'; returns None for sizes the shop doesn't use."""
    return SIZE_ALIASES.get(" ".join(size.lower().replace(".", "").split()))


def _find_product(conn: sqlite3.Connection, product: str) -> sqlite3.Row | None:
    """Look up one catalogue row by product_id (primary key), falling back to an exact name match."""
    key = product.strip()
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (key,)).fetchone()
    if row is None:
        row = conn.execute("SELECT * FROM catalogue WHERE name = ? COLLATE NOCASE", (key,)).fetchone()
    if row is None:
        # The agent and customers see display names ("Benjamin Franklin 1/4 Zip"); match those too.
        for candidate in conn.execute("SELECT * FROM catalogue"):
            if display_name(candidate["name"]).lower() == key.lower():
                return candidate
    return row


def _not_found(product: str) -> LookupFailed:
    similar = search_products(product.replace("-", " "), limit=3).matches
    return LookupFailed(
        reason="product_not_found",
        message=f"No product matches '{product}'. Don't guess: use search_products or ask the customer.",
        suggestions=[f"{m.product_id}: {m.name}" for m in similar],
    )


def get_product_info(product: str) -> ProductInfo | LookupFailed:
    """Look up one product's description, colors and price in the database.

    Call this for any question about a specific product's price or what it looks like.

    Args:
        product: The product_id from search_products (preferred, e.g. "basic-hoodie-big-yale"),
            or the product's exact name (e.g. "Basic Hoodie Big Yale").
    """
    with closing(connect()) as conn:
        row = _find_product(conn, product)
    if row is None:
        return _not_found(product)
    return ProductInfo(
        product_id=row["product_id"],
        name=display_name(row["name"]),
        category=category_for(row["garment_type"]),
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
    )


def check_stock(product: str, size: str | None = None) -> StockReport | LookupFailed:
    """Look up how many units of one product are in stock right now, by size.

    Call this for any question about availability or quantity, even if stock was mentioned earlier.

    Args:
        product: The product_id from search_products (preferred), or the product's exact name.
        size: Optional size the customer asked about: XS, S, M, L, XL or XXL (words like "medium" work too).
    """
    size_code = None
    if size:
        size_code = normalize_size(size)
        if size_code is None:
            return LookupFailed(
                reason="unknown_size",
                message=f"'{size}' isn't a size the shop stocks.",
                suggestions=SIZE_ORDER,
            )

    with closing(connect()) as conn:
        row = _find_product(conn, product)
        if row is None:
            return _not_found(product)
        # inventory has one row per (product_id, size); UNIQUE(product_id, size) makes this an index lookup.
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (row["product_id"],)
        ).fetchall()

    sizes = [
        SizeStock(size=s["size"], quantity=s["quantity"], status=_stock_status(s["quantity"]))
        for s in sort_sizes([dict(s) for s in stock])
    ]
    requested = next((s for s in sizes if s.size == size_code), None) if size_code else None
    if size_code and requested is None:
        # The size is valid but this product has no inventory row for it: treat as not stocked.
        requested = SizeStock(size=size_code, quantity=0, status="sold_out")
    return StockReport(
        product_id=row["product_id"],
        name=display_name(row["name"]),
        requested_size=requested,
        sizes=sizes,
        sizes_available=[s.size for s in sizes if s.quantity > 0],
        total_in_stock=sum(s.quantity for s in sizes),
    )


def list_categories() -> list[CategorySummary]:
    """List the shop's product categories with how many products each has and their price range."""
    groups: dict[str, list[float]] = {}
    for p in _load_catalogue():
        groups.setdefault(p["category"], []).append(p["price"])
    return [
        CategorySummary(category=c, product_count=len(prices), min_price=min(prices), max_price=max(prices))
        for c, prices in sorted(groups.items())
    ]


def get_customer_profile(ctx: RunContext[ChatDeps]) -> CustomerProfile | GuestProfile:
    """Who you're chatting with: the logged-in customer's name, email and account details, or a guest note.

    Call this when the customer asks about their account ("what email is my account under?") or when
    you need their details. Their first name is also in your instructions.
    """
    return ctx.deps.customer or GuestProfile()


def get_current_page(ctx: RunContext[ChatDeps]) -> CurrentPage:
    """What the customer is looking at on the website right now, including the product on screen.

    Call this when they say "this", "that", "it" or "this one" and it isn't clear from the conversation,
    or when they ask about "the page".
    """
    return ctx.deps.page or CurrentPage(path="unknown", page_type="other", note="The website didn't say which page is open.")


AGENT_TOOLS = [
    search_products,
    get_product_info,
    check_stock,
    list_categories,
    get_customer_profile,
    get_current_page,
]


# ---------- Page context (website -> agent deps) ----------


def describe_page(page: PageContext) -> CurrentPage:
    """Turn the page the website reports into agent context, checking any product_id against the database."""
    product = None
    if page.page_type == "product" and page.product_id:
        info = get_product_info(page.product_id)
        product = info if isinstance(info, ProductInfo) else None

    if product:
        note = (
            f"The customer is on the product page for {product.name} ({product.product_id}). "
            "If they say 'this', 'that', 'it' or 'this one' without naming another product, they mean this one."
        )
    elif page.page_type == "product":
        note = "The customer is on a product page, but that product wasn't found."
    elif page.page_type == "chat_results" and page.results_title:
        note = f"The customer is looking at your search results on the Products page: \"{page.results_title}\"."
    else:
        note = f"The customer is on the {page.page_type.replace('_', ' ')} page."
    return CurrentPage(
        path=page.path,
        page_type=page.page_type,
        product=product,
        results_title=page.results_title if page.page_type == "chat_results" else None,
        note=note,
    )


# ---------- Related products (product page) ----------

RELATED_STOP_WORDS = STOP_WORDS | {"college", "university", "left", "chest", "logo", "t-shirt", "t", "shirt", "crewneck",
                                   "hoodie", "hood", "zip", "1", "4", "crew", "sweater", "school"}

# Collections a product belongs to, based on words in its name.
COLLECTIONS = {
    "family": {"mom", "dad", "aunt", "uncle", "grandma", "grandpa", "brother", "sister", "cousin"},
    "residential-college": {"franklin", "berkeley", "branford", "davenport", "hopper", "edwards", "morse", "pierson",
                            "saybrook", "silliman", "dwight", "trumbull", "stiles"},
    "graduate-school": {"architecture", "art", "engineering", "management", "medicine", "music", "nursing", "health",
                        "law", "divinity", "forest"},
    "sports": {"baseball", "basketball", "football", "soccer", "tennis", "hockey", "golf", "volleyball", "diving",
               "swimming", "squash", "fencing", "sailing", "lacrosse", "track", "field", "crew"},
}


def related_products(product_id: str, limit: int = 4) -> list[dict]:
    """Products similar to this one: same category first, then shared collection/theme, colors and garment type.

    Returns catalogue dicts (with display names), best match first. Sold-out items only fill empty slots.
    """
    catalogue = _load_catalogue()
    target = next((p for p in catalogue if p["product_id"] == product_id), None)
    if target is None:
        return []

    def theme_words(p: dict) -> set[str]:
        # Distinctive words from the name ("bulldog", "baseball", "mom", "berkeley") plus its collections.
        words = {w for w in _words(p["raw_name"]) if w not in RELATED_STOP_WORDS}
        return words | {name for name, members in COLLECTIONS.items() if words & members}

    target_themes = theme_words(target)
    target_colors = set(color_families(target["colors"]))

    def score(p: dict) -> float:
        in_stock = any(s["quantity"] > 0 for s in p["stock"])
        return (
            (10 if p["category"] == target["category"] else 0)
            + (3 if p["garment_type"].lower() == target["garment_type"].lower() else 0)
            + 2 * len(target_themes & theme_words(p))
            + len(target_colors & set(color_families(p["colors"])))
            + (5 if in_stock else 0)
        )

    others = [p for p in catalogue if p["product_id"] != product_id]
    return sorted(others, key=lambda p: (-score(p), p["price"], p["name"]))[:limit]


# ---------- Product cards for chat replies ----------


def product_cards(product_ids: list[str]) -> list[ProductCard]:
    """Build cards for the given ids, in order, skipping duplicates and ids that don't exist."""
    by_id = {p["product_id"]: p for p in _load_catalogue()}
    cards: list[ProductCard] = []
    for pid in dict.fromkeys(product_ids):
        p = by_id.get(pid)
        if p:
            cards.append(
                ProductCard(
                    product_id=pid,
                    name=p["name"],
                    category=p["category"],
                    price=p["price"],
                    image_url=image_url(p["image_file_path"]),
                    in_stock=any(s["quantity"] > 0 for s in p["stock"]),
                )
            )
    return cards
