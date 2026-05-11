# Mac mini server setup

Run these commands on the Mac mini (terminal or SSH).

## 1. Copy files from vault

```bash
cp -r "/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault/agentic-os/mac-server" \
      ~/agentic-os-server
cd ~/agentic-os-server
npm install
```

## 2. Create your .env

```bash
cp .env.template .env
# Generate a key:
openssl rand -hex 32
# Paste the output into .env as AGENTIC_OS_API_KEY
chmod 600 .env
```

Save the key — you'll need it in n8n and credentials/.env.

## 3. Test the server

```bash
node server.js &
curl http://localhost:4242/health
# expected: {"status":"ok"}
```

## 4. Install the launchd plist (keeps server alive across reboots)

See `../launchd/com.agenticos.server.plist` — edit the API key line, then:

```bash
cp ../launchd/com.agenticos.server.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.agenticos.server.plist
launchctl list | grep agenticos
```

## 5. Verify from Windows over Tailscale

```powershell
$body = '{"prompt":"Say hello in one word"}'
Invoke-RestMethod -Uri "http://100.91.142.86:4242/run" `
  -Method POST -Body $body -ContentType "application/json" `
  -Headers @{ Authorization = "Bearer YOUR_API_KEY" }
```

Expected: JSON with `output` containing Claude's response.
