# Agentic OS — Session Handoff

_Update this file at the end of every build session._

---

## Last updated: 2026-05-11 (laptop handoff — Mac session ending mid-day; Gabe continuing on laptop. Vision captured: Telegram conversational interface + Task layer + Proactive outreach. See "🔮 Vision captured this session" below.)

## Current phase: Phase 1 + 1.5 + 2 v1 SHIPPED. Domain restructure to 4 foundational OS domains SHIPPED (commit `8e43da5`, dashboard verified showing 4 columns live). `memory.context-dump` skill created (SKILL.md + Supabase row `6722d3ce-fb37-4c74-b53e-f29df6d5d43b`). Vault on GitHub (private). Cloudflare Pages live at https://agentic-os-40r.pages.dev. Pending: **Phase 2.1** (skills.prompt column + fire-and-forget /api/run) OR **context dump session** (`memory.context-dump`, 45-60 min) — either can run next.

---

## 🔮 Vision captured this session (2026-05-11) — forward-looking, NOT to build now

Gabe surfaced these ideas mid-session. They've been integrated into `AGENTIC_OS_PLAN.md` as Phase 4 reframe + new Phase 5 + new Phase 6. **None of this is on the critical path right now** — the foundation (Phase 2.1 + context dump + Phase 3 first domains) ships before any of it. Captured here so the laptop session and future sessions have the full picture.

### Phase 4 — Telegram becomes a full conversational interface (REFRAMED, not slash commands)

The original Phase 4 was a slash-command bot (`/run <slug>`, `/plan <text>`). Reframed: **Telegram is a primary chat surface for talking to the OS — like talking to Claude on iMessage.**
- Natural-language input. Bot captures intent, asks follow-up questions when ambiguous, routes to the right action (skill / task / wiki write / direct reply).
- Conversation state stored in Supabase (`conversations` table — message history per thread, last intent, pending follow-ups).
- **Proactive too:** morning briefs at 7am, skill completion pings, due-task reminders all push to Telegram via the same channel.
- Blocked on: Phase 1.6 stable named tunnel (Telegram needs a non-rotating URL) + Phase 5 task layer + at least 2-3 real skills.

### Phase 5 — Task layer + dashboard-as-task-planner (NEW PHASE)

Reshapes the dashboard from "skill registry" to "task planner where skills are tools you invoke on tasks."
- New `tasks` table in Supabase: title, category, subcategory, status, due_date, related_skill_slugs[], related_wiki_paths[], source (dashboard/telegram/skill/manual).
- New `task_runs` join table: links a `runs` row to a `tasks` row so we can see "this skill run happened in the context of task X."
- Tasks land in Supabase three ways:
  1. **Telegram** (Phase 4 conversational): "remind me to follow up with coach J Tuesday" → task row
  2. **Dashboard**: explicit "Add task" UI
  3. **Skill outputs**: a skill emits task suggestions (raw-triage finds a TODO → proposes a task)
- **Dashboard reorg:** instead of "4 domain columns of floating skill cards," the dashboard becomes a task planner organized by category (Personal Ops, Nexum, Internship as a cross-cutting category, etc.) with **sub-categories auto-derived from `wiki/<domain>/<subfolder>/` structure**.
- **Skill cards attach to tasks.** You don't click a floating Run button — you open a task and click Run on a skill within that task's context. The task's metadata (title, related wiki, recent runs) gets passed into the skill prompt. Output gets attached back to the task.
- "Quick Run" pane preserved for skills not yet attached to a task (secondary UX, not primary).
- Blocked on: Phase 2.1 polish + at least 5+ skills across 2+ domains.

### Phase 6 — Proactive outreach + routines (NEW PHASE, separated from Telegram)

Distinct from Phase 4 because it's scheduled push (vs interactive chat) and depends on Phase 5 task data.
- Morning brief routine (~7am daily): assembles calendar + open tasks + overdue + context-aware sentence → Telegram push.
- Skill completion pings: any skill emits a Telegram message when done (configurable per-skill).
- Reminder routines: scan `tasks` for due-in-24h, overdue, abandoned-for-N-days → ping.
- Wiki-health weekly digest: stale articles, orphaned raw/ files, dangling `_index.md` entries.
- Implementation: each is a SKILL.md + Supabase row + launchd plist on the Mac, pushing through n8n's Telegram node.

### What this means for the build order

Updated phase sequence (revised 2026-05-11):
```
Phase 2.1  → dashboard polish (skills.prompt + fire-and-forget)
↓
context dump session (memory.context-dump, 45-60 min)
↓
Phase 3 → MEMORY skills (weekly-recap, search-wiki, add-note)
↓
Phase 1.6 → stable tunnel + custom domain (blocked on Student Pack)
↓
Phase 3 → PRODUCTIVITY, NEXUM skills
↓
Phase 5 → Task layer (Supabase tasks table + dashboard reorg)
↓
Phase 4 → Telegram conversational (depends on stable tunnel + tasks + skills)
↓
Phase 6 → Proactive outreach routines
↓
Phase 7 → Status + iteration
↓
Phase 3 → GROWTH & BUSINESS skills (can also happen earlier — independent)
```

(GROWTH & BUSINESS domain build is independent of the Telegram/Task layer work and can run in parallel anytime after the context dump.)

---

---

## ▶️ NEXT SESSION — pick A (2 manual steps to finish 2.1) or B

**A. Finish Phase 2.1 (2 manual steps — SHIPPED by Mac agent session 2026-05-11, 2 blockers remain)**

Phase 2.1 code is LIVE (commit `bb16050`, auto-deployed to Cloudflare Pages). The `/api/run` fire-and-forget pattern works, `/api/run/[run_id]` polling endpoint is live, SkillCard polls until completion. BUT 2 manual steps block full end-to-end from the dashboard:

### Manual step 1 — Cloudflare Pages: add SUPABASE_SERVICE_ROLE_KEY (5 min, browser)

The new `/api/run` reads `SUPABASE_SERVICE_ROLE_KEY` server-side. Without it, every dashboard Run click returns `{"error":"Supabase not configured"}`. The API token only has Workers Scripts scope (not Pages), so this must be done in the browser.

1. Go to https://dash.cloudflare.com → Pages → `agentic-os` project
2. Settings → Environment variables → Production
3. Add variable: `SUPABASE_SERVICE_ROLE_KEY` (type: Secret) → paste the value from `~/.agentic-os.env`
4. Also add to Preview environment (same value)
5. Redeploy: go to Deployments → click "Retry deployment" on the latest build

After this step, `/api/run` will return `{run_id, status: "queued", skill_slug}` immediately and polling will work.

### Manual step 2 — n8n workflow: switch "Supabase: Insert Run" to "Supabase: Update Run" (10 min, n8n UI)

The canonical workflow JSON is updated in `agentic-os/n8n-workflows/agentic-os-base.json` (commit `bb16050`). The live n8n instance still has the old Insert logic. Until this is updated, successful skill runs will try to INSERT a new row with `status=success` instead of UPDATEing the existing `status=running` row that the dashboard created. This means duplicate runs rows and the dashboard polled status won't update.

In n8n UI at `http://localhost:5678` (or `http://100.91.142.86:5678` over Tailscale):

1. Open the `agentic-os-base` workflow
2. Find the node named **"Supabase: Insert Run"**
3. Change operation from **Create** to **Update**
4. In the Update node config:
   - **Table**: `runs`
   - **Filter** → Add condition: Column = `id`, Operator = `eq`, Value = `={{ $('Webhook').item.json.body.run_id }}`
   - **Fields to update**:
     - `ended_at` = `={{ $now.toISO() }}`
     - `status` = `success`
     - `output` = `={{ $json.output }}`
5. Rename the node to **"Supabase: Update Run"**
6. Save the workflow

After both steps, run the full smoke test:
```bash
URL='https://agentic-os-40r.pages.dev'
RUN_ID=$(curl -s -X POST "$URL/api/run" -H 'Content-Type: application/json' -d '{"skill_slug":"memory.echo-test"}' | jq -r '.run_id')
echo "Run id: $RUN_ID"
for i in 1 2 3 4 5 6 7 8 9 10; do
  STATUS=$(curl -s "$URL/api/run/$RUN_ID" | jq -r '.status')
  echo "[$i] status=$STATUS"
  if [ "$STATUS" = "success" ] || [ "$STATUS" = "failure" ]; then break; fi
  sleep 3
done
```

**B. Run the context dump session NOW (45-60 min, conversational with Claude)**
- Invoke `memory.context-dump` skill OR just paste the SKILL.md prompt into a Claude Code session and run it manually.
- SKILL.md location: `agentic-os/.claude/skills/memory/context-dump.md`. Has the full 8-topic interview spec (background, current work, Nexum deep dive, build skills, voice/style, goals, fears/motivations, tools/stack).
- Output: structured markdown files in `wiki/personal/` (already created as empty stub). Updates `wiki/_master-index.md` and `wiki/personal/_index.md` as it goes.
- Doesn't need Phase 2.1 to be done first — can run via raw conversation in Claude Code on the laptop. The dashboard Run button for this skill won't work cleanly until Phase 2.1 because the route hardcodes echo-test, but the skill itself works fine when invoked directly.

**C. Different work entirely**
- Security hardening (n8n webhook Header Auth, Mac concurrent-request limiter) — both still pending.
- Phase 3 first MEMORY skills (weekly-recap, search-wiki, add-note) — would normally need context dump first for grounded prompts, but can pre-design generically.

---

## 💻 Laptop-specific notes (what you can/can't do without ~/.agentic-os.env)

The vault is iCloud-synced, so the laptop has all the source files (CLAUDE.md, plan, dashboard code, SKILL.md, wiki/). BUT sensitive secrets only live on the Mac mini at `~/.agentic-os.env` (chmod 600, not in iCloud). Implications:

| Task | Works on laptop? | Why |
|---|---|---|
| Read/edit any vault file | ✅ | iCloud-synced |
| git commit + push | ✅ | git auth uses your GitHub creds on each machine |
| Run `npm run dev` locally (dashboard preview) | ✅ | needs `dashboard/.env.local` which IS iCloud-synced (contains only anon key + tunnel URL, no secrets) |
| Trigger skills via the public dashboard URL | ✅ | hits public Cloudflare Pages URL; auth is server-side in n8n on the Mac |
| Trigger skills via curl to the cloudflared tunnel | ✅ | n8n webhook is open today; bearer is on the Mac side |
| Run `memory.context-dump` interview | ✅ | Pure text Q&A, no secrets needed for the interview portion. Output writes to iCloud-synced `wiki/personal/`. |
| Insert/update Supabase via service role | ❌ on laptop | Service role key is Mac-only. Workaround: use Supabase Dashboard SQL Editor (browser, no key needed) — that's how Phase 2.1's `alter table` would happen. |
| Restart launchd services / edit ~/.agentic-os.env | ❌ on laptop | Mac-only files. SSH to Mac if needed (Tailscale IP `100.91.142.86`). |
| Use Cloudflare API token autonomously | ❌ on laptop | Token at `~/.agentic-os.env` on Mac. Workaround: copy token from Mac to laptop's local env if needed, OR just use Cloudflare dashboard UI. |

**Practical implication:** Option B (context dump) is the most laptop-friendly. Option A (Phase 2.1) is mostly laptop-friendly except for the Supabase schema change (do that via Supabase UI in browser) and any final smoke test that depends on Mac-side n8n credentials (still works because n8n is running on the Mac regardless of where you're typing).

---

## OS domain structure — 4 foundational domains

The OS is built around 4 domains where Gabe operates daily: **MEMORY, PRODUCTIVITY, NEXUM, GROWTH & BUSINESS**. These ARE the OS — not a temporary narrowing. Additional wiki folders (school, football, bible-study, side-projects, personal-ops, consulting, ai-systems) persist for note-storage and receive raw-triage SECONDARY routing, but they are not OS domains and have no active skill build. If a real need emerges later, a folder can be promoted to OS-domain status.

**Operational order for next sessions:**
1. Finish Phase 2.1 (dashboard polish — skills.prompt column + fire-and-forget /api/run + plan/capture pane + wiki search). Dashboard now renders 4 columns (post-restructure deploy).
2. Run the **context dump session** (`memory.context-dump` skill, 45–60 min): Gabe answers 8 interview topics covering background/work/goals/voice/projects/approach. Output: wiki articles in `wiki/personal/`. Grounds every skill that follows.
3. Phase 3 build order: **MEMORY → PRODUCTIVITY → NEXUM → GROWTH & BUSINESS**.

---

## Live state (verified 2026-05-10 evening)

### launchd services on Mac mini

```
launchctl list | grep agenticos
<pid>  0  com.agenticos.server        — :4242  Express, runs `claude --print --dangerously-skip-permissions`
<pid>  0  com.agenticos.n8n           — :5678  n8n 2.19.5 (Node 22 keg-only)
<pid>  0  com.agenticos.cloudflared   — quick tunnel → localhost:5678 (URL rotates on restart)
```

### Verified end-to-end pipeline

```
caller → n8n webhook (/skill-run) → Supabase Get Skill (slug lookup) → IF Active
       → HTTP: Mac :4242/run with Bearer auth → Mac server spawns `claude --print` (CWD=vault)
       → claude executes SKILL.md prompt → response back through n8n
       → Supabase Insert Run row → response to caller
```

Last smoke test 2026-05-10 evening: `memory.echo-test` returned `{"output":"PONG\n","run_id":"4b7fc5ac-d358-4314-b0b6-33b2600434a7","skill_slug":"memory.echo-test"}`. Run row in Supabase, status=success.

### Live URLs

| URL | Purpose |
|---|---|
| `http://localhost:5678` | n8n UI (Mac) |
| `http://100.91.142.86:5678` | n8n over Tailscale (any Gabe device) |
| `https://<rotates>.trycloudflare.com` | n8n public (`grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' ~/agentic-os-server/cloudflared-stderr.log \| head -1`) |
| `http://localhost:4242/health` | Mac endpoint health |
| `http://localhost:3000` | Dashboard local dev (run with `cd agentic-os/dashboard && PATH=/opt/homebrew/opt/node@22/bin:$PATH npm run dev`) |

### Skills shipped

| Slug | Trigger | Status |
|---|---|---|
| `memory.echo-test` | n8n webhook + dashboard Run button | ✅ verified |
| `memory.raw-triage` | n8n webhook (manual today; weekly launchd routine planned) | ✅ verified end-to-end (3 articles filed in 2026-05-10 morning run) |

### Files live in vault

```
agentic-os/
├── AGENTIC_OS_PLAN.md                 # master plan (updated to reflect Phase 1.6, 10 domains, current status)
├── HANDOFF.md                          # this file
├── STATUS.md                           # current state snapshot
├── .claude/skills/memory/
│   └── raw-triage.md                  # SKILL.md prompt (date-templated, upsert syntax fixed)
├── launchd/
│   ├── com.agenticos.server.plist     # canonical (no API key — loaded via dotenv on Mac)
│   ├── com.agenticos.n8n.plist
│   └── com.agenticos.cloudflared.plist
├── mac-server/                         # canonical source for ~/agentic-os-server/
├── n8n-self-host/SETUP.md             # how Phase 1.5 was built + named-tunnel upgrade path
├── n8n-workflows/
│   ├── agentic-os-base.json           # importable workflow (7 nodes)
│   └── agentic-os-base-SETUP.md       # n8n UI walkthrough
└── dashboard/                          # Phase 2 — Next.js 15.5.2 (next-on-pages compatible)
    ├── app/, lib/, public/             # standard Next.js layout
    ├── RLS-POLICIES.sql                # applied via Management API
    ├── RESEARCH.md                     # pre-build research (next-on-pages × Next 16, Pages gotchas, etc.)
    └── README.md

CLAUDE.md                                # source of truth for Claude's project context
credentials/.env                         # NON-sensitive vars only (URLs, paths, anon key) — sensitive moved to ~/.agentic-os.env
raw/                                     # inbox, ephemeral
wiki/<10 domains>/                       # ai-systems, bible-study, consulting, football, memory, nexum, personal-ops, productivity, school, side-projects
output/
```

### Where secrets live

- **`~/.agentic-os.env`** (Mac mini, chmod 600, NOT in iCloud) — `AGENTIC_OS_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_PERSONAL_ACCESS_TOKEN`. **Single source of truth for sensitive secrets.**
- **`~/agentic-os-server/.env`** (Mac mini, chmod 600, NOT in iCloud) — duplicate of `AGENTIC_OS_API_KEY` for legacy reasons (server.js loads both files via dotenv; same value, no conflict)
- **`<vault>/credentials/.env`** (iCloud-synced) — only NON-sensitive: SUPABASE_URL, SUPABASE_PROJECT_REF, SUPABASE_ANON_KEY (safe; RLS-bound), GitHub URL, Cloudflare email, Tailscale IP, vault paths, n8n URLs. Sensitive vars are commented-out placeholders pointing at `~/.agentic-os.env`.
- **n8n SQLite** (`~/.n8n/database.sqlite`) — encrypted with key at `~/.n8n/config`. Holds the bearer + service role copies that n8n nodes use. **Back up `~/.n8n/config` separately — if lost, all stored credentials are unreadable.**

Verified 2026-05-10 evening: `grep -rl <bearer-key>` and `grep -rl <service-role-key>` against the entire vault both return empty. Zero literal-secret leaks in iCloud-synced files.

---

## What's done this session (2026-05-10, all of it)

| Phase / Task | Status | Notes |
|---|---|---|
| Phase 0 — Plan document | DONE (prior) | `agentic-os/AGENTIC_OS_PLAN.md` — updated this session for Phase 1.6 + 10 domains + current status |
| Phase 1 — Memory + Mac mini foundation | SHIPPED | All 6 tasks done; smoke test passed |
| Phase 1.5 — n8n self-host (was Phase 5, pulled forward) | SHIPPED | Node 22 keg-only, n8n 2.19.5, all 3 launchd services |
| First real skill — `memory.raw-triage` | SHIPPED | End-to-end verified 2026-05-10 morning; 3 articles filed |
| Security perimeter tightening | SHIPPED | All sensitive secrets out of iCloud → `~/.agentic-os.env` chmod 600 |
| Phase 2 v1 — Dashboard scaffold | SHIPPED | Next.js 15.5.2, builds clean (`next build` + `npx @cloudflare/next-on-pages`), local dev verified |
| Phase 2 v1 — RLS policies + anon read | SHIPPED | Applied via Supabase Management API; verified anon SELECT works, anon INSERT rejected |
| Phase 2 v1 — Run button wired | SHIPPED | `/api/run` POSTs to webhook; `memory.echo-test` returns PONG end-to-end |
| Code review (correctness + plan conformance) | DONE | Findings cataloged; all blockers/important fixed |
| Security review (secrets, perms, threat model) | DONE | Findings cataloged; all CRITICAL + HIGH fixed |
| **Phase 2 v1 — GitHub push** | SHIPPED 2026-05-11 | Vault at `https://github.com/ChickenPeep/agentic-os` (private). 7 commits. Comprehensive `.gitignore` excludes credentials/raw/wiki/output/.obsidian/agentic-os-Vault/dashboard build artifacts. Zero secret leaks verified. |
| **Phase 2 v1 — Cloudflare Pages deploy** | SHIPPED 2026-05-11 | Live at `https://agentic-os-40r.pages.dev`. Project name: `agentic-os` (Pages). Connected to `ChickenPeep/agentic-os` main branch. Build = `npx @cloudflare/next-on-pages`, root = `agentic-os/dashboard`. 4 env vars set on Production+Preview. |
| **Phase 2 v1 — End-to-end deployed verification** | SHIPPED 2026-05-11 | `POST https://agentic-os-40r.pages.dev/api/run -d '{"skill_slug":"memory.echo-test"}'` → returned `{"output":"PONG\n","run_id":"d73033ce-...","skill_slug":"memory.echo-test"}` AND landed a row in Supabase `runs` table with `triggered_by=dashboard`. Full chain: public internet → Pages edge → cloudflared tunnel → Mac n8n → Mac Express :4242 → claude --print → all the way back. |
| **Cloudflare API token saved** | DONE 2026-05-11 | Workers Scripts + Account Settings scope. Stored at `~/.agentic-os.env` (chmod 600, Mac-only, NOT iCloud). Lets future sessions manage Cloudflare programmatically. |
| **Stale Worker `agentic-os-flare` deleted** | DONE 2026-05-11 | Was a leftover Hello-World stub from when the project was first created as a Worker (wrong product). Deleted via API. |
| **`app/favicon.ico` → `public/favicon.ico` move (commit `2376623`)** | SHIPPED 2026-05-11 | Fix for App-Router-treats-favicon-as-route bug that was making `GET /` serve favicon binary instead of page HTML. Verified live at 22:32 UTC: homepage now serves `text/html` and renders the full board. |

### Fixes applied this session (post-review)

1. **`server.js` spawn args** — removed bogus `'-p', ''` (was passing empty positional prompt)
2. **`server.js` env strip** — built `claudeEnv` minus AGENTIC_OS_API_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_PERSONAL_ACCESS_TOKEN before spawning claude. Closes prompt-injection self-exfiltration. Verified via probe prompt: claude reports `not set` for those vars now.
3. **`server.js` dotenv** — loads from `~/.agentic-os.env` first (Mac-local, single source of truth), then `~/agentic-os-server/.env` as fallback
4. **`server.js` double-response guard** — `let responded = false` prevents Express "Cannot set headers after sent" on race between error+close
5. **launchd plist** — removed `AGENTIC_OS_API_KEY` from `EnvironmentVariables` block in BOTH the live plist and the vault canonical copy. Key now loaded only via dotenv at runtime.
6. **`raw-triage.md` date** — replaced hardcoded `2026-05-10` with `${TODAY}=$(date +%Y-%m-%d)` everywhere; switched heredoc delimiter from `'EOF'` to `EOF` so variable expands. Was a silent-correctness bug for any future run.
7. **`raw-triage.md` upsert syntax** — added `?on_conflict=path` to the wiki_articles POST URL; needed for `Prefer: resolution=merge-duplicates` to work
8. **PAT moved out of iCloud** — `SUPABASE_PERSONAL_ACCESS_TOKEN` now in `~/.agentic-os.env`, vault credentials/.env has placeholder
9. **Missing wiki folders** — created `wiki/memory/` and `wiki/productivity/` with `_index.md` stubs (the raw-triage skill maps to them)
10. **Doc drift** — AGENTIC_OS_PLAN.md updated for Phase 1.6, 10 domains, current status table; wiki/_master-index.md expanded to all 10 domain rows

---

## Next session — start here

### Immediate (Phase 2.1 polish, ~1-2 hrs, agent-driven)

Phase 2 v1 is LIVE on the public internet (https://agentic-os-40r.pages.dev). The Run button only works for `memory.echo-test` today because it's special-cased in `/api/run/route.ts`. Polish before any new skill work:

1. **Add a `prompt` column to the `skills` table** so skills can self-describe their canonical prompt:
   ```sql
   alter table skills add column prompt text;
   update skills set prompt = 'reply with the literal text PONG and nothing else' where slug = 'memory.echo-test';
   update skills set prompt = '<paste contents of agentic-os/.claude/skills/memory/raw-triage.md>' where slug = 'memory.raw-triage';
   ```

2. **Update `app/api/run/route.ts`** to fetch the prompt from Supabase by slug (using server-side service-role for read, or expand RLS to allow anon SELECT on the prompt column). Pattern:
   ```ts
   const { data: skill } = await supabase.from('skills').select('prompt').eq('slug', skill_slug).single();
   // POST to webhook with skill.prompt as body.prompt
   ```

3. **Convert `/api/run` to fire-and-forget** to survive Cloudflare Pages' 30s edge timeout. The dashboard POSTs, gets back `{run_id, status: "queued"}` immediately, then polls Supabase `runs` table for completion.

   Rough pattern: insert a `runs` row with `status='running'` BEFORE firing the webhook, return that row's id immediately, let n8n update the row to `success`/`failure` when done. Dashboard polls every 2-3s or uses Supabase realtime subscription.

### High (security hardening, ~10 min, mix of UI + agent)

4. **Add Header Auth to the n8n `/webhook/skill-run` endpoint.** Currently the webhook is unauthenticated — anyone with the trycloudflare URL can trigger any active skill. In n8n UI:
   - Open the agentic-os-base workflow → Webhook node → Authentication = "Header Auth"
   - Create a credential with a random secret (`openssl rand -hex 32`)
   - Update `dashboard/.env.local`: add `WEBHOOK_AUTH_SECRET=<value>` and have `/api/run/route.ts` send it as a header
   - For curl smoke tests, add `-H "X-Webhook-Secret: <value>"`

5. **Add a simple concurrent-request limiter to `~/agentic-os-server/server.js`** (max 2-3 concurrent claude spawns; return 429 over). Prevents quota burn from accidental loops.

### After Phase 2.1 — Context dump session (NEW, ~45-60 min, conversational)

Per the SUMMER FOCUS reframe (top of `AGENTIC_OS_PLAN.md`): before any Phase 3 domain interviews, run a dedicated context dump.

- Format: Gabe talks through background, current work, goals, voice, previous projects, approach. Claude listens + asks follow-ups.
- Output: one or more wiki articles in `wiki/personal/` (new folder — create at session time). These become reference material for every skill that follows.
- Why now: grounds the upcoming Phase 3 skill prompts in Gabe's real voice/context instead of generic AI prose.

### Async (Student Pack approval, then Phase 1.6)

6. **Wait on GitHub Student Developer Pack approval.** Applied 2026-05-10 with @uwosh.edu email.

7. **Once approved (Phase 1.6):**
   - Redeem free `.me` domain on Namecheap → `gabrieltorres.me`
   - Add domain to Cloudflare, change Namecheap nameservers
   - `cloudflared tunnel login` → `tunnel create agentic-os` → `tunnel route dns agentic-os n8n.gabrieltorres.me`
   - Swap launchd plist's `tunnel --url ...` → `tunnel run agentic-os` with `~/.cloudflared/config.yml`
   - Add `WEBHOOK_URL=https://n8n.gabrieltorres.me/` to n8n plist, reload
   - Update `credentials/.env` `N8N_TUNNEL_URL` to stable URL
   - Update Cloudflare Pages env var `NEXT_PUBLIC_RUN_WEBHOOK_URL` to stable URL
   - Add **Cloudflare Access** policy on the Pages domain (Google login) — closes the public dashboard surface
   - Detailed step-by-step: `agentic-os/n8n-self-host/SETUP.md` "Upgrading to a stable tunnel"

### Phase 3 (after Phase 2.1 + context dump are done)

**Build order:** MEMORY → PRODUCTIVITY → NEXUM → GROWTH & BUSINESS.

- MEMORY: already has `memory.echo-test`, `memory.raw-triage`, `memory.context-dump`. Plan adds 1-2 more (e.g., `memory.weekly-recap`, `memory.search-wiki`).
- PRODUCTIVITY: 3-4 skills (e.g., calendar brief, daily focus, weekly review).
- NEXUM: 6-8 skills split across engineering / customer feedback / GTM / polish + portfolio.
- GROWTH & BUSINESS: 5-7 skills (daily learning, idea generation, consulting prep, sales/outreach).

Total target: ~20 skills.

**Not OS domains — not skill-tracked:** school, football, bible-study, side-projects, personal-ops, consulting, ai-systems. They receive raw-triage SECONDARY routing for notes but no skills are built for them.

---

## Deferred / open decisions

- **`agentic-os-Vault/` at vault root** — Obsidian's default welcome stub. 4 files, no content. Safe to delete. Not blocking anything. (Open since session start.)
- **n8n owner password strength** — the security review couldn't audit it. If Gabe's password is short/weak, the n8n public UI is the soft attack surface. Recommend ≥16 chars, mixed classes. Optional: enable n8n MFA if available on self-hosted.
- **`raw/` test files (`nexum-idea.md` etc.) and the prior `raw/_archived/2026-05-10/`** — left from this session's testing. Leave or clean up? If left, the next raw-triage run sees nothing new and returns `files_seen: 0` which is correct.
- **Do we want Cloudflare Access in front of n8n itself (not just the dashboard)?** That would close the open `/webhook/skill-run` problem too. But it complicates programmatic access from non-browser clients (Telegram bot in Phase 4). Defer the decision until Phase 4 design.

---

## Open MEDIUM/LOW items (defer; document & move on)

- **Concurrent-request limit on Mac server (Item 5 above)** — fix in Phase 2.1
- **Quick-tunnel URL rotation** — solved by Phase 1.6 (named tunnel). Until then, manual re-fetch via the grep one-liner.
- **`/health` endpoint unauthenticated** — only Tailscale-reachable, acceptable as-is.
- **Supabase `status_counts` view + RLS** — verified anon-readable; works.

---

## Architecture cheat-sheet (one-liner per layer)

- **Mac mini = canonical execution host.** Always-on, runs n8n + Express + cloudflared via launchd.
- **Bearer token + Tailscale + future Cloudflare Access = the perimeter.** `--dangerously-skip-permissions` is intentional and required for autonomous skills; the safety is "only the operator can wake the robot," not "the robot asks before each action."
- **Each skill = one SKILL.md prompt + one Supabase row.** All skills share the same n8n workflow (`agentic-os-base`); the workflow looks up the skill by slug and routes the prompt to the Mac.
- **Dashboard = Next.js on Cloudflare Pages.** Reads from Supabase via anon key + RLS. Hits the n8n webhook through `/api/run` (server-side, hides webhook URL from client bundle).
- **Wiki = LLM-maintained markdown.** No vector DB. `wiki/_master-index.md` is the entry point; per-domain `_index.md` lists articles.

---

## Notes / gotchas (cumulative)

- **Apple Silicon node path:** `/opt/homebrew/bin/node` (system Node 26). n8n uses `/opt/homebrew/opt/node@22/bin/node` (keg-only Node 22) because `isolated-vm` doesn't compile on 26.
- **launchd needs explicit PATH:** every plist needs `PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin` in `EnvironmentVariables` so child processes can find `claude`, `node`, etc.
- **n8n encryption key:** `~/.n8n/config`. Back this up. If lost, all stored credentials are unreadable.
- **Cloudflare quick tunnel URL rotates** on cloudflared restart. To get current: `grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' ~/agentic-os-server/cloudflared-stderr.log | head -1`. Replaced by stable named tunnel in Phase 1.6.
- **`--dangerously-skip-permissions`** is set on the Mac claude invocation. Required for autonomous skills to write files. The trust boundary is the bearer token — keep it on Mac only.
- **n8n SQLite + direct edits:** the previous session edited `database.sqlite` directly to bump HTTP node timeout to 240s. n8n had to be restarted to pick up the change. Avoid direct SQLite edits when possible — use n8n UI or REST API.

---

## Key config (non-sensitive — sensitive secrets live at `~/.agentic-os.env` on Mac)

| Key | Value |
|---|---|
| Supabase project | `ykfjnageewaonunrnwft` |
| Supabase URL | `https://ykfjnageewaonunrnwft.supabase.co` |
| Mac Tailscale IP | `100.91.142.86` |
| Mac endpoint port | `4242` |
| n8n local URL | `http://localhost:5678` |
| n8n public URL | rotates — see grep one-liner above |
| GitHub | `https://github.com/ChickenPeep/agentic-os` |
| Dashboard local | `http://localhost:3000` |
| Vault path (Mac) | `/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault` |
| Vault path (Windows) | `C:\Users\gabri\iCloudDrive\agentic-os-vault` |
