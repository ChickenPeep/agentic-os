# Discord Command Center Bot — Design Spec

**Date:** 2026-06-08
**Status:** Approved design, ready for implementation plan
**Domain:** new (`COMMAND-CENTER` / agentic-os infra)
**Host:** Mac mini (canonical execution host)

## 1. Purpose

Give Gabe a way to talk to Claude Code 24/7 from his phone. He frequently captures
feature ideas (often for Nexum) by dictating or typing notes while away from a
computer. This bot turns a Discord channel into a low-friction front-end onto the
always-on `claude` CLI on the Mac mini: he texts an idea, Claude chats back with
memory, and for real work it researches and builds autonomously on a git branch,
then reports back for approval.

Non-goals (v1): voice-message transcription, multiple users, threads-per-task,
auto-merge, auto-deploy, a Telegram front-end.

## 2. Decisions (locked)

| Decision | Choice |
|---|---|
| Autonomy | Talk + research + **stage on a branch**, report back, gate the risky actions |
| Interaction | **One ongoing chat with memory** in a dedicated channel; long tasks run in the background with progress + final report |
| Gated actions (require explicit "go") | Push/merge to main, deploy/restart services, spend money / paid APIs, send external messages |
| Voice | **Phone dictation → text** (no transcription pipeline) |
| Engine | **Claude Code CLI reusing the Mac's existing login** (subscription auth, no separate API billing) |
| Idea logging | Every incoming idea logged to vault `raw/` inbox **and** the dashboard |

## 3. Architecture

A single long-running Python process using `discord.py`, managed by launchd
(`com.agenticos.discord-bot.plist`, `KeepAlive=true`, `RunAtLoad=true`), mirroring
the existing `com.agenticos.server` pattern. It connects to the Discord gateway
(websocket) and listens in one allowlisted channel. For each owner message it shells
out to the already-authenticated `claude` CLI on the Mac, resuming a persisted
session so the conversation has memory.

The bot runs as Gabe's user on the Mac and therefore has the same filesystem reach
as Claude Code normally does. The **guard hook** (section 6) is the blast-radius
limiter, not the OS.

Deployment mirrors pokemon-hunter: code lives in the iCloud vault, `deploy.sh` copies
the runtime to local disk (`~/agentic-os-server/discord-bot/`) so launchd is not
running Python out of an iCloud folder, installs deps, and loads the plist.

## 4. Components

```
agentic-os/discord-bot/
  bot.py            # discord.py gateway; message handling; progress posts; approval flow; idea logging
  runner.py         # claude -p subprocess wrapper; stream-json parsing; session + branch management
  guard_hook.py     # Claude Code PreToolUse hook: deny gated actions, allow safe ones
  state.py          # persistent map: channel -> {session_id, branch, pending_action}
  idealog.py        # append idea to vault raw/ inbox + insert dashboard row
  config.json       # owner id, channel id, branch prefix, timeouts, model
  requirements.txt  # discord.py
  supabase-seed.sql # seeds the command-center.bot skill row (dashboard column)
  deploy.sh         # copy to ~/agentic-os-server/discord-bot, install deps, load plist
  README.md
agentic-os/launchd/com.agenticos.discord-bot.plist
```

### 4.1 bot.py
- Connects with `DISCORD_BOT_TOKEN`, requires the **Message Content** privileged intent.
- Ignores all messages whose author is not `DISCORD_OWNER_ID` and all channels except
  the configured one.
- On an owner message: log the idea (idealog), post a "🤔 on it…" placeholder, dispatch
  to runner, stream progress by editing the placeholder (throttled, see 7.1), post the
  final summary.
- Recognizes approval replies ("ship it", "go", "ship") and the 👍 reaction tied to a
  pending action; on approval, executes the parked gated step (v1: push + open PR).
- Serializes work per conversation (one Claude run at a time per branch); queues extra
  messages and tells the user they're queued.

### 4.2 runner.py
- Invokes:
  `claude -p "<message>" --output-format stream-json --verbose --resume <session_id>
   --append-system-prompt "<bridge context>"` with the working directory set to the
  vault and the active task branch checked out.
- First message of a conversation omits `--resume` and captures the new `session_id`
  from the stream; subsequent messages resume it.
- `--append-system-prompt` injects bridge context: "You are reachable via Discord from
  Gabe's phone. Stage work on the current branch. You cannot push, deploy, spend money,
  or send external messages — when you need one of those, finish your work, summarize
  it, and tell Gabe to reply 'ship it'."
- Parses stream-json events → (a) human-readable progress lines (tool name + target),
  (b) the final assistant text, (c) the resulting `session_id`.
- Allowed-tools set passed so non-interactive runs don't hard-block on safe tools;
  fine-grained gating lives in the hook (Bash is allowed broadly, then filtered).

### 4.3 guard_hook.py (PreToolUse hook)
Registered in the project `.claude/settings.json` so it fires for the bot's headless
runs. Receives each tool call and returns an allow/deny decision.

- **Deny** when a Bash command matches gated patterns: `git push`, `git merge`/checkout
  into `main`, `launchctl`, any `deploy.sh` / service restart, outbound network sends
  (`curl`/`wget`/`gh ... create`/webhook POSTs) except read-only fetches used for
  research, and anything invoking a paid API. On deny, return a message Claude will
  read ("Gated action — stage it and ask Gabe to approve").
- **Allow**: Read, Write, Edit, Grep, Glob, and Bash for `git add/commit/branch/status/
  diff/checkout -b`, local test runs, and read-only research fetches.
- Pure function `decide(tool_name, tool_input) -> {allow, reason}` for unit testing.

> Note: distinguishing "git commit" (allow) from "git push" (deny) requires inspecting
> the Bash command string, which is why a hook is used rather than only `--allowedTools`.

### 4.4 state.py
- Persists to `~/agentic-os-server/discord-bot/data/state.json` (gitignored runtime).
- Per channel: `session_id`, `branch`, `pending_action` (e.g. `{type: "push", branch}`),
  `updated_at`. Loaded on boot so memory + pending approvals survive restarts.

### 4.5 idealog.py
- On every owner message, append to the vault `raw/` inbox a timestamped markdown file
  (`raw/idea-YYYYMMDD-HHMMSS.md`) with the raw text and the Discord message link, so it
  is triaged within the normal ~7-day raw flow.
- Insert a dashboard row into Supabase via the service role key, reusing the existing
  `runs` table + RunHistory machinery (same pattern as pokemon-hunter). The bot is
  seeded as its own skill row (`command-center.bot`, domain `COMMAND-CENTER`) so each
  idea/task logs a `runs` row against that `skill_id`: `started_at`, `status`
  (`received` → `working` → `done`/`failed`), `output` (idea text truncated + branch +
  diff stat), `triggered_by: "discord"`, `host: "mac"`. This gives the command center a
  POKEMON-style column for free. The insert runs in bot.py (Python), not through a
  Claude tool call, so the guard hook does not apply to it. Logging failure must never
  block the chat (best-effort, swallow errors with a log line).

## 5. Data flow

1. Gabe sends a message in `#command-center`.
2. bot.py verifies author == owner and channel == allowed; otherwise ignore silently.
3. idealog records the idea to `raw/` + dashboard (best-effort).
4. Bot posts "🤔 on it…" and dispatches to runner with the message, resuming the session.
5. For a work task, runner ensures branch `bot/<slug>` is checked out, runs Claude
   headless with the guard hook.
6. Runner streams events; bot edits the placeholder with throttled progress.
7. On completion the bot posts: summary of changes, branch name, `git diff --stat`, and
   "Reply **ship it** to push + open a PR." It stores `pending_action`.
8. Gabe replies "ship it" → bot runs `git push -u origin <branch>` then `gh pr create`,
   posts the PR link, clears `pending_action`.
9. Deploy / spend / external actions are surfaced in the summary but never auto-run; they
   require Gabe to act deliberately (at a computer or via a future explicit command).

## 6. Security

- **Owner allowlist** (`DISCORD_OWNER_ID`): the bot acts only on Gabe's messages. This is
  the primary control — a Claude-with-tools bridge open to others would be dangerous.
- **Channel allowlist**: only the configured channel is processed.
- Secrets (`DISCORD_BOT_TOKEN`, `DISCORD_OWNER_ID`, channel id) in `~/.agentic-os.env`,
  never in the vault/git.
- Never operates on `main`; never pushes/deploys without explicit approval (guard hook).
- Git only on the Mac (canonical host) per the iCloud-shared-`.git` caution in CLAUDE.md.

## 7. Error handling & limits

- **Long runs**: heartbeat edits ("still working… 4m") with a hard cap (default 20 min,
  configurable) then abort + report.
- **Claude crash / non-zero exit**: post the stderr tail; keep the session so Gabe can
  retry or redirect.
- **Discord disconnects**: discord.py auto-reconnects; launchd `KeepAlive` restarts the
  process if it dies.
- **Concurrency**: one Claude run per conversation at a time; extra messages queue with a
  "queued behind current task" note to avoid git collisions.
- **Dirty / wrong branch**: if the working tree is unexpectedly dirty or on `main`, stop
  and report rather than guess.
- **Rate limits**: throttle progress edits to <= 1 edit / ~2s; reuse one message rather
  than spamming new ones.

### 7.1 Discord progress throttling
Live progress updates edit a single message at most once every ~2 seconds, coalescing
intermediate events, to stay under Discord's edit rate limits.

## 8. Testing

- `runner.py` unit: feed canned stream-json transcripts → assert correct progress lines,
  final text, and captured session_id.
- `guard_hook.py` unit: feed tool-call payloads (`git push`, `deploy.sh`, `launchctl`,
  external `curl`, `git commit`, `Write`) → assert each deny/allow decision.
- `idealog.py` unit: assert a raw/ file is written and the dashboard insert is attempted;
  assert a logging failure does not raise.
- Dry-run mode: process a test message against a test channel with a trivial prompt.
- Manual acceptance: (a) read-only question ("what's in the vault root?"), (b) a small
  feature task → verify branch + staged diff + summary, (c) "ship it" → PR link appears,
  (d) confirm a `git push` attempt by Claude mid-task is blocked by the hook.

## 9. Setup Gabe performs (gated on him, like the Discord webhook)

1. Create a Discord application + bot at discord.com/developers; copy the bot token.
2. Enable the **Message Content Intent** (Bot → Privileged Gateway Intents).
3. Invite the bot to his server (scopes: `bot`; permissions: read/send messages, read
   history in the chosen channel).
4. Paste the token to Claude → added to `~/.agentic-os.env` as `DISCORD_BOT_TOKEN`,
   plus `DISCORD_OWNER_ID` and the channel id.
5. Claude seeds `supabase-seed.sql` (the `command-center.bot` skill row) and copies the
   resulting `skill_id` into `~/.agentic-os.env` as `COMMAND_CENTER_BOT_SKILL_ID`.
6. Claude runs `deploy.sh` and loads the launchd service.

## 10. Future (explicitly out of v1)

- Telegram front-end reusing `runner.py` (kept separable for this reason).
- Voice-message transcription (Whisper).
- Threads-per-task for parallel projects.
- Optional auto-merge and a whitelisted, explicitly-confirmed deploy command.
