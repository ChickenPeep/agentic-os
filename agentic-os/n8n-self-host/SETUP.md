# n8n self-host on Mac mini

Phase 1.5 — replaces n8n cloud. n8n + Cloudflare quick tunnel both run as launchd services on the Mac mini.

## Architecture

```
Mac mini  (canonical execution host, always on)
├── launchd
│   ├── com.agenticos.server       — port 4242, Express endpoint that runs Claude Code
│   ├── com.agenticos.n8n          — port 5678, n8n (Node 22, isolated runtime)
│   └── com.agenticos.cloudflared  — quick tunnel: public *.trycloudflare.com → localhost:5678
└── Tailscale  100.91.142.86       — n8n also reachable at http://100.91.142.86:5678 over the tailnet
```

External callers (Telegram in Phase 4, Cloudflare Pages dashboard in Phase 2 if hosted publicly) hit the cloudflared URL. Internal callers (anything on the tailnet — Windows desktop, Dell, phone via Tailscale) hit the Tailscale URL. The Mac itself uses localhost.

## Why Node 22 in a separate prefix

n8n's native dep `isolated-vm` doesn't compile on Node 26 yet. Node 22 LTS (installed via `brew install node@22`, keg-only) is used JUST for n8n. The system Node 26 still drives `agentic-os-server` and any other Node work. Both versions coexist cleanly:

- System Node:  `/opt/homebrew/bin/node` (v26.x, used by agentic-os-server)
- n8n Node:     `/opt/homebrew/opt/node@22/bin/node` (v22.22.x, only for n8n)
- n8n install:  `~/.n8n-runtime/` (isolated `npm -g --prefix` so n8n's deps don't collide with system globals)
- n8n data:     `~/.n8n/` (default — SQLite db, encryption key, credentials, workflows)

## Install steps (already done — for reference / future Mac rebuilds)

```bash
# 1. Node 22 (keg-only — does NOT replace system node)
brew install node@22

# 2. n8n into isolated prefix, using Node 22's npm (PATH override forces node-gyp to use Node 22)
mkdir -p ~/.n8n-runtime
PATH="/opt/homebrew/opt/node@22/bin:$PATH" \
  /opt/homebrew/opt/node@22/bin/npm install -g n8n --prefix="$HOME/.n8n-runtime"

# 3. Cloudflared
brew install cloudflared

# 4. Plists from vault → ~/Library/LaunchAgents/, then load
cp "/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault/agentic-os/launchd/com.agenticos.n8n.plist"          ~/Library/LaunchAgents/
cp "/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault/agentic-os/launchd/com.agenticos.cloudflared.plist"  ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.agenticos.n8n.plist
launchctl load ~/Library/LaunchAgents/com.agenticos.cloudflared.plist

# 5. Verify all three services up
launchctl list | grep agenticos
# expected:
#   <pid>  0  com.agenticos.server
#   <pid>  0  com.agenticos.n8n
#   <pid>  0  com.agenticos.cloudflared

# 6. Health checks
curl http://localhost:5678/healthz                                              # local
curl http://100.91.142.86:5678/healthz                                          # tailnet
TUNNEL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' ~/agentic-os-server/cloudflared-stderr.log | head -1)
curl "$TUNNEL/healthz"                                                          # public
```

## Capturing / refreshing the public URL

Quick tunnel URLs **rotate on every cloudflared restart**. To get the current one:

```bash
grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' ~/agentic-os-server/cloudflared-stderr.log | head -1
```

If you need to force a new URL (e.g., the old one is in someone's curl history): `launchctl unload && launchctl load` the cloudflared plist.

When you bring up a stable named tunnel later (see "Upgrading to a stable tunnel" below), update `N8N_TUNNEL_URL` in `credentials/.env` AND set `WEBHOOK_URL` in the n8n plist so the displayed webhook URLs in the n8n UI match.

## First-run setup (one-time, in the n8n UI)

1. Open `http://localhost:5678` (Mac itself), `http://100.91.142.86:5678` (any tailnet device), or the trycloudflare URL (anywhere on the internet)
2. n8n shows a setup screen — create the owner account: email + password. n8n is single-user by default.
3. Skip the survey if asked.
4. You're in. The encryption key was auto-generated on first start and lives at `~/.n8n/config` — **back it up if you ever wipe `~/.n8n/`**, otherwise stored credentials become unreadable.

## Importing the agentic-os-base workflow

Follow `agentic-os/n8n-workflows/agentic-os-base-SETUP.md` from step 1 onward. The only change vs the n8n cloud version: when it tells you to copy the production webhook URL, copy from your local n8n. The webhook will be reachable at:

- `http://localhost:5678/webhook/skill-run` (Mac itself — for testing curl from the Mac)
- `http://100.91.142.86:5678/webhook/skill-run` (any tailnet device — Windows, phone, etc.)
- `<N8N_TUNNEL_URL>/webhook/skill-run` (anywhere — required for Telegram in Phase 4)

n8n shows webhook URLs as `localhost:5678` in the UI by default. That's fine for local copy-paste; for external clients use the tailnet or tunnel URL instead.

## Operating notes

| Action | Command |
|---|---|
| Stop n8n | `launchctl unload ~/Library/LaunchAgents/com.agenticos.n8n.plist` |
| Start n8n | `launchctl load ~/Library/LaunchAgents/com.agenticos.n8n.plist` |
| Restart n8n | unload then load |
| Tail n8n logs | `tail -f ~/agentic-os-server/n8n-stdout.log ~/agentic-os-server/n8n-stderr.log` |
| Tail cloudflared logs | `tail -f ~/agentic-os-server/cloudflared-stderr.log` |
| Upgrade n8n | `PATH="/opt/homebrew/opt/node@22/bin:$PATH" /opt/homebrew/opt/node@22/bin/npm install -g n8n@latest --prefix="$HOME/.n8n-runtime"` then restart |
| Backup data | `tar czf ~/n8n-backup-$(date +%F).tar.gz ~/.n8n` (includes db, creds, encryption key) |

## Upgrading to a stable tunnel (deferred — do before Phase 4)

When you have a domain on Cloudflare:

1. `cloudflared tunnel login` — opens browser, picks the domain
2. `cloudflared tunnel create agentic-os` — creates a named tunnel, generates `~/.cloudflared/<UUID>.json`
3. `cloudflared tunnel route dns agentic-os n8n.<yourdomain>` — points subdomain at the tunnel
4. Replace the cloudflared launchd plist's ProgramArguments with: `cloudflared tunnel run agentic-os` (instead of `tunnel --url …`)
5. Add a `~/.cloudflared/config.yml` mapping `n8n.<yourdomain>` → `http://localhost:5678`
6. Reload the cloudflared service
7. Update `credentials/.env` `N8N_TUNNEL_URL=https://n8n.<yourdomain>`
8. Add `WEBHOOK_URL=https://n8n.<yourdomain>/` to the n8n plist EnvironmentVariables, reload n8n
9. Webhook URLs in the n8n UI will now show the stable URL — paste-ready for Telegram, third-party services

## Why we did NOT do today (and when to revisit)

| Skipped | Revisit when |
|---|---|
| Stable named tunnel + domain | Before Phase 4 (Telegram needs a URL that doesn't rotate) |
| HTTPS in front of n8n | Cloudflare Tunnel terminates HTTPS for us. If we ever expose n8n directly (no tunnel), revisit. |
| Postgres (instead of SQLite) | If/when a single workflow run starts hitting concurrency or db locking issues. SQLite is fine for personal volume. |
| Basic-auth on the n8n UI | n8n's built-in owner-account auth handles this. If you ever want IP allowlisting on the tunnel, use Cloudflare Access. |
| `WEBHOOK_URL` env var | When you have a stable tunnel URL — until then it'd be a lie. |
