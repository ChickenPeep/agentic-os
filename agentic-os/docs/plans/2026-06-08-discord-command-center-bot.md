# Discord Command Center Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An always-on Discord bot on the Mac mini that lets Gabe text Claude Code from his phone — chat with memory, autonomous research/building on a git branch, with push/deploy/spend/external-send gated behind explicit approval.

**Architecture:** A single long-running `discord.py` process (launchd, `KeepAlive=true`) listens in one allowlisted channel for the owner's messages. Each message is logged (vault `raw/` + Supabase `runs`) and dispatched to a runner that shells out to the Mac's already-authenticated `claude` CLI (`-p --output-format stream-json --resume <id> --settings bridge-settings.json`). A PreToolUse guard hook, loaded **only** via `--settings` for the bot's runs, denies gated actions while allowing safe ones. Results are summarized back to Discord; "ship it" pushes + opens a PR.

**Tech Stack:** Python 3.9+, `discord.py`, the `claude` CLI (v2.1+), Supabase REST (service role key), launchd, git/`gh`.

**Spec:** `agentic-os/docs/specs/2026-06-08-discord-command-center-bot-design.md`

---

## File Structure

```
agentic-os/discord-bot/
  guard_hook.py         # decide(tool_name, tool_input) pure fn + stdin/stdout hook CLI
  bridge-settings.json  # registers guard_hook as a PreToolUse hook (bot runs only)
  state.py              # Store: persistent per-channel {session_id, branch, pending_action}
  idealog.py            # log_idea() -> raw/ file; log_run()/update_run() -> Supabase runs
  runner.py             # parse_stream_events() pure parser + run_claude() subprocess driver
  bot.py                # discord.py gateway, owner/channel gate, dispatch, progress, approval
  helpers.py            # pure helpers: is_approval(), slugify(), format_progress()
  config.json           # branch_prefix, timeouts, model, progress throttle
  requirements.txt      # discord.py
  supabase-seed.sql     # seeds command-center.bot skill row
  deploy.sh             # copy runtime to ~/agentic-os-server/discord-bot, install, load plist
  README.md
  .gitignore
  .gitattributes
  tests/
    test_guard_hook.py
    test_state.py
    test_idealog.py
    test_runner.py
    test_helpers.py
agentic-os/launchd/com.agenticos.discord-bot.plist
```

**Key interfaces (consistent names used across all tasks):**
- `guard_hook.decide(tool_name: str, tool_input: dict) -> dict` returning `{"allow": bool, "reason": str}`
- `state.Store(path)` with `.get(channel_id) -> dict`, `.update(channel_id, **fields)`, `.clear_pending(channel_id)`
- `idealog.log_idea(text: str, message_url: str, raw_dir: str) -> str` (returns file path)
- `idealog.log_run(skill_id, started_at, status, output) -> str | None` (returns run id), `idealog.update_run(run_id, status, output) -> None`
- `runner.parse_stream_events(lines: Iterable[str]) -> ParsedRun` (dataclass: `progress: list[str]`, `final_text: str`, `session_id: str | None`, `is_error: bool`)
- `runner.run_claude(prompt, *, session_id, resume, branch, cwd, settings_path, on_progress) -> ParsedRun`
- `helpers.is_approval(text: str) -> bool`, `helpers.slugify(text: str) -> str`, `helpers.format_progress(lines: list[str], final: str | None) -> str`

---

## Task 1: Project scaffold

**Files:**
- Create: `agentic-os/discord-bot/requirements.txt`
- Create: `agentic-os/discord-bot/.gitignore`
- Create: `agentic-os/discord-bot/.gitattributes`
- Create: `agentic-os/discord-bot/config.json`
- Create: `agentic-os/discord-bot/tests/__init__.py`
- Create: `agentic-os/discord-bot/tests/conftest.py`

- [ ] **Step 1: Create `requirements.txt`**

```
discord.py>=2.3,<3
pytest>=8,<9
```

- [ ] **Step 2: Create `.gitignore`** (mirror pokemon-hunter)

```
data/
__pycache__/
*.pyc
.env
.venv/
venv/
.pytest_cache/
```

- [ ] **Step 3: Create `.gitattributes`** (mirror pokemon-hunter)

```
# Shell scripts run on the Mac (bash). Force LF so Windows CRLF never breaks them.
*.sh text eol=lf
```

- [ ] **Step 4: Create `config.json`**

```json
{
  "branch_prefix": "bot/",
  "claude_timeout_seconds": 1200,
  "heartbeat_seconds": 45,
  "progress_edit_min_interval_seconds": 2,
  "model": "",
  "approval_words": ["ship it", "ship", "go", "do it", "approved"]
}
```

- [ ] **Step 5: Create `tests/__init__.py`** (empty file)

- [ ] **Step 6: Create `tests/conftest.py`** so tests import modules from the package dir

```python
import os
import sys

# Make the discord-bot package dir importable as top-level modules in tests.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 7: Install deps and verify pytest runs**

Run: `cd agentic-os/discord-bot && python3 -m pip install -q -r requirements.txt && python3 -m pytest -q`
Expected: pytest runs and reports "no tests ran" (exit 5) — confirms the harness works.

- [ ] **Step 8: Commit**

```bash
git add agentic-os/discord-bot/requirements.txt agentic-os/discord-bot/.gitignore agentic-os/discord-bot/.gitattributes agentic-os/discord-bot/config.json agentic-os/discord-bot/tests/__init__.py agentic-os/discord-bot/tests/conftest.py
git commit -m "discord-bot: project scaffold (deps, config, test harness)"
```

---

## Task 2: Guard hook — `decide()` pure function

**Files:**
- Create: `agentic-os/discord-bot/guard_hook.py`
- Test: `agentic-os/discord-bot/tests/test_guard_hook.py`

The hook allows by default and denies only gated patterns (push/merge-to-main, deploy/launchctl/restart, external sends, paid APIs). Read-only research fetches (`curl`/`wget` GETs) are allowed.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_guard_hook.py
import guard_hook


def D(tool, **inp):
    return guard_hook.decide(tool, inp)


def test_read_write_edit_allowed():
    assert D("Read", file_path="/x")["allow"] is True
    assert D("Write", file_path="/x", content="y")["allow"] is True
    assert D("Edit", file_path="/x")["allow"] is True


def test_git_commit_and_branch_allowed():
    assert D("Bash", command="git add -A && git commit -m 'wip'")["allow"] is True
    assert D("Bash", command="git checkout -b bot/foo")["allow"] is True
    assert D("Bash", command="git diff --stat")["allow"] is True


def test_git_push_denied():
    r = D("Bash", command="git push -u origin bot/foo")
    assert r["allow"] is False
    assert "approve" in r["reason"].lower()


def test_merge_to_main_denied():
    assert D("Bash", command="git merge bot/foo")["allow"] is False
    assert D("Bash", command="git checkout main")["allow"] is False


def test_deploy_and_launchctl_denied():
    assert D("Bash", command="bash deploy.sh")["allow"] is False
    assert D("Bash", command="launchctl load ~/Library/LaunchAgents/x.plist")["allow"] is False


def test_external_send_denied_but_get_allowed():
    assert D("Bash", command="curl -X POST https://api.x.com/send -d @p")["allow"] is False
    assert D("Bash", command="gh pr create --fill")["allow"] is False
    assert D("Bash", command="curl -s https://redsky.target.com/x")["allow"] is True


def test_unknown_bash_allowed_by_default():
    assert D("Bash", command="python3 -m pytest -q")["allow"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_guard_hook.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'guard_hook'`.

- [ ] **Step 3: Write minimal implementation**

```python
# guard_hook.py
"""Claude Code PreToolUse guard for the Discord bridge.

Loaded ONLY for the bot's headless runs via `claude --settings bridge-settings.json`,
so Gabe's interactive sessions are unaffected. Policy: allow by default, deny the
gated actions (push/merge-to-main, deploy/launchctl/restart, external sends, paid APIs).
"""
from __future__ import annotations

import json
import re
import sys

# Bash command patterns that must be gated (denied; Claude is told to ask for approval).
_DENY_PATTERNS = [
    r"\bgit\s+push\b",
    r"\bgit\s+merge\b",
    r"\bgit\s+(checkout|switch)\s+main\b",
    r"\bgit\s+(checkout|switch)\s+master\b",
    r"\blaunchctl\b",
    r"\bdeploy\.sh\b",
    r"\bgh\s+(pr|release|repo)\s+(create|merge|edit)\b",
    r"\b(systemctl|service)\b",
]

# Outbound-write network calls are gated; read-only GET fetches for research are allowed.
_NETWORK_BIN = re.compile(r"\b(curl|wget|http|https)\b")
_NETWORK_WRITE = re.compile(r"(-X\s*(POST|PUT|PATCH|DELETE)|--data|-d\s|--upload-file|-T\s)")

_DENY_RE = [re.compile(p) for p in _DENY_PATTERNS]

_ALLOW = {"Read", "Write", "Edit", "Grep", "Glob", "NotebookEdit", "TodoWrite"}


def decide(tool_name: str, tool_input: dict) -> dict:
    if tool_name in _ALLOW:
        return {"allow": True, "reason": "safe tool"}
    if tool_name != "Bash":
        # Unknown non-Bash tools (e.g. WebFetch) are read-only research; allow.
        return {"allow": True, "reason": "non-mutating tool"}

    cmd = (tool_input or {}).get("command", "") or ""
    for rx in _DENY_RE:
        if rx.search(cmd):
            return {
                "allow": False,
                "reason": "Gated action. Stage your work on the branch, summarize it, "
                          "and tell Gabe to reply 'ship it' to approve.",
            }
    if _NETWORK_BIN.search(cmd) and _NETWORK_WRITE.search(cmd):
        return {
            "allow": False,
            "reason": "Outbound external send is gated. Summarize and ask Gabe to approve.",
        }
    return {"allow": True, "reason": "ok"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_guard_hook.py -q`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add agentic-os/discord-bot/guard_hook.py agentic-os/discord-bot/tests/test_guard_hook.py
git commit -m "discord-bot: guard hook decide() with allow-by-default deny-gated policy"
```

---

## Task 3: Guard hook — stdin/stdout CLI + settings file

**Files:**
- Modify: `agentic-os/discord-bot/guard_hook.py` (append `main()`)
- Test: `agentic-os/discord-bot/tests/test_guard_hook.py` (append CLI test)
- Create: `agentic-os/discord-bot/bridge-settings.json`

Claude Code PreToolUse hooks receive a JSON event on stdin and return a JSON decision on stdout. The decision shape: `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow"|"deny", "permissionDecisionReason": "..."}}`.

- [ ] **Step 1: Write the failing test (append to `tests/test_guard_hook.py`)**

```python
import json
import subprocess
import sys
import os

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "guard_hook.py")


def _run_hook(event: dict) -> dict:
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(event),
                       capture_output=True, text=True, timeout=10)
    return json.loads(p.stdout)


def test_cli_allows_write():
    out = _run_hook({"tool_name": "Write", "tool_input": {"file_path": "/x"}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_cli_denies_push():
    out = _run_hook({"tool_name": "Bash", "tool_input": {"command": "git push origin x"}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "ship it" in out["hookSpecificOutput"]["permissionDecisionReason"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_guard_hook.py -k cli -q`
Expected: FAIL — `json.decoder.JSONDecodeError` (no stdout, `main()` missing).

- [ ] **Step 3: Append `main()` to `guard_hook.py`**

```python
def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        event = {}
    result = decide(event.get("tool_name", ""), event.get("tool_input", {}))
    decision = "allow" if result["allow"] else "deny"
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": result["reason"],
        }
    }))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create `bridge-settings.json`** (the `$DISCORD_BOT_DIR` token is replaced by `deploy.sh` with the deployed absolute path in Task 9)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $DISCORD_BOT_DIR/guard_hook.py"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_guard_hook.py -q`
Expected: PASS (all guard_hook tests).

- [ ] **Step 6: Commit**

```bash
git add agentic-os/discord-bot/guard_hook.py agentic-os/discord-bot/bridge-settings.json agentic-os/discord-bot/tests/test_guard_hook.py
git commit -m "discord-bot: guard hook CLI + bridge-settings.json (PreToolUse registration)"
```

---

## Task 4: Persistent conversation state

**Files:**
- Create: `agentic-os/discord-bot/state.py`
- Test: `agentic-os/discord-bot/tests/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_state.py
import os
import state


def test_get_returns_empty_for_unknown(tmp_path):
    s = state.Store(str(tmp_path / "state.json"))
    assert s.get(123) == {}


def test_update_persists_across_instances(tmp_path):
    path = str(tmp_path / "state.json")
    s = state.Store(path)
    s.update(123, session_id="sess-1", branch="bot/foo")
    s2 = state.Store(path)
    got = s2.get(123)
    assert got["session_id"] == "sess-1"
    assert got["branch"] == "bot/foo"


def test_update_merges_fields(tmp_path):
    s = state.Store(str(tmp_path / "state.json"))
    s.update(1, session_id="a")
    s.update(1, branch="bot/b")
    assert s.get(1) == {"session_id": "a", "branch": "bot/b"}


def test_pending_set_and_clear(tmp_path):
    s = state.Store(str(tmp_path / "state.json"))
    s.update(1, pending_action={"type": "push", "branch": "bot/b"})
    assert s.get(1)["pending_action"]["type"] == "push"
    s.clear_pending(1)
    assert s.get(1).get("pending_action") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_state.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'state'`.

- [ ] **Step 3: Write minimal implementation**

```python
# state.py
"""Persistent per-channel conversation state (session id, branch, pending approval).

Stored as a single JSON file on local disk so memory and pending approvals survive
bot restarts. Keys are stringified channel ids.
"""
from __future__ import annotations

import json
import os
from typing import Any


class Store:
    def __init__(self, path: str):
        self.path = path
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    self._data = json.load(f)
            except (ValueError, OSError):
                self._data = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self.path)

    def get(self, channel_id: int) -> dict:
        return dict(self._data.get(str(channel_id), {}))

    def update(self, channel_id: int, **fields: Any) -> None:
        rec = self._data.setdefault(str(channel_id), {})
        rec.update(fields)
        self._save()

    def clear_pending(self, channel_id: int) -> None:
        rec = self._data.get(str(channel_id))
        if rec and "pending_action" in rec:
            rec["pending_action"] = None
            self._save()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_state.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add agentic-os/discord-bot/state.py agentic-os/discord-bot/tests/test_state.py
git commit -m "discord-bot: persistent per-channel conversation state"
```

---

## Task 5: Idea logging (raw/ inbox + Supabase runs)

**Files:**
- Create: `agentic-os/discord-bot/idealog.py`
- Test: `agentic-os/discord-bot/tests/test_idealog.py`

`log_idea` writes a timestamped markdown file to the vault `raw/`. `log_run`/`update_run` POST/PATCH the Supabase `runs` table via the service role key (best-effort: any failure returns `None`/swallows, never raises). Network calls use `urllib` (stdlib) to avoid adding a dependency, and are skipped when env vars are missing.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_idealog.py
import os
import idealog


def test_log_idea_writes_raw_file(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    path = idealog.log_idea("Add a streak counter to Nexum",
                            "https://discord.com/channels/1/2/3",
                            str(raw), now="2026-06-08T12:00:00Z")
    assert os.path.exists(path)
    body = open(path).read()
    assert "Add a streak counter to Nexum" in body
    assert "discord.com/channels/1/2/3" in body


def test_log_run_returns_none_without_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("COMMAND_CENTER_BOT_SKILL_ID", raising=False)
    assert idealog.log_run("2026-06-08T12:00:00Z", "received", "hi") is None


def test_log_run_swallows_network_errors(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:1")  # nothing listening
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "x")
    monkeypatch.setenv("COMMAND_CENTER_BOT_SKILL_ID", "skill-1")
    # Must not raise even though the connection fails.
    assert idealog.log_run("2026-06-08T12:00:00Z", "received", "hi") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_idealog.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'idealog'`.

- [ ] **Step 3: Write minimal implementation**

```python
# idealog.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_idealog.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add agentic-os/discord-bot/idealog.py agentic-os/discord-bot/tests/test_idealog.py
git commit -m "discord-bot: idea logging to raw/ inbox + Supabase runs (best-effort)"
```

---

## Task 6: Runner — stream-json parser

**Files:**
- Create: `agentic-os/discord-bot/runner.py`
- Test: `agentic-os/discord-bot/tests/test_runner.py`

`parse_stream_events` turns `claude --output-format stream-json` lines into a `ParsedRun`. Event shapes (from Claude Code): assistant tool-use → `{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Edit","input":{"file_path":"x"}}]}}`; final result → `{"type":"result","subtype":"success","result":"<text>","session_id":"<id>","is_error":false}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_runner.py
import json
import runner


def _lines(*events):
    return [json.dumps(e) for e in events]


def test_parses_final_text_and_session():
    lines = _lines(
        {"type": "system", "subtype": "init", "session_id": "sess-9"},
        {"type": "result", "subtype": "success", "result": "Done. Staged on bot/x.",
         "session_id": "sess-9", "is_error": False},
    )
    out = runner.parse_stream_events(lines)
    assert out.final_text == "Done. Staged on bot/x."
    assert out.session_id == "sess-9"
    assert out.is_error is False


def test_collects_tool_use_progress():
    lines = _lines(
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": "a.py"}}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "git commit -m x"}}]}},
        {"type": "result", "subtype": "success", "result": "ok", "session_id": "s", "is_error": False},
    )
    out = runner.parse_stream_events(lines)
    assert "Edit a.py" in out.progress[0]
    assert "git commit" in out.progress[1]


def test_error_result_flagged():
    lines = _lines(
        {"type": "result", "subtype": "error_max_turns", "result": "stopped",
         "session_id": "s", "is_error": True},
    )
    out = runner.parse_stream_events(lines)
    assert out.is_error is True


def test_ignores_malformed_lines():
    out = runner.parse_stream_events(["not json", "", "{bad}"])
    assert out.final_text == ""
    assert out.session_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_runner.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'runner'`.

- [ ] **Step 3: Write minimal implementation (parser only)**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_runner.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add agentic-os/discord-bot/runner.py agentic-os/discord-bot/tests/test_runner.py
git commit -m "discord-bot: runner stream-json parser (pure, tested)"
```

---

## Task 7: Runner — `run_claude()` subprocess driver

**Files:**
- Modify: `agentic-os/discord-bot/runner.py` (append `run_claude` + branch helpers)
- Test: `agentic-os/discord-bot/tests/test_runner.py` (append command-construction test)

`run_claude` builds the argv, runs the subprocess streaming stdout line-by-line into `parse_stream_events` while invoking `on_progress`, and enforces a timeout. The argv builder is factored into `build_argv` so it can be unit-tested without spawning Claude.

- [ ] **Step 1: Write the failing test (append to `tests/test_runner.py`)**

```python
def test_build_argv_first_message_uses_session_id():
    argv = runner.build_argv("hello", session_id="uuid-1", resume=False,
                             settings_path="/s.json", model="")
    assert "--session-id" in argv and "uuid-1" in argv
    assert "--resume" not in argv
    assert "-p" in argv and "hello" in argv
    assert argv[argv.index("--output-format") + 1] == "stream-json"
    assert argv[argv.index("--settings") + 1] == "/s.json"


def test_build_argv_resume_uses_resume_flag():
    argv = runner.build_argv("hi again", session_id="uuid-1", resume=True,
                             settings_path="/s.json", model="claude-opus-4-8")
    assert "--resume" in argv and "uuid-1" in argv
    assert "--session-id" not in argv
    assert "--model" in argv and "claude-opus-4-8" in argv
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_runner.py -k build_argv -q`
Expected: FAIL — `AttributeError: module 'runner' has no attribute 'build_argv'`.

- [ ] **Step 3: Append implementation to `runner.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_runner.py -q`
Expected: PASS (all runner tests).

- [ ] **Step 5: Commit**

```bash
git add agentic-os/discord-bot/runner.py agentic-os/discord-bot/tests/test_runner.py
git commit -m "discord-bot: run_claude subprocess driver + branch helpers"
```

---

## Task 8: Pure bot helpers

**Files:**
- Create: `agentic-os/discord-bot/helpers.py`
- Test: `agentic-os/discord-bot/tests/test_helpers.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_helpers.py
import helpers


def test_is_approval_matches_words():
    for t in ["ship it", "Ship It", "go", "  do it ", "approved"]:
        assert helpers.is_approval(t) is True
    for t in ["what about ships", "don't ship it yet", "research go-karts"]:
        assert helpers.is_approval(t) is False


def test_slugify():
    assert helpers.slugify("Add a Streak Counter to Nexum!") == "add-a-streak-counter-to-nexum"
    assert helpers.slugify("   spaced   out  ") == "spaced-out"
    assert len(helpers.slugify("word " * 40)) <= 40


def test_format_progress_truncates_and_lists():
    msg = helpers.format_progress(["Edit a.py", "$ git commit -m x"], final=None)
    assert "Edit a.py" in msg
    assert "git commit" in msg
    done = helpers.format_progress(["Edit a.py"], final="All done.")
    assert "All done." in done
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_helpers.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'helpers'`.

- [ ] **Step 3: Write minimal implementation**

```python
# helpers.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_helpers.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add agentic-os/discord-bot/helpers.py agentic-os/discord-bot/tests/test_helpers.py
git commit -m "discord-bot: pure helpers (approval detection, slugify, progress)"
```

---

## Task 9: Bot orchestration (`bot.py`)

**Files:**
- Create: `agentic-os/discord-bot/bot.py`

discord.py gateway wiring is integration code (not unit-tested here; covered by the manual acceptance run in Task 12). It composes the tested modules. Reads config from env + `config.json`.

- [ ] **Step 1: Write `bot.py`**

```python
# bot.py
"""Discord Command Center bot: phone -> Claude Code on the Mac mini.

Listens in one allowlisted channel for the owner's messages, logs each idea,
runs Claude headless on a per-conversation branch with the guard hook, streams
progress back, and handles the 'ship it' approval to push + open a PR.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
import uuid

import discord

import helpers
import idealog
import runner
from state import Store

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_config() -> dict:
    with open(os.path.join(HERE, "config.json")) as f:
        return json.load(f)


CFG = _load_config()
VAULT = os.environ.get("VAULT_PATH",
                       "/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault")
TOKEN = os.environ["DISCORD_BOT_TOKEN"]
OWNER_ID = int(os.environ["DISCORD_OWNER_ID"])
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
SETTINGS_PATH = os.path.join(HERE, "bridge-settings.json")
RAW_DIR = os.path.join(VAULT, "raw")
STATE = Store(os.path.join(HERE, "data", "state.json"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
_locks: dict[int, asyncio.Lock] = {}


def _lock(cid: int) -> asyncio.Lock:
    return _locks.setdefault(cid, asyncio.Lock())


@client.event
async def on_ready():
    print(f"command-center bot online as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.id != OWNER_ID or message.channel.id != CHANNEL_ID:
        return
    text = (message.content or "").strip()
    if not text:
        return

    # Approval path.
    if helpers.is_approval(text):
        await _handle_approval(message)
        return

    async with _lock(message.channel.id):
        await _handle_task(message, text)


async def _handle_task(message: discord.Message, text: str):
    # Best-effort logging (never blocks chat).
    try:
        idealog.log_idea(text, message.jump_url, RAW_DIR)
    except Exception as e:
        print(f"[idealog raw] {e}")
    started = idealog._utcnow()
    run_id = idealog.log_run(started, "working", text)

    rec = STATE.get(message.channel.id)
    session_id = rec.get("session_id") or str(uuid.uuid4())
    resume = bool(rec.get("session_id"))
    branch = rec.get("branch") or (CFG["branch_prefix"] + helpers.slugify(text) or "bot/task")
    STATE.update(message.channel.id, session_id=session_id, branch=branch)

    placeholder = await message.channel.send("🤔 on it…")

    progress: list[str] = []
    last_edit = {"t": 0.0}

    def on_progress(line: str):
        progress.append(line)
        now = time.time()
        if now - last_edit["t"] >= CFG["progress_edit_min_interval_seconds"]:
            last_edit["t"] = now
            asyncio.run_coroutine_threadsafe(
                placeholder.edit(content=helpers.format_progress(progress, None)[:1900]),
                client.loop,
            )

    try:
        runner.ensure_branch(VAULT, branch)
        result = await asyncio.to_thread(
            runner.run_claude, text,
            session_id=session_id, resume=resume, cwd=VAULT,
            settings_path=SETTINGS_PATH, model=CFG.get("model", ""),
            timeout=CFG["claude_timeout_seconds"], on_progress=on_progress,
        )
    except Exception as e:
        await placeholder.edit(content=f"⚠️ run failed: {e}")
        if run_id:
            idealog.update_run(run_id, "failed", str(e))
        return

    if result.session_id:
        STATE.update(message.channel.id, session_id=result.session_id)

    diffstat = subprocess.run(["git", "-C", VAULT, "diff", "--stat", "main...HEAD"],
                              capture_output=True, text=True).stdout.strip()
    summary = result.final_text or "(no output)"
    footer = ""
    if diffstat:
        STATE.update(message.channel.id, pending_action={"type": "push", "branch": branch})
        footer = f"\n\n📦 staged on `{branch}`:\n```\n{diffstat[:600]}\n```\nReply **ship it** to push + open a PR."
    final_msg = helpers.format_progress(progress, summary)[:1700] + footer
    await placeholder.edit(content=final_msg[:1990])
    if run_id:
        idealog.update_run(run_id, "error" if result.is_error else "done", summary)


async def _handle_approval(message: discord.Message):
    rec = STATE.get(message.channel.id)
    pending = rec.get("pending_action")
    if not pending or pending.get("type") != "push":
        await message.channel.send("Nothing staged to ship right now.")
        return
    branch = pending["branch"]
    await message.channel.send(f"🚀 pushing `{branch}` and opening a PR…")
    push = subprocess.run(["git", "-C", VAULT, "push", "-u", "origin", branch],
                          capture_output=True, text=True)
    if push.returncode != 0:
        await message.channel.send(f"⚠️ push failed:\n```\n{push.stderr[-500:]}\n```")
        return
    pr = subprocess.run(["gh", "pr", "create", "--fill", "--head", branch],
                        cwd=VAULT, capture_output=True, text=True)
    STATE.clear_pending(message.channel.id)
    link = pr.stdout.strip() or "(PR created)"
    await message.channel.send(f"✅ shipped. {link}")


if __name__ == "__main__":
    client.run(TOKEN)
```

- [ ] **Step 2: Byte-compile to catch syntax errors**

Run: `cd agentic-os/discord-bot && python3 -m py_compile bot.py && echo OK`
Expected: `OK` (note: importing bot.py requires env vars; py_compile only checks syntax).

- [ ] **Step 3: Run the full unit suite (modules bot.py depends on)**

Run: `cd agentic-os/discord-bot && python3 -m pytest -q`
Expected: PASS (all tests from Tasks 2–8).

- [ ] **Step 4: Commit**

```bash
git add agentic-os/discord-bot/bot.py
git commit -m "discord-bot: gateway orchestration (dispatch, progress, approval)"
```

> **Note on the push/PR step:** `git push` and `gh pr create` here run from `bot.py`
> (Python), AFTER Gabe's explicit "ship it" — they are NOT Claude tool calls, so the
> guard hook (which only governs Claude's headless runs) does not and should not apply.
> This is the single intended path by which gated git actions execute, and only on approval.

---

## Task 10: Supabase seed + launchd plist + deploy script

**Files:**
- Create: `agentic-os/discord-bot/supabase-seed.sql`
- Create: `agentic-os/launchd/com.agenticos.discord-bot.plist`
- Create: `agentic-os/discord-bot/deploy.sh`

- [ ] **Step 1: Create `supabase-seed.sql`** (mirror pokemon-hunter)

```sql
-- COMMAND-CENTER bot skill row for the dashboard.
-- After applying: select id from skills where slug = 'command-center.bot';
-- and put it in ~/.agentic-os.env as COMMAND_CENTER_BOT_SKILL_ID.
insert into skills (domain, name, slug, description, type, status, host)
values
  ('COMMAND-CENTER', 'bot', 'command-center.bot',
   'Discord bot bridging Gabe''s phone to Claude Code on the Mac mini; logs ideas and staged work.',
   'agent', 'active', 'mac')
on conflict (slug) do update
  set description = excluded.description,
      domain = excluded.domain,
      type = excluded.type,
      host = excluded.host;
```

- [ ] **Step 2: Create `com.agenticos.discord-bot.plist`** (mirror the server plist; loads env via the wrapper in deploy.sh)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.agenticos.discord-bot</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/gabri/agentic-os-server/discord-bot/run-bot.sh</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/gabri/agentic-os-server/logs/discord-bot-stdout.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/gabri/agentic-os-server/logs/discord-bot-stderr.log</string>
</dict>
</plist>
```

- [ ] **Step 3: Create `deploy.sh`** (copies runtime to local disk, writes `run-bot.sh`, patches `bridge-settings.json`, loads plist — mirrors pokemon-hunter/deploy.sh)

```bash
#!/bin/bash
# Deploy the Discord command-center bot onto the Mac mini. Idempotent; re-run after edits.
set -euo pipefail

MAC_VAULT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
SRC="$MAC_VAULT/agentic-os/discord-bot"
DEST="$HOME/agentic-os-server/discord-bot"
LA="$HOME/Library/LaunchAgents"
PL="com.agenticos.discord-bot"

[ -d "$SRC" ] || { echo "ERROR: source not found: $SRC"; exit 1; }

echo "==> Copying runtime to $DEST"
mkdir -p "$DEST" "$HOME/agentic-os-server/logs" "$LA"
rsync -a --delete \
  --exclude 'data/' --exclude '__pycache__/' --exclude '.venv/' --exclude '.pytest_cache/' \
  "$SRC/" "$DEST/"

echo "==> Installing Python deps"
python3 -m pip install -q -r "$DEST/requirements.txt"

echo "==> Patching bridge-settings.json with deployed path"
python3 - "$DEST" <<'PY'
import json, sys, os
dest = sys.argv[1]
p = os.path.join(dest, "bridge-settings.json")
s = json.load(open(p))
for grp in s.get("hooks", {}).get("PreToolUse", []):
    for h in grp.get("hooks", []):
        h["command"] = f"python3 {dest}/guard_hook.py"
json.dump(s, open(p, "w"), indent=2)
PY

echo "==> Writing run-bot.sh (sources env, then launches)"
cat > "$DEST/run-bot.sh" <<EOF
#!/bin/bash
set -uo pipefail
cd "$DEST"
set -a
[ -f ~/.agentic-os.env ] && source ~/.agentic-os.env
export VAULT_PATH="$MAC_VAULT"
set +a
exec python3 bot.py
EOF
chmod +x "$DEST/run-bot.sh"

echo "==> Installing launchd service"
cp "$MAC_VAULT/agentic-os/launchd/$PL.plist" "$LA/$PL.plist"
launchctl unload "$LA/$PL.plist" 2>/dev/null || true
launchctl load "$LA/$PL.plist"
echo "==> Done. Tail logs: ~/agentic-os-server/logs/discord-bot-*.log"
```

- [ ] **Step 4: Make deploy.sh executable and syntax-check both shell scripts**

Run: `cd agentic-os/discord-bot && chmod +x deploy.sh && bash -n deploy.sh && echo OK`
Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add agentic-os/discord-bot/supabase-seed.sql agentic-os/discord-bot/deploy.sh agentic-os/launchd/com.agenticos.discord-bot.plist
git commit -m "discord-bot: supabase seed, launchd plist, deploy script"
```

---

## Task 11: README

**Files:**
- Create: `agentic-os/discord-bot/README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# Discord Command Center Bot

Text Claude Code from your phone. Runs 24/7 on the Mac mini. You message one Discord
channel; the bot chats with memory, researches/builds on a `bot/<slug>` branch, and
reports back. Push/merge, deploy, spending, and external sends wait for you to reply
**ship it**. Ideas are logged to the vault `raw/` inbox and the dashboard.

## How it works
`bot.py` (discord.py, launchd) → `runner.py` shells out to the Mac's logged-in
`claude` CLI (`-p --output-format stream-json --resume <id> --settings bridge-settings.json`).
`guard_hook.py` is a PreToolUse hook loaded **only** for the bot's runs (via `--settings`),
so your own interactive Claude sessions are unaffected. It allows safe tools and denies
gated ones (push/merge/deploy/launchctl/external sends/paid APIs).

## Setup (on the Mac mini)
1. **Create the Discord bot:** https://discord.com/developers/applications → New
   Application → Bot → Reset Token → copy it. Under **Privileged Gateway Intents**,
   enable **Message Content Intent**.
2. **Invite it:** OAuth2 → URL Generator → scopes `bot`; permissions: View Channel,
   Send Messages, Read Message History. Open the URL, add it to your server.
3. **Get the IDs:** in Discord, enable Developer Mode (Settings → Advanced), then
   right-click your user → Copy User ID, and right-click the target channel → Copy
   Channel ID.
4. **Env:** add to `~/.agentic-os.env`:
   ```
   DISCORD_BOT_TOKEN=...
   DISCORD_OWNER_ID=...
   DISCORD_CHANNEL_ID=...
   COMMAND_CENTER_BOT_SKILL_ID=...   # from the seed step
   ```
5. **Seed the dashboard:** apply `supabase-seed.sql`, then
   `select id from skills where slug='command-center.bot';` → put it in the env above.
6. **Deploy:** `bash deploy.sh` (copies runtime to `~/agentic-os-server/discord-bot/`,
   installs deps, loads the launchd service). Re-run after any edit.

## Test
```bash
python3 -m pytest -q          # unit tests
```
Then in Discord: send "what's in the vault root?" (read-only), then a small feature
request; verify a `bot/...` branch + staged diff appear, then reply **ship it** for a PR.

## Guardrails
The guard hook (`guard_hook.py`, `decide()`) is the blast-radius limiter. The ONLY path
that pushes/opens a PR is `bot.py` after your explicit "ship it" — never Claude itself.
Deploy / spend / external sends are reported, never auto-run.
````

- [ ] **Step 2: Commit**

```bash
git add agentic-os/discord-bot/README.md
git commit -m "discord-bot: README (setup, guardrails, test)"
```

---

## Task 12: Full suite + manual acceptance (gated on Gabe's Discord setup)

**Files:** none (verification only)

- [ ] **Step 1: Run the full unit suite**

Run: `cd agentic-os/discord-bot && python3 -m pytest -q`
Expected: all tests pass.

- [ ] **Step 2: (Gabe) Complete Discord app + env setup** per README steps 1–5. Stop here until `DISCORD_BOT_TOKEN`, `DISCORD_OWNER_ID`, `DISCORD_CHANNEL_ID`, `COMMAND_CENTER_BOT_SKILL_ID` exist in `~/.agentic-os.env`.

- [ ] **Step 3: Deploy and confirm the service is up**

Run: `bash agentic-os/discord-bot/deploy.sh && launchctl list | grep discord-bot`
Expected: deploy completes; `com.agenticos.discord-bot` listed. Check `~/agentic-os-server/logs/discord-bot-stdout.log` shows "command-center bot online".

- [ ] **Step 4: Manual acceptance in Discord**
  - Send "what's in the vault root?" → bot replies with a read-only answer (no branch).
  - Send a small feature request (e.g. "add a one-line note to STATUS.md saying the bot is live") → bot posts progress, then a summary with a `bot/...` branch + diff stat.
  - In another terminal, confirm the guard blocks pushes: check the run did NOT push (`git -C "$VAULT" branch -r` shows no new remote branch yet).
  - Reply **ship it** → bot posts a PR link; verify the PR exists on GitHub.
  - Confirm the idea was logged: a new `raw/idea-*.md` file exists and a `runs` row shows for `command-center.bot`.

- [ ] **Step 5: Final commit (if any acceptance fixes were needed)**

```bash
git add -A && git commit -m "discord-bot: acceptance fixes" || echo "nothing to commit"
```

---

## Self-Review Notes (author)

- **Spec coverage:** architecture (T9), components bot/runner/guard/state/idealog (T2–T9),
  data flow incl. approval (T9), security owner/channel allowlist + guard via `--settings`
  (T2/T3/T9), error handling timeout/crash/serialize (T7/T9), idea logging raw+dashboard
  (T5), dashboard skill seed (T10), testing (T2–T8, T12), setup steps (T11). All spec
  sections map to a task.
- **Guard-only-for-bot:** enforced via `--settings bridge-settings.json` (T3/T7), not a
  vault-wide `.claude/settings.json` — protects Gabe's interactive sessions.
- **Gated push path:** the single intended exception is `bot.py`'s post-approval
  `git push`/`gh pr create` (T9 note) — runs outside Claude, only on "ship it".
- **Type/name consistency:** `decide`, `Store.get/update/clear_pending`, `log_idea/log_run/
  update_run`, `parse_stream_events`/`ParsedRun`/`build_argv`/`run_claude`,
  `is_approval/slugify/format_progress` used identically across tasks.
