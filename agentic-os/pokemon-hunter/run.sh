#!/bin/bash
# launchd entrypoint for pokemon.check-stock.
# Sources secrets, runs one check tick, and logs a Supabase `runs` row only when
# noteworthy (an alert fired, or errors occurred) plus one hourly heartbeat, so the
# dashboard RunHistory stays readable under a 5-minute cadence.
#
# Deployed location (mirrors mac-server convention):
#   ~/agentic-os-server/pokemon-hunter/run.sh
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# --- secrets: per-machine env first (not in iCloud), then vault env ---
# When deployed to ~/agentic-os-server/, the vault is NOT at ../.. , so also try the
# canonical iCloud vault path. Prefer keeping real secrets in ~/.agentic-os.env.
MAC_VAULT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
set -a
[ -f ~/.agentic-os.env ] && source ~/.agentic-os.env
for ENVF in "$DIR/../../credentials/.env" "$MAC_VAULT/credentials/.env"; do
  [ -f "$ENVF" ] && source "$ENVF"
done
set +a

STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SUMMARY="$(python3 check_stock.py 2>>"$DIR/check-stock.err.log")"
EXIT=$?
ENDED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "$STARTED_AT $SUMMARY"   # goes to launchd StandardOutPath

# Parse the JSON summary (last line of stdout) without jq dependency.
ALERTS=$(printf '%s' "$SUMMARY" | python3 -c "import sys,json;print(json.loads(sys.stdin.read() or '{}').get('alerts_sent',0))" 2>/dev/null || echo 0)
NERR=$(printf '%s' "$SUMMARY" | python3 -c "import sys,json;print(len(json.loads(sys.stdin.read() or '{}').get('errors',[])))" 2>/dev/null || echo 0)

# --- decide whether to log this tick ---
HEARTBEAT_FILE="$DIR/data/.last_heartbeat"
NOTEWORTHY=0
[ "${ALERTS:-0}" -gt 0 ] && NOTEWORTHY=1
[ "${NERR:-0}" -gt 0 ] && NOTEWORTHY=1
# hourly heartbeat: log if marker older than 3600s or missing
if [ ! -f "$HEARTBEAT_FILE" ] || [ "$(( $(date +%s) - $(stat -f %m "$HEARTBEAT_FILE" 2>/dev/null || echo 0) ))" -ge 3600 ]; then
  NOTEWORTHY=1
  mkdir -p "$DIR/data" && touch "$HEARTBEAT_FILE"
fi

if [ "$NOTEWORTHY" -eq 1 ] && [ -n "${SUPABASE_URL:-}" ] && [ -n "${POKEMON_CHECK_STOCK_SKILL_ID:-}" ]; then
  STATUS="success"; [ "$EXIT" -ne 0 ] && STATUS="failure"
  # Escape the summary for embedding as a JSON string value.
  OUT=$(printf '%s' "$SUMMARY" | python3 -c "import sys,json;print(json.dumps(sys.stdin.read()))")
  curl -s -X POST "$SUPABASE_URL/rest/v1/runs" \
    -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
    -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=minimal" \
    -d "{\"skill_id\":\"$POKEMON_CHECK_STOCK_SKILL_ID\",\"started_at\":\"$STARTED_AT\",\"ended_at\":\"$ENDED_AT\",\"status\":\"$STATUS\",\"output\":$OUT,\"triggered_by\":\"cron\",\"host\":\"mac\"}" >/dev/null
  # bump skill last_run_at; run_count increment is best-effort via a SQL function if present
  curl -s -X PATCH "$SUPABASE_URL/rest/v1/skills?slug=eq.pokemon.check-stock" \
    -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
    -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
    -H "Content-Type: application/json" \
    -H "Prefer: return=minimal" \
    -d "{\"last_run_at\":\"$ENDED_AT\"}" >/dev/null
fi

exit 0
