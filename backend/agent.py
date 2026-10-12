"""Campus Customs shop agent: PydanticAI + gpt-5.6-luna through Portkey.

main.py calls run_chat() for every chat message. The agent itself is built once, on the first message,
with tools from tools.py and structured output from models.py; prompts/prompt.md is re-read on every run.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv  # noqa: E402
from openai import AsyncOpenAI  # noqa: E402
from pydantic_ai import Agent, RunContext  # noqa: E402
from pydantic_ai.exceptions import ModelHTTPError  # noqa: E402
from pydantic_ai.messages import (  # noqa: E402
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.openai import OpenAIResponsesModel  # noqa: E402
from pydantic_ai.providers.openai import OpenAIProvider  # noqa: E402
from pydantic_ai.usage import UsageLimits  # noqa: E402

import model_usage  # noqa: E402
from models import AgentReply, ChatDeps, ChatReply, ChatTurn, PageResults, SearchResults  # noqa: E402
from tools import AGENT_TOOLS, product_cards  # noqa: E402

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")  # hw4/.env (copy .env.example and add your key)

# gpt-5.6-luna: the cheapest approved model (see model_usage.py). The rest of the project uses gpt-6-astra per
# AGENTS.md; the user chose luna for this chatbot because astra costs about 50x more per token.
MODEL_NAME = "gpt-5.6-luna"
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1").rstrip("/")
PROMPT_PATH = HERE / "prompts" / "prompt.md"
MAX_MODEL_REQUESTS = 8  # a few tool calls per message is plenty; stops runaway loops
MAX_HISTORY_TURNS = 12  # earlier messages sent to the model for context
CONTENT_FILTER_REPLY = (
    "Sorry, I can't help with that. I'm here to help you find Campus Customs gear. "
    "Ask me about hoodies, crewnecks, tees, sizes or what's in stock!"
)

logger = logging.getLogger("campus_customs.agent")


class AgentUnavailable(RuntimeError):
    """The agent can't run (e.g. PORTKEY_API_KEY missing)."""


@dataclass
class ChatOutcome:
    reply: ChatReply
    usage: model_usage.ChatUsage | None  # None when the content filter answered instead of the model
    messages: list = field(default_factory=list)  # this run's model messages (tool calls), for the audit trail
    content_filtered: bool = False
    dropped_page_ids: int = 0  # page_results ids dropped because search didn't return them


@lru_cache(maxsize=1)
def get_agent() -> Agent[ChatDeps, AgentReply]:
    """Build the agent once and reuse it for every request."""
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise AgentUnavailable("PORTKEY_API_KEY is not set in the project .env file.")
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-api-key": api_key},
    )
    agent = Agent(
        OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client)),
        deps_type=ChatDeps,
        output_type=AgentReply,
        tools=AGENT_TOOLS,
        retries=2,
    )

    @agent.instructions
    def system_prompt() -> str:
        # Read on every run so edits to prompt.md apply without restarting (uvicorn only reloads .py files).
        return PROMPT_PATH.read_text(encoding="utf-8")

    @agent.instructions
    def chat_context(ctx: RunContext[ChatDeps]) -> str:
        """Who is chatting and what page they're on, added to the instructions for every message."""
        customer = ctx.deps.customer
        if customer:
            who = (
                f"The customer is logged in as {customer.first_name} {customer.last_name} ({customer.email}). "
                "Their chat history is saved, so earlier messages may be from previous visits."
            )
        else:
            who = "The customer is a guest (not logged in). Their chat isn't saved after they leave."
        where = ctx.deps.page.note if ctx.deps.page else "The website didn't say which page is open."
        return f"## Current chat\n- {who}\n- {where}"

    return agent


def _to_message_history(history: list[ChatTurn]) -> list[ModelMessage]:
    """Turn the website's earlier chat turns into PydanticAI messages."""
    messages: list[ModelMessage] = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        if turn.role == "user":
            messages.append(ModelRequest(parts=[UserPromptPart(content=turn.content)]))
        else:
            messages.append(ModelResponse(parts=[TextPart(content=turn.content)]))
    return messages


async def run_chat(message: str, history: list[ChatTurn], deps: ChatDeps) -> ChatOutcome:
    """Answer one customer message: the reply (text plus product cards) and which model answered at what cost."""
    try:
        result = await get_agent().run(
            message,
            message_history=_to_message_history(history),
            deps=deps,
            usage_limits=UsageLimits(request_limit=MAX_MODEL_REQUESTS),
        )
    except ModelHTTPError as e:
        # Azure's content filter (in front of the model on the Portkey route) blocks jailbreak attempts
        # and harmful requests before the model sees them. Answer politely instead of erroring.
        if "content_filter" in str(e.body):
            logger.warning("Chat message blocked by the model provider's content filter")
            return ChatOutcome(ChatReply(reply=CONTENT_FILTER_REPLY), usage=None, content_filtered=True)
        raise
    output: AgentReply = result.output
    run_usage = result.usage  # a property in PydanticAI 2.x
    usage = model_usage.gauge(
        MODEL_NAME, result.new_messages(), run_usage.input_tokens, run_usage.output_tokens, run_usage.requests
    )
    # Cards are built from the database, so a made-up id can never show a fake product.
    searched = _searched_ids(result.new_messages())
    page_results = _page_results(output, searched)
    requested = len(output.page_results.product_ids) if output.page_results else 0
    reply = ChatReply(reply=output.reply, products=product_cards(output.product_ids), page_results=page_results)
    return ChatOutcome(
        reply,
        usage,
        messages=result.new_messages(),
        dropped_page_ids=requested - (len(page_results.products) if page_results else 0),
    )


def _searched_ids(messages: list[ModelMessage]) -> set[str]:
    """product_ids that search_products actually returned during this run."""
    ids: set[str] = set()
    for message in messages:
        for part in message.parts:
            if isinstance(part, ToolReturnPart) and isinstance(part.content, SearchResults):
                ids.update(m.product_id for m in part.content.matches)
    return ids


def _page_results(output: AgentReply, searched_ids: set[str]) -> PageResults | None:
    """Turn the agent's page_results request into product cards for the Products page.

    Only ids that came back from search_products in this run are kept, so the page can only ever show
    real search matches (never ids the model invented or remembered from an earlier message).
    """
    request = output.page_results
    if request is None:
        return None
    cards = product_cards([pid for pid in request.product_ids if pid in searched_ids])
    if not cards:
        return None
    return PageResults(title=request.title, query=request.query, products=cards)
