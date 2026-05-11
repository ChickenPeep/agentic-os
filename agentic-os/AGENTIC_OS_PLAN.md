# Agentic OS — Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personal Agentic OS on top of an Obsidian vault, with a Mac mini as the always-on execution brain, a Next.js dashboard on Cloudflare Pages as the control surface, and n8n cloud as the webhook hub — so every repeatable task is one click away.

**Architecture:** Skills/routines/agents live in the vault and are registered in Supabase. The dashboard (Cloudflare) and Telegram bot send webhook calls to n8n cloud, which forwards to the Mac mini over Tailscale. The Mac mini runs Claude Code to execute skills and writes results back to Supabase and the vault.

**Tech Stack:** Obsidian vault (Markdown), Claude Code CLI, Supabase (Postgres), n8n cloud (webhook hub), Next.js 14 App Router, Cloudflare Pages, Tailscale, Telegram Bot API, launchd (Mac cron), Node.js/Express (Mac execution endpoint), GitHub (CI/CD).

---

## Foundational OS structure — 4 active domains

_Set 2026-05-11. The OS is built for 4 domains where Gabe operates daily. Other wiki folders persist for note-storage but aren't OS domains and aren't part of the skill build. Additions to this domain set happen on-demand when a real need surfaces — not as a queued backlog._

### The 4 OS domains

1. **MEMORY** — vault, wiki, capture. Foundation, always on.
2. **PRODUCTIVITY** — calendar brief, daily focus, weekly review.
3. **NEXUM** — full product lifecycle:
   - Engineering: schema, features, deploys, code review
   - Customer feedback: coach/player conversations, feedback loops
   - GTM: positioning, outreach to D3 programs, pricing exploration
   - Polish + portfolio: presentation quality, demo flows
4. **GROWTH & BUSINESS** — combined daily learning + business expansion:
   - Daily learning routine: surfaces ONE high-signal YouTube video per day relevant to Nexum, AI building, or consulting. Also tracks Claude/Anthropic and OpenAI/ChatGPT updates daily.
   - Idea generation: weekly skill that produces new app ideas, new AI uses for Nexum, new consulting angles.
   - Consulting prep: builds out positioning, client discovery patterns, deliverable templates for small business consulting.
   - Sales/outreach: cold email templates, follow-up cadences, lead capture.

### Additional wiki folders (not OS domains, not skill-tracked)

school, football, bible-study, side-projects, personal-ops, consulting (campus AI consulting — distinct from GROWTH & BUSINESS consulting prep), ai-systems

These receive notes via raw-triage SECONDARY routing when content clearly belongs there. No active skill build planned. If a real need emerges later, a folder can be promoted to OS-domain status (own dashboard column, skill folder, classifier PRIMARY slot).

### OS skill count target

| Domain | Target |
|---|---|
| MEMORY | 3–4 skills |
| PRODUCTIVITY | 3–4 skills |
| NEXUM | 6–8 skills (engineering / customer feedback / GTM / polish + portfolio) |
| GROWTH & BUSINESS | 5–7 skills (daily learning / idea generation / consulting prep / sales+outreach) |

**Total: ~20 skills.** The OS is "real" when these are built and running.

### Phase 3 build order

MEMORY → PRODUCTIVITY → NEXUM → GROWTH & BUSINESS.

### Pre-Phase-3 step — Context dump session (NEW)

A dedicated 45–60 minute interview captures Gabe's background/work/goals/voice/projects/approach as durable wiki articles in `wiki/personal/`. The interview is itself a skill: `memory.context-dump`. Runs after Phase 2.1 polish; precedes Phase 3 first-domain interview.

---

## Conventions & Decisions

### Host decision matrix

| Criterion | Mac local (`launchd`) | n8n cloud |
|---|---|---|
| Needs access to vault files | YES → mac | |
| Needs access to local Claude Code | YES → mac | |
| Needs cloud-only context (SaaS webhooks, no Mac dependency) | | YES → cloud |
| Routine should run even when Mac is off | | YES → cloud |
| Default | **mac** | exception |

### Naming conventions

- Skill files: `agentic-os/.claude/skills/<domain>/<slug>.md`
- Routine plists: `~/Library/LaunchAgents/com.agenticos.<domain>.<slug>.plist`
- Webhook URLs: `https://n8n.cloud/webhook/<domain>-<slug>`
- Supabase skill slug: `<domain>.<slug>` (e.g. `memory.raw-triage`)

### Vault paths (cross-platform)

| Machine | Path |
|---|---|
| Mac mini (canonical) | `/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault` |
| Windows desktop | `C:\Users\gabri\iCloudDrive\agentic-os-vault` |
| Obsidian opens | the root of the above on each machine |

### Mac mini execution endpoint

A small **Express (Node.js)** server running on the Mac mini, listening on port **4242** (internal only, not exposed to internet). Tailscale makes it reachable from n8n cloud at `http://<tailscale-ip>:4242`. Each POST triggers `claude --print "<prompt>"` via `child_process.exec`. Logs stdout/stderr back in the n8n response.

---

## Supabase Schema

```sql
-- skills: one row per codified skill/routine/agent
create table skills (
  id           uuid primary key default gen_random_uuid(),
  domain       text not null,          -- MEMORY, NEXUM, etc.
  name         text not null,
  slug         text not null unique,   -- domain.slug
  description  text,
  type         text not null check (type in ('skill','routine','agent')),
  webhook_url  text,
  status       text not null default 'active' check (status in ('active','paused','retired')),
  host         text not null default 'mac' check (host in ('mac','cloud')),
  created_at   timestamptz not null default now(),
  last_run_at  timestamptz,
  run_count    integer not null default 0
);

-- runs: one row per execution
create table runs (
  id            uuid primary key default gen_random_uuid(),
  skill_id      uuid references skills(id),
  started_at    timestamptz not null default now(),
  ended_at      timestamptz,
  status        text not null default 'running' check (status in ('running','success','failure')),
  output        text,
  triggered_by  text check (triggered_by in ('dashboard','telegram','cron','plan_triage','manual')),
  host          text check (host in ('mac','cloud'))
);

-- plans: raw captures triaged by AI
create table plans (
  id               uuid primary key default gen_random_uuid(),
  raw_text         text not null,
  triaged_at       timestamptz,
  action_taken     text,               -- 'new_skill','wiki_article','nexum_ticket','calendar','deferred','none'
  target_skill_id  uuid references skills(id),
  status           text not null default 'pending' check (status in ('pending','triaged','done')),
  wiki_article_path text
);

-- wiki_articles: index of vault wiki entries
create table wiki_articles (
  id               uuid primary key default gen_random_uuid(),
  domain           text not null,
  path             text not null unique,   -- relative to vault root, e.g. wiki/nexum/db-schema.md
  title            text not null,
  summary          text,
  source_raw_files text[],
  updated_at       timestamptz not null default now()
);

-- status_counts: dashboard header numbers
create view status_counts as
select
  count(*) filter (where status = 'active')  as active_skills,
  count(*) filter (where status = 'paused')  as paused_skills,
  count(*) filter (where status = 'retired') as retired_skills,
  count(*) filter (where type  = 'routine')  as routines,
  count(*) filter (where type  = 'agent')    as agents
from skills;
```

---

## Phase 0 — Plan document ✅

This document. Review and approve before Phase 1.

**Checklist:**
- [ ] Gabriel reviews this document
- [ ] Gabriel approves or requests changes
- [ ] Move to Phase 1

---

## Phase 1 — Memory + Mac mini foundation

**Goal:** Vault structure created, CLAUDE.md written, Supabase schema deployed, Mac mini execution endpoint running, n8n base workflow wired.

**Prerequisite info needed from Gabriel:**
- Mac's Tailscale IP
- Supabase project URL + anon key + service role key
- Anthropic API key
- GitHub repo URL (will be created or already exists)
- Cloudflare account email
- n8n cloud base URL (the cloud instance URL)

### Task 1.1 — Vault folder structure

**Files to create (all at vault root):**
```
CLAUDE.md
raw/.gitkeep
wiki/_master-index.md
wiki/nexum/_index.md
wiki/consulting/_index.md
wiki/school/_index.md
wiki/football/_index.md
wiki/bible-study/_index.md
wiki/side-projects/_index.md
wiki/personal-ops/_index.md
wiki/ai-systems/_index.md
output/.gitkeep
agentic-os/.claude/skills/.gitkeep
agentic-os/.claude/routines/.gitkeep
agentic-os/.claude/agents/.gitkeep
agentic-os/.claude/memory/.gitkeep
agentic-os/dashboard/  (Next.js, Phase 2)
agentic-os/n8n-workflows/  (exported JSON, Phase 4)
agentic-os/STATUS.md
```

- [ ] Create all folders and placeholder files listed above (Claude Code does this from the Windows machine where the vault is open)
- [ ] Verify iCloud sync shows them on the Mac

### Task 1.2 — Write CLAUDE.md

**File:** `CLAUDE.md` at vault root

- [ ] Write the following content exactly:

```markdown
# Gabriel Torres — Agentic OS Context

## Who I am
- Gabriel Torres (Gabe), sophomore Information Systems major at UW Oshkosh
- Internal AI Consultant on campus (uwosh.edu, Copilot + Gemini approved)
- Building Nexum — D3 football performance tracking platform
- Lead a college Bible study, play football at UWO

## Stack
VS Code, Claude Code, Supabase, n8n, Cloudflare, GitHub, Obsidian, Tailscale

## Voice & output rules
- Direct, plain language
- No em-dashes in any drafted external output
- Copy-paste ready

## Machines
| Machine | Role | Path |
|---|---|---|
| Mac mini | **Canonical execution host** — always on, runs Claude Code, hosts vault | `/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault` |
| Windows desktop | Primary dev, Nexum work | `C:\Users\gabri\iCloudDrive\agentic-os-vault` |
| Dell Inspiron 14 | Mobile work | iCloud sync |
| Phone | Telegram remote, Obsidian read | |

All machines on Tailscale. Vault syncs via iCloud Drive.

## Vault map
```
agentic-os-vault/
├── CLAUDE.md              ← this file
├── raw/                   ← inbox (triage within 7 days)
├── wiki/                  ← LLM-maintained domain knowledge
│   ├── _master-index.md
│   ├── nexum/
│   ├── consulting/
│   ├── school/
│   ├── football/
│   ├── bible-study/
│   ├── side-projects/
│   ├── personal-ops/
│   └── ai-systems/
├── output/                ← artifacts, reports, decks
└── agentic-os/            ← the OS itself
    ├── .claude/           ← skills, routines, agents, memory
    ├── dashboard/         ← Next.js app
    ├── n8n-workflows/     ← exported JSON
    └── STATUS.md
```

## Memory rules
- Skills that produce knowledge → write to wiki/, update _index.md + _master-index.md
- Skills that produce external artifacts → output/
- raw/ is ephemeral. Triage within ~7 days.
- No vector DB. Markdown only. _master-index.md is the entry point.
- CLAUDE.md is the source of truth for my context. Update when context changes.

## Domains
MEMORY, PRODUCTIVITY, NEXUM, CONSULTING, SCHOOL, FOOTBALL, BIBLE STUDY, SIDE PROJECTS, PERSONAL OPS

## Abstraction levels
- SKILL: repeatable, clear inputs/outputs, has webhook + dashboard card
- ROUTINE: skill on a schedule (default: Mac launchd)
- AGENT: multi-step autonomous workflow

## Execution host default
Mac mini is the canonical host. Only use n8n cloud cron when the routine needs cloud-only context or must run when Mac is off.
```

- [ ] Commit file

### Task 1.3 — Supabase schema

- [ ] Open Supabase dashboard, select or create project `agentic-os`
- [ ] Go to SQL Editor, paste and run the full schema from the "Supabase Schema" section above
- [ ] Verify all 4 tables and 1 view appear in the Table Editor
- [ ] Copy the project URL and anon key — needed for dashboard env vars

### Task 1.4 — Mac mini execution endpoint

This is a Node.js/Express service that listens for POST requests from n8n and runs Claude Code.

**File to create on Mac:** `~/agentic-os-server/server.js`

- [ ] SSH into Mac mini (or open terminal on it) and run:
```bash
mkdir ~/agentic-os-server && cd ~/agentic-os-server
npm init -y
npm install express
```

- [ ] Create `~/agentic-os-server/server.js` with this content:

```javascript
const express = require('express');
const { exec } = require('child_process');
const app = express();
app.use(express.json());

const API_KEY = process.env.AGENTIC_OS_API_KEY; // set in env before starting

app.post('/run', (req, res) => {
  const { prompt, skill_id, triggered_by } = req.body;
  if (!prompt) return res.status(400).json({ error: 'prompt required' });

  // Simple bearer token auth
  const auth = req.headers.authorization;
  if (!auth || auth !== `Bearer ${API_KEY}`) {
    return res.status(401).json({ error: 'unauthorized' });
  }

  const vaultPath = process.env.VAULT_PATH ||
    '/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault';

  // Run claude in print mode (non-interactive, returns output)
  const cmd = `cd "${vaultPath}" && claude --print "${prompt.replace(/"/g, '\\"')}"`;

  exec(cmd, { timeout: 120000, maxBuffer: 1024 * 1024 * 10 }, (err, stdout, stderr) => {
    if (err) {
      return res.status(500).json({ error: err.message, stderr });
    }
    res.json({ output: stdout, stderr });
  });
});

app.get('/health', (req, res) => res.json({ status: 'ok' }));

const PORT = process.env.PORT || 4242;
app.listen(PORT, '0.0.0.0', () => console.log(`agentic-os server on :${PORT}`));
```

- [ ] Create a `.env` file (never committed):
```
AGENTIC_OS_API_KEY=<generate a random 32-char hex string>
VAULT_PATH=/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault
PORT=4242
```

- [ ] Install `dotenv` and update server to load it: `npm install dotenv`, add `require('dotenv').config();` as first line

- [ ] Test locally:
```bash
node server.js &
curl -X POST http://localhost:4242/health
# expected: {"status":"ok"}
```

- [ ] Keep the server running. Note the Mac's Tailscale IP (`tailscale ip -4`).

- [ ] Test from Windows machine over Tailscale:
```powershell
$body = @{ prompt = "echo hello from claude" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://<tailscale-ip>:4242/run" `
  -Method POST -Body $body -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer <your-api-key>" }
```

### Task 1.5 — Keep server alive with launchd

**File on Mac:** `~/Library/LaunchAgents/com.agenticos.server.plist`

- [ ] Create the plist:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.agenticos.server</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/node</string>
    <string>/Users/gabri/agentic-os-server/server.js</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>AGENTIC_OS_API_KEY</key>
    <string>REPLACE_WITH_KEY</string>
    <key>VAULT_PATH</key>
    <string>/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault</string>
    <key>PORT</key>
    <string>4242</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/gabri/agentic-os-server/stdout.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/gabri/agentic-os-server/stderr.log</string>
</dict>
</plist>
```

- [ ] Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.agenticos.server.plist
launchctl list | grep agenticos
```

- [ ] Verify it survives a restart (optional test: `sudo reboot`, then check after boot)

### Task 1.6 — n8n base workflow

**Goal:** n8n cloud receives a webhook, looks up the skill in Supabase, POSTs to Mac, logs the run.

- [ ] In n8n cloud, create a new workflow called `agentic-os-base`
- [ ] Add nodes in order:

```
[Webhook trigger]
  → path: /skill-run
  → method: POST
  → body: { skill_slug, prompt, triggered_by }

[Supabase node: get skill]
  → operation: SELECT from skills WHERE slug = {{$json.skill_slug}}
  → capture: id, webhook_url, host, status

[IF node: skill active?]
  → condition: {{$json.status}} == "active"
  → true branch: continue
  → false branch: respond 400 "skill not active"

[HTTP Request node: call Mac]
  → URL: http://<tailscale-ip>:4242/run
  → method: POST
  → headers: Authorization: Bearer <api-key>
  → body: { prompt: {{$json.prompt}}, skill_id: {{$json.id}}, triggered_by: {{$json.triggered_by}} }

[Supabase node: insert run]
  → operation: INSERT into runs
  → data: { skill_id, started_at: now, ended_at: now, status: "success", output, triggered_by, host: "mac" }

[Respond to Webhook]
  → body: { output, run_id }
```

- [ ] Activate the workflow and copy the webhook URL
- [ ] Test end-to-end: POST to the n8n webhook with a real skill_slug, see output

---

## Phase 1.6 — Stable named Cloudflare tunnel (added during execution)

**Goal:** Replace the Cloudflare quick tunnel (URL rotates on every cloudflared restart) with a named tunnel bound to a stable subdomain `n8n.<custom-domain>`. Required before Phase 4 (Telegram).

**Blocked on:** GitHub Student Developer Pack approval → free `.me` domain on Namecheap → DNS migration to Cloudflare.

**Steps when unblocked:** see `agentic-os/n8n-self-host/SETUP.md` "Upgrading to a stable tunnel".

---

## Phase 2 — Dashboard MVP (sub-plan TBD)

**Goal:** Next.js app on Cloudflare Pages with domain columns (one per active domain in CLAUDE.md), skill cards, plan/capture pane, run history, wiki search.

**Sketch:**
- `agentic-os/dashboard/` — Next.js 14 App Router
- Supabase JS client (anon key) for skill cards and run history
- Each card: name, domain chip, type badge, "Run" button → POST to skill's webhook_url
- Plan/capture pane: textarea → POST to n8n `/plan-triage` webhook
- Cloudflare Pages: connect GitHub repo, set env vars, auto-deploy on push

**When to plan in detail:** After Phase 1 is live and approved.

---

## Phase 3 — Domain interview loop (sub-plan TBD)

**Build order:** MEMORY → PRODUCTIVITY → NEXUM → GROWTH & BUSINESS.

**Pre-step:** before the first domain interview, run the **context dump session** (`memory.context-dump` skill, 45–60 min, captures Gabe's background/work/goals/voice/projects → wiki articles in `wiki/personal/`). This grounds every subsequent skill.

**Per domain scaffold:**
1. Interview (light mode, 3–5 items max)
2. For each item: write SKILL.md → `INSERT into skills` → register in Supabase (so the dashboard Run button picks it up) → drop wiki stub
3. If routine: write launchd plist
4. Live for a week before next domain

**When to plan in detail:** After Phase 2.1 polish ships AND the context dump session runs.

---

## Phase 4 — Telegram remote (sub-plan TBD)

- n8n bot workflow receives `/run <slug>` or `/plan <text>`
- Same webhooks as dashboard
- `/plan` exposes the plan/capture pane as a text reply

**When to plan in detail:** After first domain (Phase 3 first pass) is live.

---

## Phase 5 — n8n local migration (optional)

- Docker on Mac mini
- Move workflows from n8n cloud to local
- Single evening of work
- Trigger: when routine volume justifies the ops cost

---

## Phase 6 — Status + iteration (sub-plan TBD)

- `STATUS.md` auto-updated from Supabase (weekly routine)
- Weekly review skill: usage, failures, retirements
- Wiki health skill: stale articles, orphaned raw/ files

---

## Current status

_Last updated: 2026-05-11_

| Phase | Status | Notes |
|---|---|---|
| 0 — Plan document | DONE | Approved |
| 1 — Memory + Mac foundation | DONE | Mac endpoint :4242, n8n self-hosted :5678, launchd services live, Supabase schema deployed, skills registered |
| 1.5 — n8n self-host migration | DONE | n8n running locally on Mac mini; cloud instance retired |
| 1.6 — Stable named tunnel | BLOCKED | Waiting on GitHub Student Pack → domain → Cloudflare DNS |
| 2 — Dashboard MVP v1 | LIVE | https://agentic-os-40r.pages.dev — public; reads from Supabase via anon+RLS; Run button works for `memory.echo-test` end-to-end |
| 2.1 — Dashboard polish | NOT STARTED | `skills.prompt` column + fire-and-forget /api/run (so all skills work from Run button, not just echo-test) + plan/capture pane + wiki search |
| 3 — Domain interviews | IN PROGRESS | MEMORY domain scaffolded (echo-test + raw-triage + context-dump live). Build order: MEMORY → PRODUCTIVITY → NEXUM → GROWTH & BUSINESS. Additional wiki folders (school, football, etc.) are not OS domains and have no active skill build. |
| 3 pre-step — Context dump session | NOT STARTED | `memory.context-dump` skill registered; runs after Phase 2.1 ships. |
| 4 — Telegram remote | NOT STARTED | Blocked until Phase 1.6 stable tunnel |
| 5 — n8n local migration | DONE | Subsumed by Phase 1.5 |
| 6 — Status + iteration | NOT STARTED | |

---

## Open questions / decisions needed

1. **Mac's Tailscale IP** — needed to wire n8n → Mac endpoint
2. **Supabase project** — existing or new? URL + keys needed
3. **GitHub repo** — where does `agentic-os/` code live? New repo? Existing?
4. **n8n cloud URL** — your cloud instance base URL
5. **API key for Mac endpoint** — generate together in Phase 1
6. **Nested vault folder** — there's an `agentic-os-Vault/` subfolder in the vault root with a default Welcome note. Should we delete it and treat the root as the vault?
