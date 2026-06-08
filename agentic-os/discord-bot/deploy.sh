#!/bin/bash
# Deploy the Discord command-center bot onto the Mac mini. Idempotent; re-run after edits.
set -euo pipefail

MAC_VAULT="$HOME/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault"
SRC="$MAC_VAULT/agentic-os/discord-bot"
DEST="$HOME/agentic-os-server/discord-bot"
LA="$HOME/Library/LaunchAgents"
PL="com.agenticos.discord-bot"

[ -d "$SRC" ] || { echo "ERROR: source not found: $SRC"; exit 1; }

echo "==> Copying runtime to $DEST"
mkdir -p "$DEST" "$HOME/agentic-os-server/logs" "$LA"
rsync -a --delete \
  --exclude 'data/' --exclude '__pycache__/' --exclude '.venv/' --exclude '.pytest_cache/' \
  "$SRC/" "$DEST/"

echo "==> Copying shared notes.py"
cp "$MAC_VAULT/agentic-os/lib/notes.py" "$DEST/notes.py"

echo "==> Installing Python deps"
python3 -m pip install -q -r "$DEST/requirements.txt"

echo "==> Patching bridge-settings.json with deployed path"
python3 - "$DEST" <<'PY'
import json, sys, os
dest = sys.argv[1]
p = os.path.join(dest, "bridge-settings.json")
s = json.load(open(p))
for grp in s.get("hooks", {}).get("PreToolUse", []):
    for h in grp.get("hooks", []):
        h["command"] = f"python3 {dest}/guard_hook.py"
json.dump(s, open(p, "w"), indent=2)
PY

echo "==> Writing run-bot.sh (sources env, then launches)"
cat > "$DEST/run-bot.sh" <<EOF
#!/bin/bash
set -uo pipefail
cd "$DEST"
set -a
[ -f ~/.agentic-os.env ] && source ~/.agentic-os.env
export VAULT_PATH="$MAC_VAULT"
set +a
exec python3 bot.py
EOF
chmod +x "$DEST/run-bot.sh"

echo "==> Installing launchd service"
cp "$MAC_VAULT/agentic-os/launchd/$PL.plist" "$LA/$PL.plist"
launchctl unload "$LA/$PL.plist" 2>/dev/null || true
launchctl load "$LA/$PL.plist"
echo "==> Done. Tail logs: ~/agentic-os-server/logs/discord-bot-*.log"
