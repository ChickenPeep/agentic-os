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


def _yaml_value(v, force_quote: bool = False) -> str:
    s = "" if v is None else str(v)
    # ISO 8601 timestamps (e.g. 2026-06-08T14:30:00Z) are safe unquoted in YAML
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?$", s):
        return s
    # Newlines, carriage-returns, and backslashes must always be double-quoted.
    needs_newline_escape = bool(re.search(r"[\n\r\\]", s))
    if force_quote or needs_newline_escape or s == "" or re.search(r'[:#\[\]{}",]', s) or s != s.strip():
        # Escape backslashes first (before escaping quotes, so \ doesn't double-escape).
        escaped = s.replace("\\", "\\\\")
        # Escape double-quotes.
        escaped = escaped.replace('"', '\\"')
        # Escape newlines/carriage-returns to literal sequences inside the scalar.
        escaped = escaped.replace("\r\n", "\\n")
        escaped = escaped.replace("\n", "\\n")
        escaped = escaped.replace("\r", "\\r")
        return '"' + escaped + '"'
    return s


def _unique_path(path: str) -> str:
    """Return *path* unchanged if it doesn't exist; otherwise insert -2, -3, ...
    before the .md extension until a free slot is found."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while True:
        candidate = f"{base}-{n}{ext}"
        if not os.path.exists(candidate):
            return candidate
        n += 1


def _write_note(path: str, frontmatter: dict, body: str,
                quoted_keys: set | None = None) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["---"]
    for k, v in frontmatter.items():
        fq = quoted_keys is not None and k in quoted_keys
        lines.append(f"{k}: {_yaml_value(v, force_quote=fq)}")
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
    path = _unique_path(os.path.join(vault, CC, "activity", name))
    return _write_note(path, fm, summary)


def write_idea(vault: str, title: str, text: str, source: str,
               project: str = "", status: str = "new",
               created: str | None = None) -> str:
    created = created or _utcnow()
    fm = {"type": "idea", "title": title, "status": status,
          "source": source, "project": project, "created": created}
    name = f"{_stamp(created)}-{_slugify(title)}.md"
    path = _unique_path(os.path.join(vault, CC, "ideas", name))
    return _write_note(path, fm, text, quoted_keys={"title"})


def write_research(vault: str, title: str, body: str,
                   source: str = "deep-research", created: str | None = None) -> str:
    created = created or _utcnow()
    fm = {"type": "research", "title": title, "source": source, "created": created}
    name = f"{_stamp(created)}-{_slugify(title)}.md"
    path = _unique_path(os.path.join(vault, CC, "research", name))
    return _write_note(path, fm, body)


def _parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in text[3:end].strip("\n").splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def sync_skills(vault: str) -> list[str]:
    src = os.path.join(vault, "agentic-os", ".claude", "skills")
    written = []
    for f in sorted(glob.glob(os.path.join(src, "**", "*.md"), recursive=True)):
        fm = _parse_frontmatter(open(f).read())
        slug = fm.get("slug")
        if not slug:
            continue
        stub = {"type": "skill", "slug": slug, "domain": fm.get("domain", ""),
                "name": fm.get("name", ""), "description": fm.get("description", ""),
                "skill_type": fm.get("type", "")}
        body = f"{fm.get('description', '')}\n\nSource: `{os.path.relpath(f, vault)}`"
        written.append(_write_note(os.path.join(vault, CC, "skills", f"{slug}.md"), stub, body))
    return written
