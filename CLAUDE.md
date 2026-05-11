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

| Machine | Role | Vault path |
|---|---|---|
| Mac mini | **Canonical execution host** — always on, runs Claude Code, hosts vault | `/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault` |
| Windows desktop | Primary dev, Nexum work | `C:\Users\gabri\iCloudDrive\agentic-os-vault` |
| Dell Inspiron 14 | Mobile work | iCloud sync |
| Phone | Telegram remote, Obsidian read | |

All machines on Tailscale. Vault syncs via iCloud Drive. Mac mini is the canonical execution host — skills run there by default.

## Vault map

```
agentic-os-vault/
├── CLAUDE.md                  ← this file — source of truth for my context
├── credentials/
│   └── .env                   ← keys and config (iCloud-synced — see security note)
├── raw/                       ← inbox, dump anything (triage within ~7 days)
├── wiki/                      ← LLM-maintained domain knowledge
│   ├── _master-index.md       ← entry point, updated after every wiki write
│   ├── memory/                ← OS domain
│   ├── productivity/          ← OS domain
│   ├── nexum/                 ← OS domain
│   ├── growth-business/       ← OS domain
│   ├── personal/              ← context-dump output (reference for all skills)
│   ├── consulting/            ← note-storage only
│   ├── school/                ← note-storage only
│   ├── football/              ← note-storage only
│   ├── bible-study/           ← note-storage only
│   ├── side-projects/         ← note-storage only
│   ├── personal-ops/          ← note-storage only
│   └── ai-systems/            ← note-storage only
├── output/                    ← query results, reports, slide decks
└── agentic-os/                ← the OS code itself
    ├── AGENTIC_OS_PLAN.md     ← master build plan
    ├── STATUS.md              ← auto-updated phase + skill counts
    ├── .claude/
    │   ├── skills/            ← SKILL.md files by domain
    │   ├── routines/          ← routine configs
    │   ├── agents/            ← agent configs
    │   └── memory/            ← memory hooks
    ├── dashboard/             ← Next.js app (Cloudflare Pages)
    └── n8n-workflows/         ← exported workflow JSON
```

## Domains (the 4 foundational OS domains)
MEMORY, PRODUCTIVITY, NEXUM, GROWTH & BUSINESS

## Additional wiki folders (no OS skill build, but raw-triage can route notes here when unambiguous)
school, football, bible-study, side-projects, personal-ops, consulting, ai-systems

## Abstraction levels

| Level | Icon | Description |
|---|---|---|
| MANUAL | 👆 | One-off thinking. No codification. |
| SKILL | 📓 | Repeatable, clear inputs/outputs. Has SKILL.md + Supabase entry + webhook + dashboard card. |
| ROUTINE | ⏰ | Skill on a schedule. Default: Mac launchd. Use n8n cloud cron only when Mac-off is OK or cloud-only context needed. |
| AGENT | 🤖 | Multi-step autonomous workflow with trigger, tools, success criteria. Runs on Mac mini. |

## Memory rules

- Skills that produce knowledge → write to `wiki/<domain>/`, update that folder's `_index.md` and `wiki/_master-index.md`.
- Skills that produce external artifacts → `output/`.
- `raw/` is ephemeral. Triage within ~7 days.
- No vector DB. Markdown only. `_master-index.md` is the entry point.
- This file (`CLAUDE.md`) is the source of truth for my context. Update it when context changes.

## Execution host default

Mac mini is the canonical host for all skills and routines. Only use n8n cloud cron when the routine needs cloud-only context or must survive Mac being off.

## Key config

- Supabase project: `ykfjnageewaonunrnwft` → `https://ykfjnageewaonunrnwft.supabase.co`
- Mac mini Tailscale IP: `100.91.142.86`
- Mac endpoint port: `4242`
- n8n cloud: `https://gabrieltorres18.app.n8n.cloud`
- GitHub: `https://github.com/ChickenPeep/agentic-os`
- Dashboard: Cloudflare Pages (auto-deploy from GitHub)
