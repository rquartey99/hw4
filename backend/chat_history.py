"""Saved chat history for logged-in customers, stored in campus_customs.db's chat_messages table.

One row per message: (id, user_id, role, content, products_json, page_results_json, created_at).
Guests' chats are never saved. user_id always comes from the session cookie, never from the browser.
"""

import json
import sqlite3
from contextlib import closing

import auth
from models import MAX_TURN_CHARS, ChatReply, ChatTurn, HistoryMessage, PageResults
from tools import product_cards

MAX_LOADED_MESSAGES = 50  # shown in the chat widget when a customer returns


def init_chat_history() -> None:
    """Add what this app needs to the existing chat_messages table (safe to run on every startup)."""
    with closing(auth.connect_rw()) as conn, conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(chat_messages)")}
        if "page_results_json" not in columns:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN page_results_json TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)")


def save_exchange(user_id: int, message: str, reply: ChatReply) -> None:
    """Store the customer's message and the assistant's reply as two rows, in one transaction."""
    products_json = json.dumps([card.model_dump() for card in reply.products])
    page_json = reply.page_results.model_dump_json() if reply.page_results else None
    with closing(auth.connect_rw()) as conn, conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
            (user_id, message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json, page_results_json) "
            "VALUES (?, 'assistant', ?, ?, ?)",
            (user_id, reply.reply, products_json, page_json),
        )


def _recent_rows(conn: sqlite3.Connection, user_id: int, limit: int) -> list[sqlite3.Row]:
    rows = conn.execute(
        "SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit)
    ).fetchall()
    return list(reversed(rows))  # oldest first


def _product_ids(products_json: str | None) -> list[str]:
    """Works for both our card format and the older rows, which stored full product objects."""
    try:
        items = json.loads(products_json) if products_json else []
    except json.JSONDecodeError:
        return []
    return [item["product_id"] for item in items if isinstance(item, dict) and "product_id" in item]


def load_history(user_id: int, limit: int = MAX_LOADED_MESSAGES) -> list[HistoryMessage]:
    """The customer's most recent messages, oldest first, with product cards rebuilt from the database."""
    with closing(auth.connect_rw()) as conn:
        rows = _recent_rows(conn, user_id, limit)
    history: list[HistoryMessage] = []
    for row in rows:
        page_results = None
        if row["page_results_json"]:
            saved = PageResults.model_validate_json(row["page_results_json"])
            # Rebuild cards so reloaded results show today's prices and stock.
            cards = product_cards([c.product_id for c in saved.products])
            page_results = PageResults(title=saved.title, query=saved.query, products=cards) if cards else None
        history.append(
            HistoryMessage(
                id=row["id"],
                role=row["role"],
                content=row["content"],
                products=product_cards(_product_ids(row["products_json"]))[:6],
                page_results=page_results,
                created_at=row["created_at"],
            )
        )
    return history


def recent_turns(user_id: int, limit: int) -> list[ChatTurn]:
    """The last few saved messages as plain turns, for the agent's context."""
    with closing(auth.connect_rw()) as conn:
        rows = _recent_rows(conn, user_id, limit)
    return [
        ChatTurn(role=r["role"], content=r["content"][:MAX_TURN_CHARS])
        for r in rows
        if r["role"] in ("user", "assistant")
    ]


def clear_history(user_id: int) -> int:
    """Delete all of this customer's saved chat messages. Returns how many were removed."""
    with closing(auth.connect_rw()) as conn, conn:
        return conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,)).rowcount
