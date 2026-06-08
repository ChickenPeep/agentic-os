# Pokemon Stock Hunter

A 24/7 in-stock monitor + drop-research tool for sealed Pokemon TCG product, part of the
agentic-os. Checks store-level availability at Target / Best Buy / Walmart / Sam's Club
near Oshkosh, Greenfield/Greendale, and Franklin WI, and pings Discord when something
drops with a "which store to hit first" hint. **No auto-purchase** — monitor + alert +
drop research only.

Domain: `POKEMON`. Host: Mac mini. Skills: `pokemon.check-stock`, `pokemon.research-drops`.

## Layout

```
check_stock.py        # one tick: watchlist x stores -> Discord on rising edge -> exit
state.py              # rising-edge dedup state (data/state.json, gitignored)
notify.py             # Discord webhook embed + camp-order hint
retailers/
  target.py           # RedSky fulfillment (store-level)        [enabled]
  bestbuy.py          # official Best Buy Developer API         [set BESTBUY_API_KEY]
  walmart.py          # M6 (best-effort, online-level)          [not built]
  samsclub.py         # M7 (stretch)                            [not built]
config/
  watchlist.json      # products: name, type, per-retailer SKU/TCIN
  stores.json         # store/club ids + city + camp priority
run.sh                # launchd entry: env + run + Supabase run logging
research-drops.sh     # launchd entry: weekly claude --print -> drops calendar
supabase-seed.sql     # POKEMON skill rows for the dashboard
```

## Setup (on the Mac mini)

1. **Python deps:** `cd agentic-os/pokemon-hunter && python3 -m pip install -r requirements.txt`
2. **Secrets** in `credentials/.env` (or `~/.agentic-os.env`):
   - `DISCORD_POKEMON_WEBHOOK_URL` — create a channel webhook in Discord (Server
     Settings -> Integrations -> Webhooks -> New Webhook -> Copy URL).
   - `BESTBUY_API_KEY` — free at https://developer.bestbuy.com (enables Best Buy).
   - `TARGET_REDSKY_KEY` — optional; only if Target starts returning `error:auth`.
   - `POKEMON_CHECK_STOCK_SKILL_ID` — the Supabase skills.id after seeding (below).
3. **Pin real store ids** in `config/stores.json` (replace every `TODO_*`):
   - Target store number: target.com store locator (the number in the store URL).
   - Best Buy storeId: the Best Buy API `/v1/stores` endpoint, or the store page URL.
4. **Set your watchlist** in `config/watchlist.json` — the TCINs/SKUs in there now are
   **placeholder examples and must be verified** for the exact products you want
   (open the Target product page; the TCIN is the `A-XXXXXXXX` in the URL).
5. **Seed the dashboard:** apply `supabase-seed.sql`, then
   `select id from skills where slug='pokemon.check-stock';` and put that id in the env.
6. **Deploy + schedule (one command):** the vault syncs to the Mac over iCloud, so the
   code is already there. Then run the deploy script ON THE MAC to copy the runtime to
   local disk (`~/agentic-os-server/`), install deps, test, and load both schedulers:
   ```bash
   bash "$HOME/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault/agentic-os/pokemon-hunter/deploy.sh"
   ```
   Re-run `deploy.sh` any time you edit config to push changes to the running copy.
   The skill `.md` files, dashboard, and wiki calendar live in the vault and just sync;
   only this Python runtime + the plists need deploying.

## Test

```bash
python3 check_stock.py    # prints {checked, in_stock, alerts_sent, errors, ts}
```
With a real in-stock TCIN + a real Target store id + a webhook set, a Discord embed
lands on your phone. Run twice: the second run must NOT re-alert (rising-edge dedup).

## Operating

- **Release-day mode:** edit the check-stock plist `StartInterval` to 60-120s, then
  `launchctl unload <plist> && launchctl load <plist>`. Revert after the drop. Never
  below 60s for Target/Best Buy; keep Walmart/Sam's slower (ban risk).
- **Add a product / store:** edit the JSON in `config/` (git-tracked).

## Feasibility & roadmap

| Retailer | Status | Notes |
|---|---|---|
| Target | Built | RedSky fulfillment, store-level. Most reliable. |
| Best Buy | Built (needs key) | Official API; in-store coverage can be patchy. |
| Walmart | M6 | Heavy bot protection; online-level best-effort. |
| Sam's Club | M7 | Membership/login-gated; likely needs a headless browser. |

Next after four-store coverage: a Discord bot (`/check`, `/watch`) replacing the
one-way webhook — see the plan's M7.
