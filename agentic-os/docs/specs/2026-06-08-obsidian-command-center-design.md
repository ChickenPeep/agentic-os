# Obsidian Command Center — Design Spec

**Date:** 2026-06-08
**Status:** Approved design, ready for implementation plan
**Supersedes:** the Next.js dashboard at `agentic-os/dashboard/` (to be retired) and Supabase run-logging.

## 1. Purpose & mental model

The vault **is** the command center. Markdown is the single source of truth (no database,
no web app), matching CLAUDE.md ("No vector DB. Markdown only.") and Chase Hannegan's
"skills > memory > dashboard, Claude reads the vault directly" model.

Skills and the Discord bot write structured markdown notes into the vault. A single
`Command Center.md` note uses the Dataview plugin to roll those into live tables. Gabe
works inside an Obsidian workspace with Claude docked in a terminal and an embedded web
pane. Everything syncs to Obsidian mobile via iCloud; the Discord bot provides remote
"doing" from the phone. Together they fully replace the web dashboard.

## 2. Decisions (locked)

| Decision | Choice |
|---|---|
| Data layer | **Pure markdown in the vault.** Retire Supabase + Next.js dashboard. |
| Dashboard surface | A Dataview note `command-center/Command Center.md` inside Obsidian |
| Sections | Activity feed, Ideas inbox, Skills registry, Active projects |
| Rendering | **Dataview, live** (auto-updates from note frontmatter) |
| Terminal | Claude docked in an Obsidian Terminal-plugin pane |
| Web search | (a) `deep-research` skill writes cited notes **and** (b) an embedded browser pane (Custom Frames) |
| Visual style | Sleek/polished CSS snippet, **Palette A · Midnight Focus**, built with the `frontend-design` skill |
| Ideas location | Structured `command-center/ideas/` board (moved out of the loose `raw/` inbox) |
| Tooling note | `impeccable` is NOT available on the Mac (lives in the NEXUM/Windows repo); use `frontend-design` here, run `impeccable critique` later on Windows |

## 3. Architecture

```
Discord bot ─┐
Pokemon hunter ├─► write markdown notes (via shared lib/notes.py) ─► vault folders
deep-research ─┘                                                       │
                                                                       ▼
                              Obsidian: Command Center.md (Dataview) renders live tables
                              + docked Claude terminal + Custom Frames web pane
                              + command-center.css snippet (Palette A)
```

No process runs "for" the dashboard — it is just a note. Producers write files; Dataview
reads them. This is the isolation boundary: producers know only the note schema (§5), not
the dashboard.

## 4. Folder structure

```
command-center/
  Command Center.md        # the dashboard note (frontmatter: cssclasses: [command-center])
  activity/                # one note per run
       2026-06-08-1430-pokemon-check.md
  ideas/                   # captured ideas, triageable
       2026-06-08-1432-streak-counter.md
  projects/                # one note per active project (hand-maintained or via Claude)
       nexum.md
  research/                # cited findings notes from deep-research
       2026-06-08-d3-camps.md
  skills/                  # generated stub note per skill (mirrors .claude/skills frontmatter)
       pokemon.check-stock.md
.obsidian/snippets/
  command-center.css       # Palette A theme, scoped to .command-center
agentic-os/lib/
  notes.py                 # shared note-writer (frontmatter + body), copied into runtimes at deploy
```

## 5. Note schemas (frontmatter contracts)

**Activity** (`command-center/activity/<UTCdate>-<slug>.md`):
```yaml
type: activity
skill: pokemon.check-stock        # slug of the producing skill
status: success | failure | staged | running
when: 2026-06-08T14:30:00Z        # ISO-8601 UTC
summary: "checked 6, 0 in stock"  # one line
branch: bot/streak-counter        # optional, bot tasks only
```

**Idea** (`command-center/ideas/<UTCdate>-<slug>.md`):
```yaml
type: idea
title: "Add a streak counter to Nexum"
status: new | doing | done
source: discord | manual
project: nexum                     # optional tag
created: 2026-06-08T14:32:00Z
```
Body: the raw idea text + a backlink to the Discord message when source=discord.

**Project** (`command-center/projects/<slug>.md`):
```yaml
type: project
name: Nexum
status: active | paused | done
next: "athlete dashboard MVP"
updated: 2026-06-08
```

**Skill stub** (`command-center/skills/<slug>.md`): Obsidian hides dot-folders, so Dataview
cannot index `agentic-os/.claude/skills/` directly. A sync step mirrors each skill's
frontmatter (`slug`, `domain`, `name`, `description`, `type`) into a visible stub note that
Dataview reads. The canonical source stays `.claude/skills/`; the stubs are generated and
git-ignored or committed as a snapshot (regenerated when skills change).
```yaml
type: skill
slug: pokemon.check-stock
domain: POKEMON
name: check-stock
description: "..."
skill_type: routine
```

## 6. The `Command Center.md` note

Frontmatter `cssclasses: [command-center]` so the CSS snippet scopes only to this note.
Four Dataview blocks (DQL), each a section with a styled card/table:

1. **Activity** — `TABLE skill, status, summary FROM "command-center/activity" SORT when DESC LIMIT 25`
2. **Ideas** — grouped by status: `TABLE title, project, source FROM "command-center/ideas" WHERE status != "done" SORT created DESC` (plus a collapsed "done" list)
3. **Skills** — `TABLE domain, description, skill_type FROM "command-center/skills" SORT domain ASC` (stubs synced from `.claude/skills/`)
4. **Projects** — `TABLE status, next, updated FROM "command-center/projects" SORT updated DESC`

Status values render as colored pills via the CSS snippet (success/done → green `#3FB950`,
staged/doing → accent blue `#2F81F7`, new/running → amber `#D29922`, failure → red).

## 7. Visual design — Palette A · Midnight Focus

Implemented as a scoped Obsidian CSS snippet (`command-center.css`) built with the
`frontend-design` skill. Design tokens:

| Token | Hex | Use |
|---|---|---|
| `--cc-bg` | `#0D1117` | note background |
| `--cc-surface` | `#161B22` | cards / table rows |
| `--cc-line` | `rgba(255,255,255,.07)` | borders / dividers |
| `--cc-text` | `#E6EDF3` | primary text |
| `--cc-muted` | `#8B949E` | secondary text, timestamps |
| `--cc-accent` | `#2F81F7` | links, active pills, highlights |
| `--cc-ok` | `#3FB950` | success/done |
| `--cc-warn` | `#D29922` | new/running |
| `--cc-danger` | `#F85149` | failure |

Style intent: card-styled Dataview tables (rounded surfaces, subtle borders, generous
row spacing), uppercase muted section labels, pill-shaped status badges, system font
stack, one accent color carrying the eye. Scoped to `.command-center` so it never alters
Gabe's normal note-reading experience. Quality bar: clean, minimal, "locked in" — no
visual noise.

## 8. Plumbing (producers)

**`agentic-os/lib/notes.py`** — shared, stdlib-only helper:
- `write_activity(vault, skill, status, summary, when=None, branch=None) -> path`
- `write_idea(vault, title, text, source, project="", status="new", created=None) -> path`
- `sync_skills(vault) -> list[path]` — read every `.claude/skills/**/*.md` frontmatter and
  (re)write `command-center/skills/<slug>.md` stubs so Dataview can index them. Run on
  deploy and whenever skills change.
- Each writes a frontmatter+body markdown file into the correct `command-center/` folder,
  with a filesystem-safe, timestamped, slugified filename. Pure functions, unit-testable.
- Deployed by copying into each runtime dir (pokemon-hunter, discord-bot) via their deploy
  scripts, so launchd runs never import across iCloud.

**Discord bot** (`agentic-os/discord-bot/idealog.py`): replace the Supabase `log_run`/
`update_run`/`runs` calls with `notes.write_idea(...)` (on capture) and
`notes.write_activity(...)` (on task start/finish). `log_idea`'s raw/ write is replaced by
the structured `write_idea`. Drop `COMMAND_CENTER_BOT_SKILL_ID` and Supabase env usage.
The bot's gateway/guard/approval logic is unchanged.

**Pokemon hunter** (`agentic-os/pokemon-hunter/run.sh`): replace the Supabase `runs` POST +
`skills` PATCH with a call that writes an `activity` note (via a tiny Python shim using
`notes.py`) on noteworthy ticks + the hourly heartbeat. Discord stock alerts unchanged.

**deep-research skill:** configure it to save its final cited report into
`command-center/research/<date>-<slug>.md` with `type: research` frontmatter so it surfaces
in the vault (and optionally a Dataview "Recent research" list).

## 9. Obsidian workspace (setup guide)

Rewrite `agentic-os/docs/obsidian-command-center.md` to the final state:
- **Plugins:** Dataview (new, required), Terminal (polyipseity), Custom Frames (Ellpeck).
- **Layout:** main pane = `Command Center.md`; bottom split = Terminal running `claude` in
  the vault; right split = Custom Frames web pane (default to a search engine for the
  embedded web search). Save as an Obsidian **Workspace** so it restores.
- **Mobile:** install Dataview on Obsidian mobile to view the command center on the phone.

## 10. What gets retired

- **`agentic-os/dashboard/`** (Next.js) — deleted from the repo (recoverable in git
  history). The running localhost dev server is stopped.
- **Supabase logging** — removed from the Pokemon hunter and Discord bot. The Supabase
  project is left dormant (nothing writes to it); `supabase-seed.sql` files are removed or
  marked obsolete. No data migration needed (run history is low-value/ephemeral).

## 11. Testing

- `lib/notes.py` unit tests: assert correct folder, filename (timestamped, slugified,
  collision-safe), valid YAML frontmatter, and body content for `write_activity`/`write_idea`.
- Discord bot: existing tests updated so `idealog` is exercised against the new note-writer
  (raw/ + Supabase tests replaced); confirm a logging failure still never raises.
- Pokemon hunter: a manual tick writes a real `activity` note; verify it appears.
- Command center: open `Command Center.md` in Obsidian with Dataview installed; verify all
  four sections render and the CSS snippet applies (pills colored, cards styled).
- CSS scoping: confirm a normal note (without the cssclass) is visually unchanged.

## 12. Scope / phasing

1. `command-center/` structure + `lib/notes.py` (+ tests, incl. `sync_skills`) + skill stubs
   + `Command Center.md` Dataview note + `command-center.css` (Palette A) + a few seed notes
   → **opens in Obsidian immediately.**
2. Repoint the Discord bot (`idealog`) and Pokemon hunter (`run.sh`) to `notes.py`.
3. Wire `deep-research` to write into `command-center/research/`.
4. Rewrite the Obsidian setup guide; delete the Next.js dashboard + Supabase logging.

## 13. Out of scope (future)

- `impeccable critique` polish pass (do on Windows where the skill lives).
- Smart Connections / semantic search (would revisit "markdown only").
- Per-skill "last run" derived column in the registry.
- Telegram front-end (the bot's runner remains separable).
