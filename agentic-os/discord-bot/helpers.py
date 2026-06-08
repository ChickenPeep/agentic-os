"""Pure helpers for the Discord bot (approval detection, slug, progress formatting)."""
from __future__ import annotations

import re

_APPROVAL = {"ship it", "ship", "go", "do it", "approved"}


def is_approval(text: str) -> bool:
    return (text or "").strip().lower() in _APPROVAL


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:max_len].rstrip("-")


def format_progress(lines: list[str], final: str | None) -> str:
    recent = lines[-8:]
    body = "\n".join(f"• {ln}" for ln in recent) if recent else "• working…"
    if final:
        return f"{final}\n\n—\n{body}" if recent else final
    return f"🤔 working…\n{body}"
