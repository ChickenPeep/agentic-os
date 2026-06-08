"""Shared markdown-note writer for the Obsidian command center.

Stdlib only. Skills and the Discord bot call these to drop frontmatter notes into
command-center/ folders, which a Dataview note renders. Copied into each runtime dir
by that runtime's deploy script so launchd never imports across iCloud.
"""
from __future__ import annotations

import datetime as _dt
import glob
import os
import re

CC = "command-center"


def _utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify(text: str, max_len: int = 50) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:max_len].rstrip("-") or "untitled"


def _stamp(iso: str) -> str:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})", iso or "")
    if not m:
        return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d-%H%M")
    y, mo, d, h, mi = m.groups()
    return f"{y}-{mo}-{d}-{h}{mi}"


def _yaml_value(v) -> str:
    s = "" if v is None else str(v)
    # ISO 8601 timestamps (e.g. 2026-06-08T14:30:00Z) are safe unquoted in YAML
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?$", s):
        return s
    if s == "" or re.search(r'[:#\[\]{}",]', s) or s != s.strip():
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _write_note(path: str, frontmatter: dict, body: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["---"]
    for k, v in frontmatter.items():
        lines.append(f"{k}: {_yaml_value(v)}")
    lines += ["---", "", body.rstrip() + "\n"]
    with open(path, "w") as f:
        f.write("\n".join(lines))
    return path


def write_activity(vault: str, skill: str, status: str, summary: str,
                   when: str | None = None, branch: str | None = None) -> str:
    when = when or _utcnow()
    fm = {"type": "activity", "skill": skill, "status": status,
          "when": when, "summary": summary}
    if branch:
        fm["branch"] = branch
    name = f"{_stamp(when)}-{_slugify(skill)}.md"
    return _write_note(os.path.join(vault, CC, "activity", name), fm, summary)
