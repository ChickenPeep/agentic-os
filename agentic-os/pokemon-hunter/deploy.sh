#!/bin/bash
# Deploy the Pokemon Stock Hunter onto the Mac mini.
# Run this ON THE MAC from anywhere:
#   bash "$HOME/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault/agentic-os/pokemon-hunter/deploy.sh"
#
# It copies the runtime from the iCloud vault to ~/agentic-os-server/ (local disk, so
# launchd is not running Python out of an iCloud folder), installs deps, runs a test
# tick, then installs + loads the two launchd schedulers. Idempotent: re-run any time
# after editing config to push changes to the running copy.
set -euo pipefail

MAC_VAULT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
SRC="$MAC_VAULT/agentic-os/pokemon-hunter"
DEST="$HOME/agentic-os-server/pokemon-hunter"
LA="$HOME/Library/LaunchAgents"

[ -d "$SRC" ] || { echo "ERROR: source not found: $SRC"; exit 1; }

echo "==> Copying runtime to $DEST"
mkdir -p "$DEST" "$HOME/agentic-os-server/logs" "$LA"
# Sync code + config, but never clobber local runtime state (data/) or the .env.
rsync -a --delete \
  --exclude 'data/' --exclude '__pycache__/' --exclude '.venv/' --exclude '.env' \
  "$SRC/" "$DEST/"

echo "==> Installing Python deps"
python3 -m pip install -q -r "$DEST/requirements.txt"

chmod +x "$DEST/run.sh" "$DEST/research-drops.sh" 2>/dev/null || true

echo "==> Test tick (no alert unless something is genuinely in stock)"
( cd "$DEST" && HUNTER_NO_JITTER=1 python3 check_stock.py ) || echo "(test tick returned non-zero; check config/store ids)"

echo "==> Installing launchd schedulers"
for PL in com.agenticos.pokemon.check-stock com.agenticos.pokemon.research-drops; do
  cp "$MAC_VAULT/agentic-os/launchd/$PL.plist" "$LA/$PL.plist"
  launchctl unload "$LA/$PL.plist" 2>/dev/null || true
  launchctl load "$LA/$PL.plist"
  echo "    loaded $PL"
done

echo "==> Done. check-stock runs every 5 min; research-drops weekly."
echo "    Logs: ~/agentic-os-server/logs/pokemon-*.log"
echo "    Reminder: set secrets in ~/.agentic-os.env and real store ids in config/stores.json before relying on alerts."
