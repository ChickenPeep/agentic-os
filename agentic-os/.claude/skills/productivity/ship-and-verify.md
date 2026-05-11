---
slug: productivity.ship-and-verify
domain: PRODUCTIVITY
name: ship-and-verify
description: Stages + commits + pushes vault changes to GitHub, waits for Cloudflare Pages redeploy, smoke-tests the deployed dashboard, returns structured pass/fail result. Includes secret-leak guard.
type: skill
---

You are running the `productivity.ship-and-verify` skill. Your job is to commit and push any pending vault changes to GitHub, wait for Cloudflare Pages to redeploy, smoke-test the deployed dashboard, and return a structured JSON result. If no changes exist, exit cleanly. Never push a real secret.

At the end you MUST output ONLY a single JSON object (no prose, no markdown fences) matching the schema at the bottom of this prompt.

---

## Step 1 -- Change directory and capture git status

Run this in a single bash call:

```bash
VAULT="/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
cd "$VAULT"
git status --short
```

Log the output. If git status returns empty (no lines), return immediately:

```json
{"result": "nothing_to_ship"}
```

Do not proceed with any further steps.

---

## Step 2 -- Stage all changes

```bash
VAULT="/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
cd "$VAULT"
git add -A
git diff --cached --name-only
```

Capture the list of staged files. This is the `files_changed` array in the final output.

Note: the vault `.gitignore` excludes `credentials/`, `wiki/`, `raw/`, `output/`, `.obsidian/`, `agentic-os-Vault/`, build artifacts, and `.DS_Store`. The `git add -A` is safe to run as-is.

---

## Step 3 -- Secret-leak scan (NON-NEGOTIABLE)

Run this grep against the staged diff:

```bash
VAULT="/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
cd "$VAULT"
# Exclude lines that are themselves grep command invocations (e.g. this pattern in SKILL.md docs)
LEAK_PAT='AGENTIC_OS_API_KEY=[a-f0-9]{64}|SUPABASE_SERVICE_ROLE_KEY=eyJ|sbp_[a-z0-9]{36}|sk-ant-api[0-9]'
git diff --cached | grep -v 'grep.*LEAK_PAT\|grep -iE.*eyJ\|LEAK_PAT=' | grep -iE "$LEAK_PAT" || true
```

If the grep returns ANY matches:

- Unstage everything: `git reset HEAD`
- Return immediately:

```json
{
  "result": "blocked_secret_leak",
  "patterns_found": ["<each matched line, truncated to first 40 chars>"]
}
```

Do not commit. Do not push. This check is non-negotiable. The OS must never push a real secret to GitHub.

If the grep returns no matches, continue to Step 4.

---

## Step 4 -- Commit

If the caller's prompt contains a specific commit message, use it. Otherwise build one:

```bash
VAULT="/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
cd "$VAULT"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
COMMIT_MSG="auto: ship work-in-progress at $TS"
git commit -m "$COMMIT_MSG"
```

Capture the commit SHA:

```bash
cd "$VAULT"
git rev-parse HEAD
```

---

## Step 5 -- Push to origin main

```bash
VAULT="/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
cd "$VAULT"
git push origin main
```

If push fails, return:

```json
{
  "result": "shipped_but_smoke_failed",
  "commit_sha": "<sha>",
  "files_changed": [...],
  "smoke_test": {
    "homepage": "broken",
    "api_run": "broken",
    "details": "git push failed: <error output>"
  }
}
```

---

## Step 6 -- Wait for Cloudflare Pages redeploy

```bash
sleep 90
```

Cloudflare Pages typically deploys within 60-90 seconds of a push. This wait gives it time before the smoke test.

---

## Step 7 -- Smoke test the deployed dashboard

Run both checks:

### 7a. Homepage check

```bash
curl -sI https://agentic-os-40r.pages.dev/
```

Parse the response:
- Expect HTTP status `200`
- Expect `content-type` header containing `text/html` (NOT `image/x-icon`)
- If both pass: `homepage = "ok"`
- Otherwise: `homepage = "broken"`

### 7b. API run check

```bash
curl -s -X POST https://agentic-os-40r.pages.dev/api/run \
  -H "Content-Type: application/json" \
  -d '{"skill_slug":"memory.echo-test"}'
```

Parse the response:
- If the response is JSON containing a `run_id` field: `api_run = "ok"`
- If the response is JSON containing `"error"` with the value `"Supabase not configured"` or similar env-missing error: `api_run = "env_missing"`
- Any other failure (non-JSON, HTTP 5xx, connection refused, timeout): `api_run = "broken"`

---

## Step 8 -- Determine final result

Use this decision table:

| homepage | api_run | result |
|----------|---------|--------|
| ok | ok | shipped_ok |
| ok | env_missing | shipped_but_pages_env_missing |
| ok | broken | shipped_but_smoke_failed |
| broken | (any) | shipped_but_smoke_failed |

---

## Step 9 -- Output ONLY this JSON

No prose, no markdown fences. Raw JSON only:

```
{
  "result": "shipped_ok" | "shipped_but_pages_env_missing" | "shipped_but_smoke_failed" | "blocked_secret_leak" | "nothing_to_ship",
  "commit_sha": "<40-char hex sha, or null if nothing was committed>",
  "files_changed": ["<relative path>", ...],
  "smoke_test": {
    "homepage": "ok" | "broken",
    "api_run": "ok" | "env_missing" | "broken",
    "details": "<one-line summary of what the smoke test returned>"
  }
}
```

For `nothing_to_ship` and `blocked_secret_leak` results, `commit_sha` is null, `files_changed` is [], and `smoke_test` can be omitted or null.

---

## Constraints

- Never echo or log the contents of `~/.agentic-os.env` or `credentials/.env`. The secret-leak grep in Step 3 is the only guard needed.
- Never skip Step 3. Even if the caller is trusted, the grep runs every time.
- Always `cd "$VAULT"` at the start of each bash block. The working directory does not persist between calls.
- If git push succeeds but curl to pages.dev times out entirely, treat homepage as "broken" and return `shipped_but_smoke_failed`.
- The `shipped_but_pages_env_missing` result is NOT a failure of this skill. It means the deploy succeeded but the Phase 2.1 Supabase env var is not yet set in Cloudflare. Report it clearly and do not retry.
- Return ONLY the raw JSON object as your final output. No other text.
