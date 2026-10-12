"""Extra protection for customer information.

- redact_sensitive(): removes card numbers, card security codes, Social Security numbers and typed passwords from
  chat text before it reaches the AI model or the database.
- RateLimiter: caps how many chat messages one customer (or IP address) can send in a time window.
- add_security_middleware(): security headers on every response, no caching of personal data, and an Origin
  check that stops other websites from sending requests with a customer's login cookie.
"""

import re
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# ---------- Sensitive-data redaction ----------

CARD_CANDIDATE = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
SECURITY_CODE = re.compile(r"(?i)\b(cvv2?|cvc|security code)\b\s*(?:is|:|=|#)?\s*\d{3,4}\b")
PASSWORD = re.compile(r"(?i)\b(password|passcode|passwd|pwd)\b\s*(?:is|:|=)\s*\S+")


def _luhn_ok(digits: str) -> bool:
    """The checksum every real card number passes; avoids redacting order numbers or phone numbers."""
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    return total % 10 == 0


def redact_sensitive(text: str) -> tuple[str, list[str]]:
    """Return (text with sensitive details replaced, kinds of details found)."""
    found: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            found.append("card number")
            return "[card number removed]"
        return m.group(0)

    text = CARD_CANDIDATE.sub(card, text)
    text, n = SECURITY_CODE.subn(lambda m: f"{m.group(1)} [removed]", text)
    found += ["card security code"] * bool(n)
    text, n = SSN.subn("[SSN removed]", text)
    found += ["Social Security number"] * bool(n)
    text, n = PASSWORD.subn(lambda m: f"{m.group(1)} [removed]", text)
    found += ["password"] * bool(n)
    return text, found


# ---------- Rate limiting ----------


class RateLimiter:
    """Sliding-window limit: at most `limit` events per `window` seconds for each key (kept in memory)."""

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        events = self._events[key]
        while events and events[0] <= now - self.window:
            events.popleft()
        if len(events) >= self.limit:
            return False
        events.append(now)
        return True


# 20 chat messages per 5 minutes per customer (or per IP address for guests): plenty for shopping,
# but it stops scripts from flooding the assistant (and running up AI costs).
chat_limiter = RateLimiter(limit=20, window=5 * 60)


# ---------- Headers and Origin check ----------

ALLOWED_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"}
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PRIVATE_PATHS = ("/api/auth", "/api/chat")  # responses with personal data

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",  # browsers must trust our content types
    "X-Frame-Options": "DENY",  # the site can't be embedded in another site (clickjacking)
    "Referrer-Policy": "same-origin",  # page URLs aren't leaked to other sites
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def add_security_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def security(request: Request, call_next):
        # Requests that change data must come from our own site. Browsers always send Origin on cross-site
        # POST/DELETE, so a hostile page can't use a customer's login cookie (defense on top of SameSite=Lax).
        origin = request.headers.get("origin")
        if request.method in UNSAFE_METHODS and origin and origin not in ALLOWED_ORIGINS:
            return JSONResponse({"detail": "Request blocked: unexpected origin."}, status_code=403)

        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith(PRIVATE_PATHS):
            response.headers["Cache-Control"] = "no-store"  # don't keep account or chat data in caches
        return response
