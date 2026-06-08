"""Log incoming ideas to the vault raw/ inbox and the Supabase runs table.

All Supabase calls are best-effort: missing env or network failure returns None and
never raises, so logging can never block the chat. Uses stdlib urllib (no new deps).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import urllib.request
from typing import Optional


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_idea(text: str, message_url: str, raw_dir: str, now: Optional[str] = None) -> str:
    ts = now or _utcnow()
    safe = ts.replace(":", "").replace("-", "")
    fname = f"idea-{safe}.md"
    path = os.path.join(raw_dir, fname)
    body = (
        f"---\nsource: discord-command-center\ncaptured: {ts}\n---\n\n"
        f"# Idea ({ts})\n\n{text}\n\n[Discord message]({message_url})\n"
    )
    with open(path, "w") as f:
        f.write(body)
    return path


def _supabase_request(method: str, path: str, payload: Optional[dict]) -> Optional[dict]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        return None
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{url}{path}", data=data, method=method)
    req.add_header("apikey", key)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=representation")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except Exception:
        return None


def log_run(started_at: str, status: str, output: str) -> Optional[str]:
    skill_id = os.environ.get("COMMAND_CENTER_BOT_SKILL_ID")
    if not skill_id:
        return None
    rows = _supabase_request("POST", "/rest/v1/runs", {
        "skill_id": skill_id,
        "started_at": started_at,
        "status": status,
        "output": output[:4000],
        "triggered_by": "discord",
        "host": "mac",
    })
    if isinstance(rows, list) and rows:
        return rows[0].get("id")
    return None


def update_run(run_id: str, status: str, output: str) -> None:
    if not run_id:
        return
    _supabase_request("PATCH", f"/rest/v1/runs?id=eq.{run_id}", {
        "status": status,
        "output": output[:4000],
        "ended_at": _utcnow(),
    })
