# Agentic OS — Status

_Auto-updated by the weekly status routine. Last updated manually: 2026-05-10 (evening)._

## Phase status

| Phase | Status | Notes |
|---|---|---|
| 0 — Plan document | DONE | `agentic-os/AGENTIC_OS_PLAN.md` reviewed and approved |
| 1 — Memory + Mac foundation | **SHIPPED** | End-to-end smoke test passed 2026-05-10 20:33 UTC. `memory.echo-test` skill returned `PONG\n`, run row in Supabase. |
| 1.5 — n8n self-host (was Phase 5, pulled forward) | **SHIPPED** | n8n + cloudflared running as launchd; workflow active; quick tunnel URL live |
| 2 — Dashboard MVP | **v1 LIVE on public internet** | https://agentic-os-40r.pages.dev — verified end-to-end 2026-05-11. Run button works for `memory.echo-test`. Dashboard renders 4 OS-domain columns post-restructure. Still needs: `skills.prompt` column for non-echo skills + fire-and-forget /api/run (Phase 2.1) + custom domain (Phase 1.6). |
| 3 — Domain interview loop | NOT STARTED | MEMORY → PRODUCTIVITY → NEXUM → … |
| 4 — Telegram remote | NOT STARTED | Needs stable named tunnel (replace quick tunnel first) |
| 5 — n8n local migration | DONE | Subsumed by Phase 1.5 |
| 6 — Status + iteration | NOT STARTED | Weekly review skill, this file auto-updated |

## Live services on Mac mini (launchd)

```
launchctl list | grep agenticos
<pid>  0  com.agenticos.server        — :4242  Express endpoint, runs `claude --print` per webhook
<pid>  0  com.agenticos.n8n           — :5678  n8n (Node 22, ~/.n8n-runtime/, data ~/.n8n/)
<pid>  0  com.agenticos.cloudflared   — quick tunnel → localhost:5678 (URL rotates on restart)
```

| URL | Purpose | Verified 2026-05-10 |
|---|---|---|
| `http://localhost:5678/healthz` | n8n local | ✅ |
| `http://100.91.142.86:5678/healthz` | n8n over Tailscale | (test from Windows) |
| `https://sms-thereby-coins-pink.trycloudflare.com/healthz` | n8n public | ✅ |
| `http://localhost:4242/health` | Mac endpoint local | ✅ |
| `http://localhost:4242/run` (Bearer) | Mac endpoint, runs claude | ✅ (returned `{"output":"PONG\n"}`) |

## Files in vault (Phase 1 + 1.5 deliverables)

```
agentic-os/
├── AGENTIC_OS_PLAN.md                                # master plan
├── HANDOFF.md                                         # session-to-session handoff
├── STATUS.md                                          # this file
├── .claude/{skills,routines,agents,memory}/.gitkeep   # ready for Phase 3
├── launchd/
│   ├── com.agenticos.server.plist                    # Mac endpoint (PATH-fixed for ARM)
│   ├── com.agenticos.n8n.plist                       # n8n service (Node 22 path)
│   └── com.agenticos.cloudflared.plist               # quick tunnel
├── mac-server/                                        # canonical source for ~/agentic-os-server/
│   ├── server.js  package.json  .env.template  SETUP.md
├── n8n-self-host/
│   └── SETUP.md                                       # how Phase 1.5 was built + how to upgrade tunnel
├── n8n-workflows/
│   ├── agentic-os-base.json                          # importable workflow (7 nodes)
│   └── agentic-os-base-SETUP.md                      # n8n UI walkthrough + smoke test
└── dashboard/                                         # Phase 2 — Next.js 15 (Cloudflare Pages)
    ├── app/page.tsx                                   # skills grid by domain
    ├── app/api/run/route.ts                          # Run button → n8n webhook (wired)
    ├── app/components/SkillCard.tsx                  # skill card + Run button
    ├── .env.local                                     # dev env (Supabase + webhook URL)
    └── RLS-POLICIES.sql                              # applied 2026-05-10 via Management API

CLAUDE.md                                              # source of truth for Claude's project context
credentials/.env                                       # secrets (git-ignored; SEE iCloud NOTE below)
raw/                                                   # inbox (triage in 7 days)
wiki/                                                  # 8 domain folders + _master-index.md
output/                                                # artifacts and reports
```

## Supabase

Project `ykfjnageewaonunrnwft` — schema deployed:
- Tables: `skills`, `runs`, `plans`, `wiki_articles` ✅
- View: `status_counts` ✅

## Skill counts

| Domain | Skills | Routines | Agents |
|---|---|---|---|
| MEMORY | 3 | 0 | 0 |
| PRODUCTIVITY | 1 | 1 | 0 |
| NEXUM | 0 | 0 | 0 |
| GROWTH & BUSINESS | 0 | 0 | 0 |

_Additional wiki folders (school, football, bible-study, side-projects, personal-ops, consulting, ai-systems) exist for note-storage but are not OS domains and don't have skills built._

MEMORY skills: `memory.echo-test` (smoke test / PONG), `memory.raw-triage` (triages raw/ into wiki/), `memory.context-dump` (45-60 min interview → wiki/personal/ articles).

## Live working flows (end-to-end verified)

| Skill | Trigger | Verified | Result |
|---|---|---|---|
| `memory.echo-test` | n8n webhook + dashboard Run button | 2026-05-10 | `{"output":"PONG\n","run_id":"...","skill_slug":"memory.echo-test"}` |
| `memory.raw-triage` | n8n webhook | 2026-05-10 | Pipeline verified; no raw/ files to triage at test time |

## Phase 1 + 1.5 acceptance evidence (2026-05-10)

End-to-end smoke test — `memory.echo-test` skill via local n8n webhook:

```
curl -X POST http://localhost:5678/webhook/skill-run \
  -d '{"skill_slug":"memory.echo-test","prompt":"...","triggered_by":"manual"}'
→ {"output":"PONG\n","run_id":"a0edfdf7-f1fb-47d1-bf66-718121df3e46","skill_slug":"memory.echo-test"}
```

Supabase `runs` row inserted with `status='success'`, `host='mac'`, output `PONG\n`. Full pipeline verified:

```
caller → n8n webhook → Supabase Get Skill → IF Active → Mac :4242 → claude --print → Supabase Insert Run → response
```

## Up next

- Phase 2.1 — Dashboard polish: add `prompt` column to `skills` table; update `/api/run` to fetch prompt from Supabase (enables Cloudflare Pages deploy); then push to GitHub and deploy to Pages.
- Phase 1.6 (parallel) — when GitHub Student Pack approves: register `gabrieltorres.me` → migrate DNS to Cloudflare → swap quick tunnel for stable named tunnel `n8n.gabrieltorres.me`
- Phase 3 — Domain interview loop (MEMORY → PRODUCTIVITY → NEXUM → ...)

_Last auto-ship test: 2026-05-11T21:41:00Z_

## Known issues / housekeeping

- **`agentic-os-Vault/` at vault root** — Obsidian's default welcome vault (3 stub files + .obsidian config). Not a duplicate of the project. Safe to delete. (See "Items needing decision" in HANDOFF.md.)
- **Cloudflare quick tunnel URL rotates** on every cloudflared restart. Acceptable for now; before Phase 4 (Telegram), upgrade to a stable named tunnel — see `agentic-os/n8n-self-host/SETUP.md` "Upgrading to a stable tunnel".
- **n8n encryption key at `~/.n8n/config`** — back this up. Without it, restored credentials are unreadable.

## Security: where secrets live

- `credentials/.env` is **git-ignored** (root `.gitignore` excludes the whole `credentials/` directory)
- BUT the entire vault lives in iCloud Drive, so `credentials/.env` syncs to iCloud and to every other machine signed into the same Apple ID. This was a deliberate informed choice — see `HANDOFF.md` and the auto-memory note. If higher security is ever needed, copy the env vars to a per-machine `~/.agentic-os.env` (chmod 600, never in iCloud) and have services read from there instead.
