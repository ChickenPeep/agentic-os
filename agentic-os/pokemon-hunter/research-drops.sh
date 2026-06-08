#!/bin/bash
# launchd entrypoint for pokemon.research-drops (weekly).
# Runs Claude headless from the vault root so it can use the pokemon.research-drops
# skill (web research -> writes wiki/side-projects/pokemon-drops-calendar.md).
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Claude must run from the real vault root so it can resolve agentic-os/.claude/skills.
# When deployed to ~/agentic-os-server/, ../.. is NOT the vault, so use the canonical
# iCloud path; fall back to ../.. for the case of running straight from the vault.
MAC_VAULT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
if [ -d "$MAC_VAULT/agentic-os/.claude/skills" ]; then
  VAULT="$MAC_VAULT"
else
  VAULT="$(cd "$DIR/../.." && pwd)"
fi
cd "$VAULT"

set -a
[ -f ~/.agentic-os.env ] && source ~/.agentic-os.env
[ -f credentials/.env ] && source credentials/.env
set +a

PROMPT="Run the pokemon.research-drops skill. Research upcoming US Pokemon TCG sealed product releases for the next ~6 months and update wiki/side-projects/pokemon-drops-calendar.md per the skill instructions. Output only the final JSON summary."

# Headless Claude run, scoped to the vault (skills resolve from agentic-os/.claude/skills).
claude --print "$PROMPT"

exit 0
