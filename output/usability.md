# Usability Improvements — Problem 9

Each change requested for Problem 9, what was built, and why it helps the **customer**, the **business**, or both.

---

## Frontend changes

### 1. Related products ("You might also like")
**What changed**
- Every product page now ends with four similar products.
- They come from a new `GET /api/products/{id}/related` route (`related_products()` in `backend/tools.py`), which scores other products by:
  - **same category first**, so a T-shirt shows T-shirts
  - then a shared **theme or collection** from the name: the same sport, residential college, graduate school, family member ("Mom", "Dad"…) or design ("Bulldog")
  - then the same garment type and colors
- In-stock items rank above sold-out ones. Clicking a related product opens it at the top of the page.

**Examples**

| Product | Related products shown |
|---|---|
| Benjamin Franklin T-Shirt | Grace Hopper, Morse, Pierson and Saybrook Logo T-Shirts (other residential-college tees) |
| Yale Mom Hoodie | Yale Dad, Grandma and Grandpa Hoodies, Basic Hoodie Big Yale |
| Tri-Blend Sports Baseball T-Shirt | Other Tri-Blend Sports tees (basketball, football, hockey, soccer) |
| School of Art Fleece Sweater | Divinity, Architecture and Music Fleece Sweaters |

**Why it helps**
- **Customer:** if an item is sold out in their size or isn't quite right, similar options are one click away, with no new search needed. Family and college groupings also make gift shopping easier (e.g. matching "Mom" and "Dad" pieces).
- **Business:** more product views per visit and more chances to sell, including add-on sales ("they bought the Mom hoodie, show the Dad hoodie"). It also keeps shoppers on the site instead of leaving when one item doesn't work.

### 2. Fixed product titles
**What changed**
- The catalogue's names had lost their punctuation. A new `display_name()` function in `backend/tools.py` restores it everywhere a name appears: the Products page, product pages, related products, chat cards, and the names the AI agent sees.
- The database itself is unchanged. Customers and the agent can look products up by either the old or the fixed name.
- **52 of 102 names** were fixed. For example:

| Before (database) | After (shown) |
|---|---|
| Benjamin Franklin 1 4 Zip | Benjamin Franklin 1/4 Zip |
| 2025 Yale Vs Harvard T Shirt | 2025 Yale vs. Harvard T-Shirt |
| Ua Mens Tech L S 2 0 | UA Men's Tech L/S 2.0 |
| Hype And Vice Yale University Premium Crewneck | Hype & Vice Yale University Premium Crewneck |
| School Of Public Health 1 4 Zip | School of Public Health 1/4 Zip |
| Tri Blend Sports Track And Field T Shirt | Tri-Blend Sports Track & Field T-Shirt |
| Yale Sports Creqneck Field Hockey | Yale Sports Crewneck Field Hockey (typo fixed) |
| Champion Reverse Weave Hoodie 1 | Champion Reverse Weave Hoodie |

**Why it helps**
- **Customer:** names are easier to read and understand ("1/4 Zip" is a garment; "1 4 Zip" looks like a mistake), and a name matches what they'd search for or say to the chatbot.
- **Business:** clean names look professional and build trust; typos and broken titles make a store look careless and hurt sales. Doing it in one function means the website and the chatbot always use the same name.

### 3. Filters on the Products page
**What changed** — a filter sidebar (`frontend/src/components/ProductFilters.tsx`, logic in `frontend/src/filters.ts`) with:

| Filter | Options |
|---|---|
| Category | All, Hoodies, Sweatshirts, T-shirts, Quarter-zips, Jackets & Fleece, Long Sleeves |
| **Size in stock** | XS–XXL (only products with that size **in stock**, from the inventory table) |
| **Color** | Navy, Blue, Gray, White, Black, Red, Yellow & Gold, Green, Multicolor, with color swatches. The catalogue's 22 color spellings ("heather gray", "charcoal gray", "navy blue"…) are grouped into these families. |
| **Price** | Under $40, $40–$60, $60–$80, $80 and up |
| Availability | Hide sold-out items |
| Sort | Name, price low→high, price high→low |

**How it works for the shopper**
- **Combining filters:** several options in one filter widen the results (Navy *or* Gray). Different filters narrow them (XS *and* Gray *and* under $40).
- **Chips:** each active filter shows as a removable chip above the results, with a live count ("14 of 102 items") and **Clear all**.
- **Filters live in the URL** (e.g. `/products?size=XS&color=Gray&price=under-40`): opening a product and pressing Back returns to the same filtered list, refreshing keeps it, and a filtered view can be shared as a link.
- **Small screens:** the filters fold behind a "Filters" button.

**Why it helps**
- **Customer:** finds what fits their size, color and budget quickly instead of scrolling through 102 products. Filtering by *size in stock* stops them falling for an item that's sold out in their size.
- **Business:** shoppers who find something quickly are more likely to buy, and fewer leave frustrated. The in-stock size filter also cuts disappointed "is this available?" questions.

---

## Backend changes

### 4. Model check on every chat, using the cheapest approved model
**What we found:** `gpt-6-astra`, the project default, is the **most expensive** model available on the Portkey key.

| Model | Input $ / 1M tokens | Output $ / 1M tokens |
|---|---|---|
| gpt-6-astra (old) | $20.00 | $75.00 |
| **gpt-5.6-luna (now)** | **$0.40** | **$1.80** |
| gpt-5-nano (cheapest overall) | $0.05 | $0.40 |

**What changed**
- **The chatbot now uses `gpt-5.6-luna`.** You chose it as the cheapest model that reliably handles the chatbot's tools and structured replies. `gpt-5-nano` is cheaper, but it's a much smaller model. This applies to Homework 4 only; AGENTS.md still says `gpt-6-astra` for the rest of the project.
- **Startup check** (`backend/model_usage.py`): the backend logs the configured model's price and confirms it's the cheapest *approved* model. It warns if a cheaper approved model exists, and notes the cheapest model overall. `GET /api/health` also reports the chat model.
- **Every chat is checked:**
  - the backend reads the model name the gateway reports on each response (e.g. `gpt-5.6-luna-global`)
  - it adds up model calls and tokens, and prices the chat with the `genai-prices` data
  - it logs a line like `Chat model=gpt-5.6-luna-global requests=2 tokens=7657 in/259 out cost=$0.00184`
  - it logs a **warning** if any response came from a different model than configured, e.g. a gateway fallback to a pricier model
- **Records:** the numbers (model, match yes/no, calls, tokens, cost) are saved to a new `chat_usage` table, **with no message text**.
- **Quality check:** after the switch, every earlier chatbot test was rerun on luna and passed: price, stock by size, sold-out sizes, XXXL, "what material?", follow-ups, results on the page, and "gym shorts".

**Why it helps**
- **Business:**
  - a typical chat now costs about **$0.002 instead of about $0.17**, roughly **90× cheaper**, with the same answers in testing
  - at 1,000 chats a day, that's about $2 a day instead of about $170
  - the per-chat check catches silent model swaps or cost spikes early
  - `chat_usage` gives a running record of AI spending
- **Customer:** no visible change in quality. Luna also tends to answer faster than the larger astra model.

### 5. More protection for customer information
**What changed** (`backend/security.py`, wired into `backend/main.py`):

| Protection | What it does |
|---|---|
| **Sensitive details removed from chats** | Card numbers (checked with the standard card checksum, so order and phone numbers aren't affected), card security codes, Social Security numbers and "my password is …" are replaced with `[card number removed]`, `[SSN removed]`, etc. **before** the message reaches the AI model or is saved. The bot's reply is checked the same way, and the customer gets a note asking them not to share that information. Logs record only *what kind* of detail was removed, never the detail itself. |
| **Chat rate limit** | At most 20 messages per 5 minutes per customer (or per IP address for guests); after that, "please wait a few minutes." |
| **Origin check** | Requests that change data (log in, log out, chat, clear history) are refused (403) if they come from another website. This stops a malicious site from using a shopper's login cookie, on top of the existing SameSite cookie setting. |
| **Security headers on every response** | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (the site can't be hidden inside another site to trick clicks), `Referrer-Policy: same-origin`, `Permissions-Policy` (no camera, mic or location) and `Cross-Origin-Opener-Policy`. |
| **No caching of personal data** | Account and chat responses carry `Cache-Control: no-store`, so a shared or public computer doesn't keep someone's chat or account details. |
| **Agent told about removed details** | The prompt tells the agent never to ask a customer to re-send removed details, and that the site has no online checkout (so it never points people to one). |

These add to what was already in place:
- hashed passwords (PBKDF2, 600k rounds)
- login lockout after 5 failed attempts
- HttpOnly session cookies, stored only as hashes
- chat history tied to the session on the server
- no password hashes ever sent to the browser or the agent

**Tested live:**
- A message with a card number, security code and password was saved as `my card is [card number removed] cvv [removed] and my password [removed]`, and a search found **0** copies of the raw values anywhere in `chat_messages`.
- Requests from `https://evil.example` got 403 (and the chat history wasn't deleted), while the site's own origin worked.
- All the security headers and `no-store` are present.

**Why it helps**
- **Customer:** if someone pastes a card number or password into the chat by mistake, it isn't sent to an outside AI service or stored where it could leak. Their account can't be controlled from another website, and their chat doesn't linger on shared computers.
- **Business:**
  - storing card numbers or SSNs creates legal and compliance risk (e.g. PCI rules for card data) and makes the database a bigger target; not storing them removes that risk
  - the rate limit protects against abuse and runaway AI bills
  - these are standard protections that customers and reviewers expect from any store with accounts

---

## Files changed
- **Frontend:**
  - `pages/Products.tsx` (filter sidebar, chips, sort, results)
  - `components/ProductFilters.tsx` and `filters.ts` (new)
  - `components/RelatedProducts.tsx` (new)
  - `pages/ProductDetail.tsx`
  - `components/ProductCard.tsx`
  - `api.ts`
  - `index.css`
- **Backend:**
  - `tools.py` (display names, color families, related products)
  - `main.py` (new product fields, related route, security, model records)
  - `agent.py` (luna and the per-chat check)
  - `model_usage.py` and `security.py` (new)
  - `prompts/prompt.md`
  - `requirements.txt` (adds `genai-prices`)
