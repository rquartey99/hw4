"""Append-only audit trail of agent-loop activity: output/audit_trail.json.

Every chat message (success, content-filter block, rate limit or error) appends one AuditEntry. The file is
never wiped: each write reads the existing list, appends, and replaces the file atomically under a file lock,
so separate server processes or a crash can't lose or corrupt entries. Entries are hash-chained, so any edit,
deletion or reordering is detectable with verify_audit_trail(). Same design as Homework 3's audit trail.

Privacy: entries store SHA-256 hashes and lengths of messages and replies, never the text, so guest chats stay
unsaved and no names, emails, or card numbers end up in the log.
"""

import fcntl
import hashlib
import json
import os
from pathlib import Path

from pydantic_ai.messages import ModelMessage, ToolCallPart, ToolReturnPart

from models import AuditEntry, AuditToolCall, LookupFailed, ProductInfo, SearchResults, StockReport

AUDIT_FILE = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------- Tool-call summaries ----------


def _summarize(result: object) -> str:
    """A short, text-free description of what a tool returned."""
    if isinstance(result, SearchResults):
        return f"SearchResults: {result.total_matches} matches, {len(result.matches)} returned"
    if isinstance(result, StockReport):
        if result.requested_size:
            s = result.requested_size
            return f"StockReport: {s.size}={s.quantity} ({s.status}), total {result.total_in_stock}"
        return f"StockReport: total {result.total_in_stock}, sizes {','.join(result.sizes_available) or 'none'}"
    if isinstance(result, ProductInfo):
        return f"ProductInfo: {result.product_id} ${result.price:.2f}"
    if isinstance(result, LookupFailed):
        return f"LookupFailed: {result.reason}"
    if isinstance(result, list):
        return f"{type(result[0]).__name__ if result else 'list'} x{len(result)}"
    # Customer profile / current page: only record the type, never the personal details.
    return type(result).__name__


def tool_calls(messages: list[ModelMessage]) -> list[AuditToolCall]:
    """The tools the agent called in this run, paired with a summary of each result."""
    returns = {
        part.tool_call_id: part.content
        for m in messages
        for part in m.parts
        if isinstance(part, ToolReturnPart)
    }
    calls: list[AuditToolCall] = []
    for m in messages:
        for part in m.parts:
            if isinstance(part, ToolCallPart) and part.tool_name != "final_result":
                result = returns.get(part.tool_call_id)
                calls.append(
                    AuditToolCall(
                        tool_name=part.tool_name,
                        args=part.args_as_dict(),
                        result_summary=_summarize(result) if part.tool_call_id in returns else "no result",
                    )
                )
    return calls


# ---------- Append + verify ----------


def entry_hash(entry: AuditEntry) -> str:
    body = entry.model_dump(mode="json", exclude={"entry_hash"})
    return sha256(json.dumps(body, sort_keys=True, separators=(",", ":")))


def append_audit(entry: AuditEntry, audit_file: Path = AUDIT_FILE) -> AuditEntry:
    """Append one entry under a file lock, chained to the previous entry's hash. Never truncates the trail.

    If the existing file isn't a valid JSON list, this raises instead of overwriting it.
    """
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_file.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)  # serializes writers, including separate processes
        entries = json.loads(audit_file.read_text(encoding="utf-8")) if audit_file.exists() else []
        if not isinstance(entries, list):
            raise RuntimeError(f"{audit_file} is not a JSON list; refusing to overwrite the audit trail")
        entry.previous_entry_hash = entries[-1]["entry_hash"] if entries else None
        entry.entry_hash = entry_hash(entry)
        entries.append(entry.model_dump(mode="json"))
        tmp = audit_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, audit_file)  # atomic: readers see the old file or the new one, never half of it
    return entry


def verify_audit_trail(audit_file: Path = AUDIT_FILE) -> tuple[bool, str]:
    """Recompute every hash in the chain. Returns (ok, message)."""
    if not audit_file.exists():
        return True, "no audit trail yet"
    entries = json.loads(audit_file.read_text(encoding="utf-8"))
    previous = None
    for i, raw in enumerate(entries):
        entry = AuditEntry(**raw)
        if entry.previous_entry_hash != previous or entry_hash(entry) != entry.entry_hash:
            return False, f"entry {i} (run {entry.run_id}) has been altered, removed or reordered"
        previous = entry.entry_hash
    return True, f"{len(entries)} entries, hash chain intact"


if __name__ == "__main__":
    ok, message = verify_audit_trail()
    print(("OK: " if ok else "TAMPERED: ") + message)
