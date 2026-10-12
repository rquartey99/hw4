"""Campus Customs API: products, images, accounts (auth.py), the shop chatbot (agent.py) and saved chats.

Run from this folder:
    uvicorn main:app --reload --port 8000
"""

import json
import logging
import sqlite3
from contextlib import asynccontextmanager, closing

from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles

import time
import uuid
from datetime import datetime, timezone

import agent
import audit
import auth
import chat_history
import model_usage
import security
from models import AuditEntry, ChatDeps, ChatReply, ChatRequest, CustomerProfile, HistoryMessage
from tools import (
    IMAGES_DIR,
    SIZE_ORDER,
    category_for,
    color_families,
    connect,
    describe_page,
    display_name,
    image_url,
    related_products,
    sort_sizes,
)

logger = logging.getLogger("campus_customs")
# Show this app's log lines (model check, cost per chat, security warnings) in the uvicorn terminal.
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     [%(name)s] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    auth.init_sessions_table()
    chat_history.init_chat_history()
    model_usage.init_usage_table()
    model_usage.log_model_choice(agent.MODEL_NAME)
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)
app.include_router(auth.router)
security.add_security_middleware(app)

# Only the product photo folder is exposed, so the .db file can never be downloaded.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def product_summary(row: sqlite3.Row) -> dict:
    colors = json.loads(row["colors"])
    in_stock = set((row["sizes_in_stock"] or "").split(","))
    return {
        "product_id": row["product_id"],
        "name": display_name(row["name"]),
        "garment_type": row["garment_type"],
        "category": category_for(row["garment_type"]),
        "price": row["price"],
        "colors": colors,
        "color_families": color_families(colors),  # for the Products page color filter
        "sizes_in_stock": [s for s in SIZE_ORDER if s in in_stock],  # for the size filter
        "image_url": image_url(row["image_file_path"]),
        "total_stock": row["total_stock"],
    }


# Catalogue rows plus total stock and the sizes that have stock ("XS,M,L").
PRODUCT_SELECT = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
           GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_in_stock
    FROM catalogue c
    LEFT JOIN inventory i ON i.product_id = c.product_id
"""


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "chat_model": agent.MODEL_NAME}


@app.get("/api/products")
def list_products() -> list[dict]:
    with closing(connect()) as conn:
        rows = conn.execute(PRODUCT_SELECT + " GROUP BY c.product_id").fetchall()
    return sorted((product_summary(r) for r in rows), key=lambda p: p["name"].lower())


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with closing(connect()) as conn:
        row = conn.execute(PRODUCT_SELECT + " WHERE c.product_id = ? GROUP BY c.product_id", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    return {
        **product_summary(row),
        "description": row["description"],
        "search_tags": json.loads(row["search_tags"]),
        "sizes": sort_sizes([{"size": s["size"], "quantity": s["quantity"]} for s in stock]),
    }


@app.get("/api/products/{product_id}/related")
def get_related_products(product_id: str, limit: int = 4) -> list[dict]:
    """Similar products for the "You might also like" section of a product page."""
    related = related_products(product_id, limit=max(1, min(limit, 12)))
    if not related:
        raise HTTPException(status_code=404, detail="Product not found")
    ids = [p["product_id"] for p in related]
    with closing(connect()) as conn:
        rows = conn.execute(
            PRODUCT_SELECT + f" WHERE c.product_id IN ({','.join('?' * len(ids))}) GROUP BY c.product_id", ids
        ).fetchall()
    by_id = {r["product_id"]: product_summary(r) for r in rows}
    return [by_id[pid] for pid in ids if pid in by_id]


def current_user(cc_session: str | None) -> sqlite3.Row | None:
    with closing(auth.connect_rw()) as conn:
        return auth.user_for_token(conn, cc_session)


def customer_profile(user: sqlite3.Row) -> CustomerProfile:
    """The customer fields the agent may see: name, email, join date and saved-message count (no password hash)."""
    info = auth.public_user(user)
    with closing(auth.connect_rw()) as conn:
        saved = conn.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (info["id"],)).fetchone()[0]
    return CustomerProfile(
        first_name=info["first_name"],
        last_name=info["last_name"],
        email=info["email"],
        member_since=info["created_at"][:10],
        saved_messages=saved,
    )


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request, cc_session: str | None = Cookie(default=None)) -> ChatReply:
    """Send one customer message to the shop agent, with who they are and which page they're on.

    Every call, whatever happens, appends one entry to output/audit_trail.json (see audit.py).
    """
    started, clock = datetime.now(timezone.utc), time.perf_counter()
    user = current_user(cc_session)
    message, removed = security.redact_sensitive(body.message)  # card numbers etc. never reach the model or logs
    record = {
        "status": "error",
        "error": None,
        "history_turns": 0,
        "outcome": None,
        "safety_events": [f"redacted: {kind}" for kind in removed],
    }
    try:
        client = f"user:{user['id']}" if user else f"ip:{request.client.host if request.client else 'unknown'}"
        if not security.chat_limiter.allow(client):
            record["status"] = "rate_limited"
            raise HTTPException(status_code=429, detail="You're sending messages very quickly. Please wait a few minutes.")

        if user:
            # Logged in: context comes from their saved history in the database, not from the browser.
            history = chat_history.recent_turns(user["id"], agent.MAX_HISTORY_TURNS)
            customer = customer_profile(user)
        else:
            history = [t.model_copy(update={"content": security.redact_sensitive(t.content)[0]}) for t in body.history]
            customer = None
        record["history_turns"] = len(history[-agent.MAX_HISTORY_TURNS :])
        deps = ChatDeps(customer=customer, page=describe_page(body.page) if body.page else None)

        try:
            outcome = await agent.run_chat(message, history, deps)
        except agent.AgentUnavailable as e:
            logger.error("Chat agent unavailable: %s", e)
            record["error"] = "AgentUnavailable"
            raise HTTPException(status_code=503, detail="The shop assistant isn't set up yet. Please try again later.")
        except Exception as e:
            logger.exception("Chat agent failed")
            record["error"] = type(e).__name__
            raise HTTPException(status_code=502, detail="Sorry, the shop assistant had a problem. Please try again.")
        record["outcome"] = outcome
        record["status"] = "content_filtered" if outcome.content_filtered else "success"

        reply = outcome.reply
        reply.reply = security.redact_sensitive(reply.reply)[0]  # in case the model repeated something sensitive
        if removed:
            # Logged by kind only; the details themselves are never written anywhere.
            logger.warning("Removed %s from a chat message before sending it to the model", ", ".join(removed))
            reply.reply += (
                f"\n\n*For your security I removed a {' and '.join(dict.fromkeys(removed))} from your message. "
                "Please don't share that in chat.*"
            )
        if outcome.usage:
            model_usage.record(outcome.usage, user["id"] if user else None)
        if user:
            chat_history.save_exchange(user["id"], message, reply)
        return reply
    finally:
        _audit_chat(started, clock, user, body, message, record)


def _audit_chat(started: datetime, clock: float, user, body: ChatRequest, message: str, record: dict) -> None:
    """Append this chat's audit entry. An audit failure is logged but never breaks the customer's chat."""
    outcome = record["outcome"]
    usage = outcome.usage if outcome else None
    reply = outcome.reply if outcome else None
    events = list(record["safety_events"])
    if outcome and outcome.content_filtered:
        events.append("content_filter_block")
    if usage and not usage.matches_configured:
        events.append(f"unexpected_model: {usage.served_model}")
    if outcome and outcome.dropped_page_ids:
        events.append(f"dropped {outcome.dropped_page_ids} page id(s) not returned by search")
    try:
        audit.append_audit(
            AuditEntry(
                run_id=str(uuid.uuid4()),
                started_at=started.isoformat().replace("+00:00", "Z"),
                finished_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                duration_s=round(time.perf_counter() - clock, 2),
                status=record["status"],
                error=record["error"],
                customer="member" if user else "guest",
                user_id=user["id"] if user else None,
                page_type=body.page.page_type if body.page else None,
                page_product_id=body.page.product_id if body.page else None,
                message_sha256=audit.sha256(message),
                message_chars=len(message),
                history_turns=record["history_turns"],
                tool_calls=audit.tool_calls(outcome.messages) if outcome else [],
                model_configured=agent.MODEL_NAME,
                model_served=usage.served_model if usage else None,
                requests=usage.requests if usage else 0,
                input_tokens=usage.input_tokens if usage else 0,
                output_tokens=usage.output_tokens if usage else 0,
                cost_usd=usage.cost_usd if usage else None,
                system_prompt_sha256=audit.file_sha256(agent.PROMPT_PATH),
                reply_sha256=audit.sha256(reply.reply) if reply else None,
                reply_chars=len(reply.reply) if reply else None,
                chat_card_ids=[c.product_id for c in reply.products] if reply else [],
                page_results_title=reply.page_results.title if reply and reply.page_results else None,
                page_results_count=len(reply.page_results.products) if reply and reply.page_results else 0,
                safety_events=events,
            )
        )
    except Exception:
        logger.exception("Could not write the audit trail entry")


@app.get("/api/chat/history")
def get_chat_history(cc_session: str | None = Cookie(default=None)) -> list[HistoryMessage]:
    """The logged-in customer's saved chat (most recent 50 messages). Guests get an empty list."""
    user = current_user(cc_session)
    return chat_history.load_history(user["id"]) if user else []


@app.delete("/api/chat/history", status_code=204)
def delete_chat_history(cc_session: str | None = Cookie(default=None)) -> None:
    """Let a logged-in customer clear their saved chat."""
    user = current_user(cc_session)
    if user is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    chat_history.clear_history(user["id"])
