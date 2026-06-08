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


_BRIDGE_PROMPT = (
    "You are reachable via Discord from Gabe's phone as the agentic-os command center. "
    "Work is staged on the current git branch. You CANNOT push, merge to main, deploy, "
    "restart services, spend money, or send external messages — a guard will block those. "
    "When you need one, finish and stage your work, summarize what you did and the branch, "
    "and tell Gabe to reply 'ship it' to approve. Be concise; you are talking to a phone."
)


def build_argv(prompt: str, *, session_id: str, resume: bool, settings_path: str,
               model: str = "") -> list[str]:
    argv = [
        "claude", "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--settings", settings_path,
        "--append-system-prompt", _BRIDGE_PROMPT,
        "--permission-mode", "acceptEdits",
    ]
    if resume:
        argv += ["--resume", session_id]
    else:
        argv += ["--session-id", session_id]
    if model:
        argv += ["--model", model]
    return argv


def ensure_branch(cwd: str, branch: str) -> None:
    """Checkout an existing bot branch or create it from the current HEAD."""
    existing = subprocess.run(["git", "-C", cwd, "rev-parse", "--verify", branch],
                              capture_output=True, text=True)
    if existing.returncode == 0:
        subprocess.run(["git", "-C", cwd, "checkout", branch], check=True,
                       capture_output=True, text=True)
    else:
        subprocess.run(["git", "-C", cwd, "checkout", "-b", branch], check=True,
                       capture_output=True, text=True)


def run_claude(prompt: str, *, session_id: str, resume: bool, cwd: str,
               settings_path: str, model: str = "", timeout: int = 1200,
               on_progress: Optional[Callable[[str], None]] = None) -> ParsedRun:
    argv = build_argv(prompt, session_id=session_id, resume=resume,
                      settings_path=settings_path, model=model)
    proc = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, bufsize=1)
    captured: list[str] = []
    try:
        for line in proc.stdout:  # streams as Claude emits events
            captured.append(line)
            partial = parse_stream_events(captured)
            if on_progress and partial.progress:
                on_progress(partial.progress[-1])
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        run = parse_stream_events(captured)
        run.is_error = True
        run.final_text = (run.final_text + "\n\n[aborted: exceeded time limit]").strip()
        return run
    return parse_stream_events(captured)
