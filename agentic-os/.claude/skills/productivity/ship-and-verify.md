---
slug: productivity.ship-and-verify
domain: PRODUCTIVITY
name: ship-and-verify
description: Stages + commits + pushes vault changes to GitHub, waits for Cloudflare Pages redeploy, smoke-tests the deployed dashboard, returns structured pass/fail result. Includes secret-leak guard.
type: skill
---

You are running the `productivity.ship-and-verify` skill. Your job is to commit and push any pending vault changes to GitHub, wait for Cloudflare Pages to redeploy, smoke-test the deployed dashboard, and return a structured JSON result. If no changes exist, exit cleanly. Never push a real secret.

At the end you MUST output ONLY a single JSON object (no prose, no markdown fences) matching the schema at the bottom of this prompt.

Result codes:
- `nothing_to_ship` -- no staged changes found
- `blocked_secret_leak` -- secret pattern detected; nothing committed or pushed
- `push_failed` -- commit succeeded locally but git push failed (auth/network); smoke test never ran
- `shipped_ok` -- pushed and all smoke checks passed
- `shipped_but_pages_env_missing` -- pushed and deployed but Supabase env var not yet set in Cloudflare
- `shipped_but_smoke_failed` -- pushed but homepage or API check returned unexpected result

---

## Step 1 -- Change directory and capture git status

<!-- VAULT is re-declared in every bash block intentionally. Bash invocations do not persist CWD or env across separate tool calls, so each block must be self-contained. -->

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

# LEAK_PAT covers:
#   - Named project keys (AGENTIC_OS_API_KEY, SUPABASE_*, CLOUDFLARE_API_TOKEN) in any assignment format:
#       KEY=value  KEY: value  "KEY": "value"  KEY = value  (the [[:space:]"=:]+ handles all)
#     followed by a value prefix matching eyJ (JWT), 40+ hex chars, sbp_ (Supabase PAT), or cfut_ (Cloudflare user token)
#   - cfut_ standalone: catches Cloudflare user tokens in any var name (e.g. CF_TOKEN=cfut_...)
#   - Anthropic SDK keys: sk-ant-api<N>-
#   - Stripe live/test keys: sk_(live|test)_<20+ alphanum>
#   - GitHub PATs: ghp_<20+ alphanum+_> (real tokens are 36 chars after prefix; threshold 20 catches even slightly truncated ones)
#     or github_pat_<60+ alphanum+_> (fine-grained PAT format)
#   - AWS access key IDs: AKIA<16 uppercase alphanum>
LEAK_PAT='(AGENTIC_OS_API_KEY|SUPABASE_SERVICE_ROLE_KEY|SUPABASE_PERSONAL_ACCESS_TOKEN|CLOUDFLARE_API_TOKEN)[[:space:]"=:]+(eyJ|[a-f0-9]{40,}|sbp_[a-z0-9]{30,}|cfut_[a-zA-Z0-9_]{20,})|cfut_[a-zA-Z0-9_]{20,}|sk-ant-api[0-9]+-|sk_(live|test)_[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9_]{20,}|github_pat_[a-zA-Z0-9_]{60,}|AKIA[A-Z0-9]{16}'

# Drop any added line (^+ prefix) that is itself a grep command invocation.
# This suppresses grep command lines inside SKILL.md docs without blanket-dropping
# lines that merely contain LEAK_PAT= (which would hide real secrets like +LEAK_PAT=sk-ant-api03-...).
git diff --cached | grep -v '^+.*grep\b' | grep -iE "$LEAK_PAT" || true
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

Capture the commit SHA (VAULT re-declared so this block is self-contained):

```bash
VAULT="/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
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

If push fails, return immediately (nothing was shipped; smoke test never ran):

```json
{
  "result": "push_failed",
  "commit_sha": "<commit_sha from git rev-parse HEAD>",
  "files_changed": "<the staged file list captured in Step 2 as a JSON array of strings>",
  "push_error": "<the stderr text from git push>"
}
```

---

## Step 6 -- Wait for Cloudflare Pages redeploy

```bash
# Cloudflare Pages p90 deploy time is ~90s (as of 2026-05-11; revisit if false-negatives increase).
# We use a 3x30s retry loop in Step 7 instead of a bare sleep here.
# No sleep needed in this step.
echo "push complete, proceeding to smoke test retry loop"
```

---

## Step 7 -- Smoke test the deployed dashboard

### 7a. Homepage check

Run the smoke test with a 3-attempt retry loop (30s gaps, 90s total -- covers p90 of Cloudflare Pages deploy variance):

```bash
# p90 of Cloudflare Pages deploy time as of 2026-05-11; revisit if false-negatives increase.
SMOKE_OK=""
for attempt in 1 2 3; do
  echo "[smoke attempt $attempt of 3] sleeping 30s before check..."
  sleep 30
  if curl -sI -m 10 'https://agentic-os-40r.pages.dev/' | head -1 | grep -q '200'; then
    SMOKE_OK="homepage_ok"
    break
  fi
done
if [ -z "$SMOKE_OK" ]; then
  echo "homepage smoke test failed after 3 attempts (90s total elapsed)"
fi
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
  "result": "shipped_ok" | "shipped_but_pages_env_missing" | "shipped_but_smoke_failed" | "push_failed" | "blocked_secret_leak" | "nothing_to_ship",
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
For `push_failed`, `smoke_test` is omitted or null (push never succeeded so no deploy happened).

---

## Constraints

- Never echo or log the contents of `~/.agentic-os.env` or `credentials/.env`. The secret-leak grep in Step 3 is the only guard needed.
- Never skip Step 3. Even if the caller is trusted, the grep runs every time.
- Always `cd "$VAULT"` at the start of each bash block. The working directory does not persist between calls.
- If git push succeeds but curl to pages.dev times out entirely after all 3 retry attempts, treat homepage as "broken" and return `shipped_but_smoke_failed`.
- The `shipped_but_pages_env_missing` result is NOT a failure of this skill. It means the deploy succeeded but the Phase 2.1 Supabase env var is not yet set in Cloudflare. Report it clearly and do not retry.
- Return ONLY the raw JSON object as your final output. No other text.
