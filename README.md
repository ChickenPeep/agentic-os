# Agentic OS

Personal automation OS built on top of an Obsidian vault, with a Mac mini as the always-on execution brain, a Next.js dashboard on Cloudflare Pages, and n8n cloud as the webhook hub.

## Architecture

- **Mac mini** runs n8n + Express endpoint + Cloudflare tunnel (all under launchd)
- **n8n** receives webhook calls, looks up the skill in Supabase, routes to the Mac
- **Mac Express endpoint** runs `claude --print` against the vault to execute skills
- **Supabase** stores skill registry, run history, plans, wiki articles
- **Dashboard** (Next.js + Cloudflare Pages) is the click-to-run control surface

## Repo layout

- `agentic-os/AGENTIC_OS_PLAN.md` — master implementation plan (phases 0-6)
- `agentic-os/HANDOFF.md` — session-to-session handoff (current state, next actions)
- `agentic-os/STATUS.md` — phase status snapshot
- `agentic-os/.claude/skills/` — SKILL.md files (one per skill, per domain)
- `agentic-os/dashboard/` — Next.js 15 dashboard (deploys to Cloudflare Pages from `agentic-os/dashboard/` as project root)
- `agentic-os/n8n-workflows/` — exported n8n workflow JSON
- `agentic-os/launchd/` — canonical copies of macOS launchd plists
- `agentic-os/mac-server/` — canonical source for the Mac Express endpoint
- `CLAUDE.md` — Claude Code context for this project

## Status

Phases 0, 1, 1.5, 2 v1 shipped. First real skill (`memory.raw-triage`) live. See `agentic-os/STATUS.md` for current phase status and `agentic-os/HANDOFF.md` for what to pick up next.

## Setup

This is a personal project; the codebase reflects one specific machine + iCloud + Tailscale setup. See `agentic-os/n8n-self-host/SETUP.md` and `agentic-os/mac-server/SETUP.md` for how things are wired.

---

Personal project by Gabriel Torres ([@ChickenPeep](https://github.com/ChickenPeep)).
