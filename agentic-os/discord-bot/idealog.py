# agentic-os/discord-bot/idealog.py
"""Bridge the Discord bot to the vault command center.

capture_idea() writes an idea note; log_activity() writes a run note. Both best-effort:
any failure returns None and never raises, so logging can't break the chat. Uses the
shared notes.py (copied into this runtime by deploy.sh).
"""
from __future__ import annotations

from typing import Optional

import notes

BOT_SKILL = "command-center.bot"


def capture_idea(vault: str, text: str, message_url: str) -> Optional[str]:
    title = (text.strip().splitlines()[0] if text.strip() else "untitled")[:80]
    body = f"{text}\n\n[Discord message]({message_url})"
    try:
        return notes.write_idea(vault, title, body, source="discord")
    except Exception as e:
        print(f"[idealog capture_idea] {e}")
        return None


def log_activity(vault: str, status: str, summary: str,
                 branch: Optional[str] = None) -> Optional[str]:
    try:
        return notes.write_activity(vault, BOT_SKILL, status, summary, branch=branch)
    except Exception as e:
        print(f"[idealog log_activity] {e}")
        return None
