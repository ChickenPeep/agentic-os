# Discord Command Center Bot

Text Claude Code from your phone. Runs 24/7 on the Mac mini. You message one Discord
channel; the bot chats with memory, researches/builds on a `bot/<slug>` branch, and
reports back. Push/merge, deploy, spending, and external sends wait for you to reply
**ship it**. Ideas are logged to the vault `raw/` inbox and the dashboard.

## How it works
`bot.py` (discord.py, launchd) → `runner.py` shells out to the Mac's logged-in
`claude` CLI (`-p --output-format stream-json --resume <id> --settings bridge-settings.json`).
`guard_hook.py` is a PreToolUse hook loaded **only** for the bot's runs (via `--settings`),
so your own interactive Claude sessions are unaffected. It allows safe tools and denies
gated ones (push/merge/deploy/launchctl/external sends/paid APIs).

## Setup (on the Mac mini)
1. **Create the Discord bot:** https://discord.com/developers/applications → New
   Application → Bot → Reset Token → copy it. Under **Privileged Gateway Intents**,
   enable **Message Content Intent**.
2. **Invite it:** OAuth2 → URL Generator → scopes `bot`; permissions: View Channel,
   Send Messages, Read Message History. Open the URL, add it to your server.
3. **Get the IDs:** in Discord, enable Developer Mode (Settings → Advanced), then
   right-click your user → Copy User ID, and right-click the target channel → Copy
   Channel ID.
4. **Env:** add to `~/.agentic-os.env`:
   ```
   DISCORD_BOT_TOKEN=...
   DISCORD_OWNER_ID=...
   DISCORD_CHANNEL_ID=...
   COMMAND_CENTER_BOT_SKILL_ID=...   # from the seed step
   ```
5. **Seed the dashboard:** apply `supabase-seed.sql`, then
   `select id from skills where slug='command-center.bot';` → put it in the env above.
6. **Deploy:** `bash deploy.sh` (copies runtime to `~/agentic-os-server/discord-bot/`,
   installs deps, loads the launchd service). Re-run after any edit.

## Test
```bash
python3 -m pytest -q          # unit tests
```
Then in Discord: send "what's in the vault root?" (read-only), then a small feature
request; verify a `bot/...` branch + staged diff appear, then reply **ship it** for a PR.

## Guardrails
The guard hook (`guard_hook.py`, `decide()`) is the blast-radius limiter. The ONLY path
that pushes/opens a PR is `bot.py` after your explicit "ship it" — never Claude itself.
Deploy / spend / external sends are reported, never auto-run.
