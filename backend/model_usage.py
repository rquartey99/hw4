"""Model check: which model answered each chat, what it cost, and whether it's the cheapest approved model.

- At startup, log_model_choice() compares the configured model's price with every model the chatbot is approved
  to use (and with the cheapest model overall), and warns if a cheaper approved model exists.
- After every chat, gauge() reads the model name the gateway reports back on each response, adds up tokens and
  cost, and flags any response that came from a different model than configured (e.g. a gateway fallback to a
  pricier one). record() saves those numbers to the chat_usage table. No message text is stored.
"""

import logging
from contextlib import closing
from dataclasses import dataclass

from genai_prices import Usage, calc_price
from pydantic_ai.messages import ModelResponse

import auth

logger = logging.getLogger("campus_customs.model")

# Models this chatbot may use: they handle its tools and structured replies reliably.
APPROVED_MODELS = ["gpt-5.6-luna", "gpt-6-astra"]
# Everything the project's Portkey key can use, for the "cheapest overall" comparison.
AVAILABLE_MODELS = [
    "gpt-5-nano", "gpt-5.4-nano", "gpt-5-mini", "gpt-5.6-luna", "gpt-5.4-mini", "gpt-5.1", "gpt-5.2",
    "gpt-5.6-terra", "gpt-5.4", "gpt-5.6-sol", "gpt-5.5", "gpt-6-astra",
]


def price_per_million(model: str) -> tuple[float, float] | None:
    """(input $, output $) per million tokens, or None if the pricing data doesn't know the model."""
    try:
        p = calc_price(Usage(input_tokens=1_000_000, output_tokens=1_000_000), model_ref=model, provider_id="openai")
    except Exception:
        return None
    return float(p.input_price), float(p.output_price)


def _blended(model: str) -> float:
    """One number for comparing models: cost of a typical chat mix (about 10 input tokens per output token)."""
    price = price_per_million(model)
    return price[0] * 10 + price[1] if price else float("inf")


def cheapest(models: list[str]) -> str:
    return min(models, key=_blended)


def log_model_choice(configured: str) -> None:
    """Startup check: is the configured model the cheapest approved one?"""
    price = price_per_million(configured)
    best_approved, best_overall = cheapest(APPROVED_MODELS), cheapest(AVAILABLE_MODELS)
    priced = f"${price[0]:.2f} in / ${price[1]:.2f} out per 1M tokens" if price else "price unknown"
    if configured == best_approved:
        logger.info("Chat model: %s (%s) - cheapest approved model", configured, priced)
    else:
        logger.warning("Chat model: %s (%s) - cheaper approved model available: %s", configured, priced, best_approved)
    if best_overall != best_approved:
        logger.info("Cheapest model overall is %s, not approved for this chatbot (quality)", best_overall)


@dataclass
class ChatUsage:
    configured_model: str
    served_model: str  # what the gateway says actually answered, e.g. "gpt-5.6-luna-2026-07-09"
    matches_configured: bool
    requests: int
    input_tokens: int
    output_tokens: int
    cost_usd: float | None


def gauge(configured: str, messages: list, input_tokens: int, output_tokens: int, requests: int) -> ChatUsage:
    """Check which model answered this chat and what it cost."""
    served = [m.model_name for m in messages if isinstance(m, ModelResponse) and m.model_name]
    unexpected = sorted({name for name in served if not name.startswith(configured)})
    served_model = unexpected[0] if unexpected else (served[-1] if served else "unknown")
    try:
        cost = float(
            calc_price(Usage(input_tokens=input_tokens, output_tokens=output_tokens), model_ref=configured, provider_id="openai").total_price
        )
    except Exception:
        cost = None
    usage = ChatUsage(configured, served_model, not unexpected, requests, input_tokens, output_tokens, cost)

    cost_text = f"${cost:.5f}" if cost is not None else "unknown"
    if unexpected:
        logger.warning("Chat answered by %s, expected %s (cost %s)", ", ".join(unexpected), configured, cost_text)
    else:
        logger.info(
            "Chat model=%s requests=%d tokens=%d in/%d out cost=%s",
            served_model, requests, input_tokens, output_tokens, cost_text,
        )
    return usage


def init_usage_table() -> None:
    with closing(auth.connect_rw()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                user_id INTEGER,
                configured_model TEXT NOT NULL,
                served_model TEXT NOT NULL,
                matches_configured INTEGER NOT NULL,
                requests INTEGER NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd REAL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """
        )


def record(usage: ChatUsage, user_id: int | None) -> None:
    """Save one chat's model and cost numbers (never the message text)."""
    with closing(auth.connect_rw()) as conn, conn:
        conn.execute(
            "INSERT INTO chat_usage (user_id, configured_model, served_model, matches_configured, requests,"
            " input_tokens, output_tokens, cost_usd) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id, usage.configured_model, usage.served_model, int(usage.matches_configured),
                usage.requests, usage.input_tokens, usage.output_tokens, usage.cost_usd,
            ),
        )
