# agentic-os-base — n8n setup guide

Phase 1 Task 1.6. Imports the base workflow that receives a webhook, looks up the skill in Supabase, calls the Mac mini endpoint, logs the run, and responds.

---

## Caveats up front (read first)

- **typeVersion numbers** in `agentic-os-base.json` are reasonable defaults for current n8n cloud (Webhook v2, IF v2, HTTP Request v4.2, Supabase v1, Respond to Webhook v1.1). If the cloud instance has shipped newer versions since this file was written, n8n will warn on import and let you accept an upgrade. Accept the upgrade if asked.
- **Webhook body path** is `$json.body.*` for Webhook v2 (e.g. `$json.body.skill_slug`). If your cloud is on an older v1 webhook, the path is just `$json.skill_slug` and you'll need to edit a few expressions in the Get Skill / Insert Run / Respond nodes accordingly.
- **Credential IDs** in the JSON are placeholders (`REPLACE_WITH_*`). After import, n8n will show those nodes as "credentials missing" until you assign the credentials you create in step 2 below. This is normal — no manual JSON edit needed.
- **Supabase node filter shape:** if the import balks at the `filters.conditions[].keyName` shape, just open the Get Skill node and recreate the filter manually in the UI: Filters → Add Condition → field `slug`, operator `eq`, value `={{ $json.body.skill_slug }}`.

---

## 1. Import the workflow

1. Open https://gabrieltorres18.app.n8n.cloud
2. Workflows → top-right menu (`⋯`) → **Import from File**
3. Select `agentic-os/n8n-workflows/agentic-os-base.json` from the vault
4. Workflow opens with 7 nodes. Save it (`⌘S`). Don't activate yet.

---

## 2. Create the two credentials

### 2a. Supabase credential — `Supabase agentic-os`

1. Settings (left sidebar) → **Credentials** → **Add credential**
2. Search "Supabase API" → select it
3. Name: `Supabase agentic-os`
4. Host: `https://ykfjnageewaonunrnwft.supabase.co`
5. Service Role Secret: paste the `SUPABASE_SERVICE_ROLE_KEY` from `credentials/.env`
6. Save

### 2b. Header Auth credential — `Mac agentic-os bearer`

1. Credentials → **Add credential**
2. Search "Header Auth" → select it
3. Name: `Mac agentic-os bearer`
4. Name (header name): `Authorization`
5. Value: `Bearer <AGENTIC_OS_API_KEY>` — the actual key lives at `~/.agentic-os.env` on the Mac (chmod 600, NOT in iCloud). On the Mac: `printf "Bearer %s" "$(grep '^AGENTIC_OS_API_KEY=' ~/.agentic-os.env | cut -d= -f2-)" | pbcopy` then paste here. Do NOT put the literal value back in this file — it's in the iCloud-synced vault.
6. Save

---

## 3. Wire the credentials into the workflow

Back in the `agentic-os-base` workflow:

| Node | Credential |
|---|---|
| Supabase: Get Skill | `Supabase agentic-os` |
| Supabase: Insert Run | `Supabase agentic-os` |
| HTTP: Call Mac | `Mac agentic-os bearer` |

Open each node, pick the credential from the dropdown, save the node, save the workflow.

---

## 4. Activate

1. Top-right toggle: **Active** → on
2. Click the **Webhook** node → copy the **Production URL** (looks like `https://gabrieltorres18.app.n8n.cloud/webhook/agentic-os-skill-run`)

---

## 5. End-to-end smoke test

You need a real `skills` row to test against. Insert a stub via the Supabase SQL editor:

```sql
insert into skills (domain, name, slug, description, type, status, host)
values ('MEMORY', 'echo test', 'memory.echo-test', 'returns whatever it gets', 'skill', 'active', 'mac')
returning id, slug;
```

Then from any machine with curl:

```bash
curl -X POST 'https://gabrieltorres18.app.n8n.cloud/webhook/agentic-os-skill-run' \
  -H 'Content-Type: application/json' \
  -d '{
    "skill_slug": "memory.echo-test",
    "prompt": "reply with the literal text PONG and nothing else",
    "triggered_by": "manual"
  }'
```

Expected response shape:

```json
{
  "output": "PONG\n",
  "run_id": "<uuid>",
  "skill_slug": "memory.echo-test"
}
```

Then verify the run was logged:

```sql
select id, skill_id, status, output, triggered_by, host, started_at
from runs
order by started_at desc
limit 5;
```

You should see one new row with `status='success'`, `host='mac'`, and your prompt's output.

---

## 6. Negative test — inactive skill returns 400

```sql
update skills set status = 'paused' where slug = 'memory.echo-test';
```

Re-run the curl above. Expect HTTP 400 with body:

```json
{ "error": "skill not active", "skill_slug": "memory.echo-test", "status": "paused" }
```

Re-activate when done:

```sql
update skills set status = 'active' where slug = 'memory.echo-test';
```

---

## What this unlocks

Phase 1 is done. The chain works:

```
[any client] → [n8n cloud webhook] → [Supabase lookup] → [Mac launchd service :4242] → [claude --print] → [back to n8n] → [Supabase runs row] → [response]
```

From here Phase 2 can build a Next.js dashboard that POSTs to this same `/skill-run` endpoint per skill card, and Phase 4 can do the same from a Telegram bot.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| 401 from Mac | Bearer value in `Mac agentic-os bearer` credential doesn't match `AGENTIC_OS_API_KEY` in the Mac plist. Re-copy from `~/.agentic-os.env` on the Mac. |
| `claude: command not found` in `output` | The plist's `PATH` env var isn't set. Re-edit `~/Library/LaunchAgents/com.agenticos.server.plist` to ensure the `PATH` entry includes `/opt/homebrew/bin`, then `launchctl unload && launchctl load`. |
| Mac call times out | First-run claude can take 30s+. The HTTP node has a 120s timeout. If it still times out, SSH to Mac and run `curl http://localhost:4242/health`. |
| Supabase node says "no rows returned" | Either the slug doesn't exist in `skills` or the filter expression isn't being evaluated. Check `$('Webhook').item.json.body.skill_slug` actually has a value in the execution view. |
| Webhook 404 | Workflow is not active, or you're hitting the test URL instead of the production URL. Toggle Active on and use the Production URL. |
