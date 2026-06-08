# runner.py
"""Drive the claude CLI in headless stream-json mode and parse its events.

parse_stream_events() is pure (testable). run_claude() wraps the subprocess and
calls on_progress(line) as human-readable progress accumulates.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional


@dataclass
class ParsedRun:
    progress: list[str] = field(default_factory=list)
    final_text: str = ""
    session_id: Optional[str] = None
    is_error: bool = False


def _describe_tool(name: str, inp: dict) -> str:
    inp = inp or {}
    if name == "Bash":
        cmd = (inp.get("command", "") or "").strip().splitlines()[0:1]
        return f"$ {cmd[0]}" if cmd else "$ (bash)"
    target = inp.get("file_path") or inp.get("path") or inp.get("pattern") or ""
    return f"{name} {target}".strip()


def parse_stream_events(lines: Iterable[str]) -> ParsedRun:
    out = ParsedRun()
    for line in lines:
        line = (line or "").strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        etype = ev.get("type")
        if etype == "system" and ev.get("session_id"):
            out.session_id = ev["session_id"]
        elif etype == "assistant":
            for block in ev.get("message", {}).get("content", []) or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    out.progress.append(_describe_tool(block.get("name", "?"), block.get("input", {})))
        elif etype == "result":
            out.final_text = ev.get("result", "") or out.final_text
            if ev.get("session_id"):
                out.session_id = ev["session_id"]
            out.is_error = bool(ev.get("is_error"))
    return out
