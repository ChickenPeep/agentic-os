# Obsidian Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the vault itself the command center — skills and the Discord bot write markdown notes that a Dataview note renders as live tables (activity, ideas, skills, projects), styled with a sleek Palette-A CSS snippet — and retire the Next.js dashboard + Supabase logging.

**Architecture:** A shared stdlib helper `lib/notes.py` writes frontmatter notes into `command-center/` folders. `Command Center.md` (DataviewJS + DQL) reads them. A scoped Obsidian CSS snippet themes it. The Discord bot and Pokemon hunter are repointed from Supabase to `notes.py`.

**Tech Stack:** Python 3.9+ (stdlib only), Obsidian + Dataview plugin, CSS, existing `claude` CLI / discord.py / launchd.

**Spec:** `agentic-os/docs/specs/2026-06-08-obsidian-command-center-design.md`

---

## File Structure

```
agentic-os/lib/
  notes.py                 # write_activity, write_idea, write_research, sync_skills (+ helpers)
  tests/
    __init__.py
    conftest.py
    test_notes.py
command-center/
  Command Center.md        # Dataview dashboard (cssclasses: [command-center])
  activity/                # generated run notes (+ one seed)
  ideas/                   # generated idea notes (+ one seed)
  projects/nexum.md        # hand-maintained project note (seed)
  research/.gitkeep        # research reports land here
  skills/                  # generated stubs (sync_skills output)
.obsidian/snippets/
  command-center.css       # Palette A theme, scoped to .command-center
```

Modified: `agentic-os/discord-bot/idealog.py` (+ its tests, conftest, deploy.sh, remove supabase-seed.sql), `agentic-os/discord-bot/bot.py`, `agentic-os/pokemon-hunter/run.sh` (+ new `log_activity.py`, deploy.sh, remove supabase-seed.sql), `agentic-os/docs/obsidian-command-center.md`. Deleted: `agentic-os/dashboard/`.

**Key interfaces (consistent across tasks):**
- `notes.write_activity(vault, skill, status, summary, when=None, branch=None) -> str`
- `notes.write_idea(vault, title, text, source, project="", status="new", created=None) -> str`
- `notes.write_research(vault, title, body, source="deep-research", created=None) -> str`
- `notes.sync_skills(vault) -> list[str]`
- `idealog.capture_idea(vault, text, message_url) -> str`
- `idealog.log_activity(vault, status, summary, branch=None) -> str`

---

## Task 1: notes.py helpers

**Files:**
- Create: `agentic-os/lib/notes.py`
- Create: `agentic-os/lib/tests/__init__.py` (empty)
- Create: `agentic-os/lib/tests/conftest.py`
- Test: `agentic-os/lib/tests/test_notes.py`

- [ ] **Step 1: Create `tests/__init__.py`** (empty file) and **`tests/conftest.py`**

```python
# agentic-os/lib/tests/conftest.py
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 2: Write the failing test**

```python
# agentic-os/lib/tests/test_notes.py
import re
import notes


def test_slugify():
    assert notes._slugify("Add a Streak Counter!") == "add-a-streak-counter"
    assert notes._slugify("   ") == "untitled"
    assert len(notes._slugify("word " * 40)) <= 50


def test_stamp_from_iso():
    assert notes._stamp("2026-06-08T14:30:00Z") == "2026-06-08-1430"
    # bad input falls back to a valid stamp shape
    assert re.match(r"\d{4}-\d{2}-\d{2}-\d{4}", notes._stamp("garbage"))


def test_write_note_roundtrip(tmp_path):
    p = notes._write_note(str(tmp_path / "a" / "n.md"),
                          {"type": "idea", "title": "Hi: there"}, "body text")
    content = open(p).read()
    assert content.startswith("---\n")
    assert 'title: "Hi: there"' in content   # value with ':' gets quoted
    assert "type: idea" in content
    assert content.rstrip().endswith("body text")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd agentic-os/lib && python3 -m pytest -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'notes'`.

- [ ] **Step 4: Write minimal implementation**

```python
# agentic-os/lib/notes.py
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agentic-os/lib && python3 -m pytest -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add agentic-os/lib/notes.py agentic-os/lib/tests/
git commit -m "command-center: notes.py helpers (slugify, stamp, frontmatter writer)"
```

---

## Task 2: notes.write_activity

**Files:**
- Modify: `agentic-os/lib/notes.py`
- Test: `agentic-os/lib/tests/test_notes.py`

- [ ] **Step 1: Write the failing test (append)**

```python
def test_write_activity(tmp_path):
    p = notes.write_activity(str(tmp_path), "pokemon.check-stock", "success",
                             "checked 6, 0 in stock", when="2026-06-08T14:30:00Z")
    assert p.endswith("command-center/activity/2026-06-08-1430-pokemon-check-stock.md")
    c = open(p).read()
    assert "type: activity" in c
    assert "skill: pokemon.check-stock" in c
    assert "status: success" in c
    assert "when: 2026-06-08T14:30:00Z" in c


def test_write_activity_with_branch(tmp_path):
    p = notes.write_activity(str(tmp_path), "command-center.bot", "staged",
                             "built streak counter", when="2026-06-08T14:30:00Z",
                             branch="bot/streak-counter")
    assert 'branch: bot/streak-counter' in open(p).read()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/lib && python3 -m pytest tests/test_notes.py -k activity -q`
Expected: FAIL — `AttributeError: module 'notes' has no attribute 'write_activity'`.

- [ ] **Step 3: Append implementation to `notes.py`**

```python
def write_activity(vault: str, skill: str, status: str, summary: str,
                   when: str | None = None, branch: str | None = None) -> str:
    when = when or _utcnow()
    fm = {"type": "activity", "skill": skill, "status": status,
          "when": when, "summary": summary}
    if branch:
        fm["branch"] = branch
    name = f"{_stamp(when)}-{_slugify(skill)}.md"
    return _write_note(os.path.join(vault, CC, "activity", name), fm, summary)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/lib && python3 -m pytest tests/test_notes.py -k activity -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add agentic-os/lib/notes.py agentic-os/lib/tests/test_notes.py
git commit -m "command-center: notes.write_activity"
```

---

## Task 3: notes.write_idea

**Files:**
- Modify: `agentic-os/lib/notes.py`
- Test: `agentic-os/lib/tests/test_notes.py`

- [ ] **Step 1: Write the failing test (append)**

```python
def test_write_idea(tmp_path):
    p = notes.write_idea(str(tmp_path), "Add a streak counter to Nexum",
                         "It should track consecutive workout days.",
                         source="discord", project="nexum",
                         created="2026-06-08T14:32:00Z")
    assert p.endswith("command-center/ideas/2026-06-08-1432-add-a-streak-counter-to-nexum.md")
    c = open(p).read()
    assert "type: idea" in c
    assert 'title: "Add a streak counter to Nexum"' in c
    assert "status: new" in c
    assert "source: discord" in c
    assert "project: nexum" in c
    assert "consecutive workout days" in c
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/lib && python3 -m pytest tests/test_notes.py -k idea -q`
Expected: FAIL — `AttributeError: ... 'write_idea'`.

- [ ] **Step 3: Append implementation to `notes.py`**

```python
def write_idea(vault: str, title: str, text: str, source: str,
               project: str = "", status: str = "new",
               created: str | None = None) -> str:
    created = created or _utcnow()
    fm = {"type": "idea", "title": title, "status": status,
          "source": source, "project": project, "created": created}
    name = f"{_stamp(created)}-{_slugify(title)}.md"
    return _write_note(os.path.join(vault, CC, "ideas", name), fm, text)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/lib && python3 -m pytest tests/test_notes.py -k idea -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentic-os/lib/notes.py agentic-os/lib/tests/test_notes.py
git commit -m "command-center: notes.write_idea"
```

---

## Task 4: notes.write_research

**Files:**
- Modify: `agentic-os/lib/notes.py`
- Test: `agentic-os/lib/tests/test_notes.py`

- [ ] **Step 1: Write the failing test (append)**

```python
def test_write_research(tmp_path):
    p = notes.write_research(str(tmp_path), "D3 football camps WI",
                             "## Findings\n- thing one\n", created="2026-06-08T09:00:00Z")
    assert p.endswith("command-center/research/2026-06-08-0900-d3-football-camps-wi.md")
    c = open(p).read()
    assert "type: research" in c
    assert "source: deep-research" in c
    assert "thing one" in c
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/lib && python3 -m pytest tests/test_notes.py -k research -q`
Expected: FAIL — `AttributeError: ... 'write_research'`.

- [ ] **Step 3: Append implementation to `notes.py`**

```python
def write_research(vault: str, title: str, body: str,
                   source: str = "deep-research", created: str | None = None) -> str:
    created = created or _utcnow()
    fm = {"type": "research", "title": title, "source": source, "created": created}
    name = f"{_stamp(created)}-{_slugify(title)}.md"
    return _write_note(os.path.join(vault, CC, "research", name), fm, body)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/lib && python3 -m pytest tests/test_notes.py -k research -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add agentic-os/lib/notes.py agentic-os/lib/tests/test_notes.py
git commit -m "command-center: notes.write_research"
```

---

## Task 5: notes.sync_skills

**Files:**
- Modify: `agentic-os/lib/notes.py`
- Test: `agentic-os/lib/tests/test_notes.py`

- [ ] **Step 1: Write the failing test (append)**

```python
def test_sync_skills(tmp_path):
    # fake a skill file under the dot-folder
    skdir = tmp_path / "agentic-os" / ".claude" / "skills" / "pokemon"
    skdir.mkdir(parents=True)
    (skdir / "check-stock.md").write_text(
        "---\nslug: pokemon.check-stock\ndomain: POKEMON\nname: check-stock\n"
        "description: Polls stores for Pokemon stock.\ntype: routine\n---\nbody\n")
    paths = notes.sync_skills(str(tmp_path))
    assert len(paths) == 1
    c = open(paths[0]).read()
    assert paths[0].endswith("command-center/skills/pokemon.check-stock.md")
    assert "type: skill" in c
    assert "slug: pokemon.check-stock" in c
    assert "domain: POKEMON" in c
    assert "skill_type: routine" in c
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agentic-os/lib && python3 -m pytest tests/test_notes.py -k sync_skills -q`
Expected: FAIL — `AttributeError: ... 'sync_skills'`.

- [ ] **Step 3: Append implementation to `notes.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agentic-os/lib && python3 -m pytest -q`
Expected: PASS (all notes tests).

- [ ] **Step 5: Commit**

```bash
git add agentic-os/lib/notes.py agentic-os/lib/tests/test_notes.py
git commit -m "command-center: notes.sync_skills (mirror .claude/skills to visible stubs)"
```

---

## Task 6: command-center folders + seed notes

**Files:**
- Create: `command-center/research/.gitkeep` (empty)
- Create: `command-center/projects/nexum.md`
- Create: `command-center/activity/2026-06-08-1200-pokemon-check-stock.md`
- Create: `command-center/ideas/2026-06-08-1201-example-idea.md`

These seeds make the Dataview note non-empty on first open. Use `notes.py` for the generated ones to guarantee schema-correct frontmatter.

- [ ] **Step 1: Create the seed activity + idea via notes.py**

Run:
```bash
cd "$(git rev-parse --show-toplevel)"
python3 -c "
import sys; sys.path.insert(0, 'agentic-os/lib')
import notes
v='.'
notes.write_activity(v,'pokemon.check-stock','success','checked 6, 0 in stock', when='2026-06-08T12:00:00Z')
notes.write_idea(v,'Example idea — delete me','This is a seed so the board is not empty.', source='manual', project='', created='2026-06-08T12:01:00Z')
print('seeded')
"
```
Expected: prints `seeded`; the two files exist under `command-center/activity/` and `command-center/ideas/`.

- [ ] **Step 2: Create `command-center/projects/nexum.md`**

```markdown
---
type: project
name: Nexum
status: active
next: "athlete dashboard MVP"
updated: 2026-06-08
---

Nexum — D3 football performance tracking platform.
```

- [ ] **Step 3: Create `command-center/research/.gitkeep`** (empty file)

- [ ] **Step 4: Commit**

```bash
git add command-center/
git commit -m "command-center: folder structure + seed notes"
```

---

## Task 7: Generate skill stubs

**Files:**
- Create: `command-center/skills/*.md` (generated)

- [ ] **Step 1: Run sync_skills against the real vault**

Run:
```bash
cd "$(git rev-parse --show-toplevel)"
python3 -c "import sys; sys.path.insert(0,'agentic-os/lib'); import notes; print(len(notes.sync_skills('.')), 'stubs')"
```
Expected: prints `6 stubs` (one per current skill); files appear under `command-center/skills/`.

- [ ] **Step 2: Verify a stub looks right**

Run: `cat "command-center/skills/pokemon.check-stock.md"`
Expected: frontmatter with `type: skill`, `slug`, `domain: POKEMON`, `skill_type`.

- [ ] **Step 3: Commit**

```bash
git add command-center/skills/
git commit -m "command-center: generated skill registry stubs"
```

---

## Task 8: Palette-A CSS snippet

**Files:**
- Create: `.obsidian/snippets/command-center.css`

Use the `frontend-design` skill to refine, but this baseline is complete and polished. Scoped to `.command-center` so it only themes the command center note.

- [ ] **Step 1: Create `.obsidian/snippets/command-center.css`**

```css
/* command-center.css — Palette A · Midnight Focus.
   Scoped to notes with `cssclasses: [command-center]`. */
.command-center {
  --cc-bg:#0D1117; --cc-surface:#161B22; --cc-line:rgba(255,255,255,.07);
  --cc-text:#E6EDF3; --cc-muted:#8B949E; --cc-accent:#2F81F7;
  --cc-ok:#3FB950; --cc-warn:#D29922; --cc-danger:#F85149;
}
.markdown-preview-view.command-center {
  background:var(--cc-bg); color:var(--cc-text);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;
}
.command-center h1 { letter-spacing:-0.02em; }
.command-center h2 {
  font-size:.78rem; text-transform:uppercase; letter-spacing:.08em;
  color:var(--cc-muted); border:0; margin:1.7em 0 .6em;
}
.command-center table.dataview, .command-center .table-view-table {
  width:100%; border-collapse:separate; border-spacing:0; font-size:.86rem;
  background:var(--cc-surface); border:1px solid var(--cc-line);
  border-radius:12px; overflow:hidden;
}
.command-center .table-view-table th {
  background:transparent; color:var(--cc-muted); text-align:left;
  font-weight:600; text-transform:uppercase; font-size:.68rem; letter-spacing:.06em;
  padding:10px 14px; border-bottom:1px solid var(--cc-line);
}
.command-center .table-view-table td {
  padding:10px 14px; border-bottom:1px solid var(--cc-line); color:var(--cc-text);
}
.command-center .table-view-table tr:last-child td { border-bottom:0; }
.command-center a { color:var(--cc-accent); text-decoration:none; }
.command-center .cc-pill {
  display:inline-block; padding:2px 10px; border-radius:999px;
  font-size:.72rem; font-weight:600; line-height:1.5;
}
.command-center .cc-success, .command-center .cc-done {
  background:color-mix(in srgb,var(--cc-ok) 18%,transparent); color:var(--cc-ok);
}
.command-center .cc-staged, .command-center .cc-doing {
  background:color-mix(in srgb,var(--cc-accent) 18%,transparent); color:var(--cc-accent);
}
.command-center .cc-new, .command-center .cc-running {
  background:color-mix(in srgb,var(--cc-warn) 20%,transparent); color:var(--cc-warn);
}
.command-center .cc-failure {
  background:color-mix(in srgb,var(--cc-danger) 20%,transparent); color:var(--cc-danger);
}
```

- [ ] **Step 2: Commit**

```bash
git add ".obsidian/snippets/command-center.css"
git commit -m "command-center: Palette A CSS snippet (scoped)"
```

---

## Task 9: The Command Center.md note

**Files:**
- Create: `command-center/Command Center.md`

Activity + Ideas use DataviewJS (so status renders as colored pills); Skills + Projects use plain DQL.

- [ ] **Step 1: Create `command-center/Command Center.md`**

````markdown
---
cssclasses: [command-center]
---
# Command Center

## Activity
```dataviewjs
const rows = dv.pages('"command-center/activity"')
  .sort(p => p.when, 'desc').slice(0, 25)
  .map(p => [
    p.when ? dv.date(p.when).toFormat("LLL d, HH:mm") : "",
    p.skill,
    `<span class="cc-pill cc-${p.status}">${p.status}</span>`,
    p.summary,
  ]);
dv.table(["When", "Skill", "Status", "Summary"], rows);
```

## Ideas
```dataviewjs
const rows = dv.pages('"command-center/ideas"')
  .where(p => p.status !== "done")
  .sort(p => p.created, 'desc')
  .map(p => [
    p.title,
    `<span class="cc-pill cc-${p.status}">${p.status}</span>`,
    p.project || "",
    p.source,
  ]);
dv.table(["Idea", "Status", "Project", "Source"], rows);
```

## Skills
```dataview
TABLE domain, description, skill_type AS "type"
FROM "command-center/skills"
SORT domain ASC
```

## Projects
```dataview
TABLE status, next, updated
FROM "command-center/projects"
SORT updated DESC
```
````

- [ ] **Step 2: Commit**

```bash
git add "command-center/Command Center.md"
git commit -m "command-center: Command Center.md (Dataview dashboard)"
```

---

## Task 10: Repoint the Discord bot to notes.py

**Files:**
- Rewrite: `agentic-os/discord-bot/idealog.py`
- Rewrite: `agentic-os/discord-bot/tests/test_idealog.py`
- Modify: `agentic-os/discord-bot/tests/conftest.py` (add lib path)
- Modify: `agentic-os/discord-bot/bot.py` (call new idealog API)
- Modify: `agentic-os/discord-bot/deploy.sh` (copy notes.py into runtime)
- Delete: `agentic-os/discord-bot/supabase-seed.sql`

- [ ] **Step 1: Update `tests/conftest.py` to also import the shared lib**

```python
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))                                   # discord-bot/
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "..", "lib"))        # agentic-os/lib/
```

- [ ] **Step 2: Write the failing tests — rewrite `tests/test_idealog.py`**

```python
# agentic-os/discord-bot/tests/test_idealog.py
import os
import idealog


def test_capture_idea_writes_note(tmp_path):
    p = idealog.capture_idea(str(tmp_path), "Add streak counter to Nexum",
                             "https://discord.com/channels/1/2/3")
    assert "command-center/ideas/" in p
    c = open(p).read()
    assert "type: idea" in c
    assert "source: discord" in c
    assert "discord.com/channels/1/2/3" in c


def test_log_activity_writes_note(tmp_path):
    p = idealog.log_activity(str(tmp_path), "success", "built it", branch="bot/x")
    c = open(p).read()
    assert "type: activity" in c
    assert "skill: command-center.bot" in c
    assert "status: success" in c
    assert "branch: bot/x" in c


def test_logging_never_raises(tmp_path, monkeypatch):
    # even if note writing fails, callers must not crash
    monkeypatch.setattr(idealog.notes, "write_idea",
                        lambda *a, **k: (_ for _ in ()).throw(IOError("boom")))
    assert idealog.capture_idea(str(tmp_path), "x", "u") is None
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_idealog.py -q`
Expected: FAIL — `AttributeError`/`ImportError` (old idealog API).

- [ ] **Step 4: Rewrite `idealog.py`**

```python
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
```

- [ ] **Step 5: Run idealog tests to verify they pass**

Run: `cd agentic-os/discord-bot && python3 -m pytest tests/test_idealog.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Update `bot.py` to use the new API.** Make these exact replacements:

Replace the idea-logging + run-start block in `_handle_task`:
```python
    # OLD:
    try:
        idealog.log_idea(text, message.jump_url, RAW_DIR)
    except Exception as e:
        print(f"[idealog raw] {e}")
    started = idealog._utcnow()
    run_id = await asyncio.to_thread(idealog.log_run, started, "running", text)
```
with:
```python
    await asyncio.to_thread(idealog.capture_idea, VAULT, text, message.jump_url)
```

Replace the exception-path logging:
```python
    # OLD:
        if run_id:
            await asyncio.to_thread(idealog.update_run, run_id, "failure", str(e))
        return
```
with:
```python
        await asyncio.to_thread(idealog.log_activity, VAULT, "failure", f"run failed: {e}")
        return
```

Replace the final-status logging:
```python
    # OLD:
    if run_id:
        await asyncio.to_thread(idealog.update_run, run_id, "failure" if result.is_error else "success", summary)
```
with:
```python
    await asyncio.to_thread(
        idealog.log_activity, VAULT,
        "failure" if result.is_error else ("staged" if diffstat else "success"),
        summary[:300], branch if diffstat else None,
    )
```

Then delete the now-unused `RAW_DIR` definition and the `COMMAND_CENTER_BOT_SKILL_ID` reference if present (search the file). Leave `import idealog` (now points to the new module).

- [ ] **Step 7: Verify bot.py compiles and the full bot suite passes**

Run: `cd agentic-os/discord-bot && python3 -m py_compile bot.py && python3 -m pytest -q`
Expected: compiles; all bot tests pass (guard/state/runner/helpers + the 3 new idealog tests).

- [ ] **Step 8: Update `deploy.sh` to copy notes.py into the runtime.** After the `rsync` block, add:
```bash
echo "==> Copying shared notes.py"
cp "$MAC_VAULT/agentic-os/lib/notes.py" "$DEST/notes.py"
```

- [ ] **Step 9: Delete the obsolete seed file**

```bash
git rm agentic-os/discord-bot/supabase-seed.sql
```

- [ ] **Step 10: Commit**

```bash
git add agentic-os/discord-bot/
git commit -m "discord-bot: log ideas/activity to vault notes (drop Supabase)"
```

---

## Task 11: Repoint the Pokemon hunter to notes.py

**Files:**
- Create: `agentic-os/pokemon-hunter/log_activity.py`
- Modify: `agentic-os/pokemon-hunter/run.sh`
- Modify: `agentic-os/pokemon-hunter/deploy.sh`
- Delete: `agentic-os/pokemon-hunter/supabase-seed.sql`

- [ ] **Step 1: Create `log_activity.py`** (thin shim run by run.sh)

```python
#!/usr/bin/env python3
"""Write a command-center activity note for a pokemon check tick.

Usage: log_activity.py <status> <summary>
Vault is taken from $VAULT_PATH (set by run.sh). Best-effort; never fails the tick.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import notes
    vault = os.environ.get("VAULT_PATH", "")
    status = sys.argv[1] if len(sys.argv) > 1 else "success"
    summary = sys.argv[2] if len(sys.argv) > 2 else ""
    if vault:
        notes.write_activity(vault, "pokemon.check-stock", status, summary)
except Exception as e:
    print(f"[log_activity] {e}")
```

- [ ] **Step 2: Modify `run.sh`** — replace the Supabase logging block (the `if [ "$NOTEWORTHY" -eq 1 ] && [ -n "${SUPABASE_URL:-}" ] ...` block with the two `curl` calls) with:

```bash
if [ "$NOTEWORTHY" -eq 1 ]; then
  STATUS="success"; [ "$EXIT" -ne 0 ] && STATUS="failure"
  VAULT_PATH="$MAC_VAULT" python3 "$DIR/log_activity.py" "$STATUS" "$SUMMARY" || true
fi
```
(Keep the existing `NOTEWORTHY`/heartbeat logic above it unchanged. `$MAC_VAULT` is already defined in run.sh; if not, add `MAC_VAULT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"` near the top.)

- [ ] **Step 3: Modify `deploy.sh`** — after the `rsync` block, add:
```bash
echo "==> Copying shared notes.py"
cp "$MAC_VAULT/agentic-os/lib/notes.py" "$DEST/notes.py"
```

- [ ] **Step 4: Syntax-check the shell + shim**

Run: `cd agentic-os/pokemon-hunter && bash -n run.sh && bash -n deploy.sh && python3 -m py_compile log_activity.py && echo OK`
Expected: `OK`.

- [ ] **Step 5: Smoke-test the shim writes a note**

Run:
```bash
cd "$(git rev-parse --show-toplevel)"
cp agentic-os/lib/notes.py agentic-os/pokemon-hunter/notes.py
VAULT_PATH="$(pwd)" python3 agentic-os/pokemon-hunter/log_activity.py success "smoke test"
ls command-center/activity/ | tail -1
rm agentic-os/pokemon-hunter/notes.py   # runtime-only copy, not committed
```
Expected: a new activity note listed. (The `notes.py` copy in pokemon-hunter is git-ignored at runtime; do not commit it — it's added by deploy.sh.)

- [ ] **Step 6: Add `notes.py` to pokemon-hunter/.gitignore and discord-bot/.gitignore**

Append a line `notes.py` to both `agentic-os/pokemon-hunter/.gitignore` and `agentic-os/discord-bot/.gitignore` so the deploy-copied shared lib is never committed into the runtime packages.

- [ ] **Step 7: Delete the obsolete seed file + commit**

```bash
git rm agentic-os/pokemon-hunter/supabase-seed.sql
git add agentic-os/pokemon-hunter/ command-center/
git commit -m "pokemon-hunter: log activity to vault notes (drop Supabase)"
```

---

## Task 12: Rewrite the Obsidian setup guide

**Files:**
- Rewrite: `agentic-os/docs/obsidian-command-center.md`

- [ ] **Step 1: Replace the file contents**

````markdown
# Obsidian Command Center — setup

The vault IS the command center. Skills + the Discord bot write markdown notes;
`command-center/Command Center.md` renders them as live tables. Claude runs in a docked
terminal; an embedded web pane sits on the right. No web app, no database.

## 1. Plugins (Settings → Community plugins → Browse)

| Plugin | ID | Role |
|---|---|---|
| **Dataview** | `dataview` | Renders the command center tables. **Required.** Enable "Enable JavaScript Queries" in its settings (the Activity/Ideas tables use DataviewJS). |
| **Terminal** (polyipseity) | `terminal` | Claude docked in a bottom pane. |
| **Custom Frames** (Ellpeck) | `obsidian-custom-frames` | The embedded web-search pane. |

Enable the **Snippets** toggle: Settings → Appearance → CSS snippets → refresh → turn on
`command-center`.

## 2. Layout
1. Open `command-center/Command Center.md` in the main pane.
2. Terminal: Command palette → *Terminal: Open integrated terminal* → drag the tab to the
   bottom split → `cd` to the vault root → run `claude`.
3. Custom Frames: add a frame (URL `https://www.perplexity.ai` or your search engine) →
   open it in the right split. This is the embedded web search.
4. Save the layout: Workspaces core plugin → Save (e.g. "Command Center").

## 3. Phone
Install Obsidian mobile + the Dataview plugin and open `Command Center.md`. The vault
syncs via iCloud, so activity/ideas/projects show on your phone. Use the Discord bot to
actually run things remotely.

## 4. How results show up
- **Skills / Pokemon hunter / bot** → write notes into `command-center/activity/` and
  `command-center/ideas/` (via `agentic-os/lib/notes.py`).
- **Research:** ask Claude (terminal or bot) to research; it runs the `deep-research`
  skill and saves the cited report into `command-center/research/` (`notes.write_research`).
- **Skills registry:** run `python3 -c "import sys;sys.path.insert(0,'agentic-os/lib');import notes;notes.sync_skills('.')"` after adding/editing a skill to refresh `command-center/skills/`.
````

- [ ] **Step 2: Commit**

```bash
git add agentic-os/docs/obsidian-command-center.md
git commit -m "docs: rewrite Obsidian command center setup for the markdown/Dataview model"
```

---

## Task 13: Retire the Next.js dashboard + Supabase logging

**Files:**
- Delete: `agentic-os/dashboard/`

- [ ] **Step 1: Stop the running localhost dev server**

Run: `pkill -f "next dev" 2>/dev/null; pkill -f "next-server" 2>/dev/null; echo "stopped"`
Expected: `stopped` (no error if nothing was running).

- [ ] **Step 2: Delete the dashboard**

```bash
git rm -r agentic-os/dashboard
```

- [ ] **Step 3: Confirm no remaining references to the dashboard or Supabase logging in active code**

Run: `grep -rniE "rest/v1/runs|supabase" agentic-os --include=*.sh --include=*.py | grep -v node_modules`
Expected: no matches in `pokemon-hunter/run.sh` or `discord-bot/` (only possibly in docs/specs, which is fine).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "command-center: retire Next.js dashboard (replaced by Obsidian/markdown)"
```

---

## Task 14: Full verification + manual Obsidian acceptance

**Files:** none (verification only)

- [ ] **Step 1: Run all Python suites**

Run:
```bash
cd "$(git rev-parse --show-toplevel)"
(cd agentic-os/lib && python3 -m pytest -q)
(cd agentic-os/discord-bot && python3 -m pytest -q)
```
Expected: all pass.

- [ ] **Step 2: Confirm the command center renders data**

Run: `ls command-center/activity command-center/ideas command-center/skills command-center/projects`
Expected: each has at least one `.md` file.

- [ ] **Step 3: (Gabe) Obsidian acceptance**
  - Install Dataview (enable JavaScript Queries), Terminal, Custom Frames; enable the
    `command-center` CSS snippet.
  - Open `command-center/Command Center.md`: all four sections render; status shows as
    colored pills; the theme is dark/Palette-A and styled as cards.
  - Open any normal note (no `command-center` cssclass): confirm it looks unchanged.
  - Dock the terminal, run `claude`; add the Custom Frames web pane; save the Workspace.

- [ ] **Step 4: (Gabe, optional) Live producer check**
  - Re-deploy the hunter (`bash agentic-os/pokemon-hunter/deploy.sh`) and bot (after its
    Discord setup); confirm new `command-center/activity/` notes appear after a tick / bot task.

- [ ] **Step 5: Final commit (if acceptance fixes were needed)**

```bash
git add -A && git commit -m "command-center: acceptance fixes" || echo "nothing to commit"
```

---

## Self-Review Notes (author)

- **Spec coverage:** data layer = markdown (all tasks); folders/schemas (T1–T6); Command
  Center.md 4 sections (T9); Dataview live + DataviewJS pills (T9); Palette-A scoped CSS
  (T8); skills registry via stubs to dodge dot-folder hiding (T5/T7/T9); notes.py shared +
  copied by deploys (T1–T5, T10, T11); repoint bot (T10) + hunter (T11); research wiring
  (write_research T4 + convention in guide T12); Obsidian workspace/terminal/web pane (T12);
  retire dashboard + Supabase (T10/T11/T13); testing (T1–T5, T10, T14); phone (T12).
- **Placeholder scan:** none — every code/CSS/markdown block is complete.
- **Name consistency:** `write_activity/write_idea/write_research/sync_skills`,
  `capture_idea/log_activity`, cssclass `command-center`, pill classes `cc-<status>`,
  folder `command-center/` used identically across tasks.
- **Known dependency:** the polished look requires the Dataview plugin (incl. JS queries)
  installed by Gabe (T12/T14) — code can't install it; flagged in the guide and acceptance.
