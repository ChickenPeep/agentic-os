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
