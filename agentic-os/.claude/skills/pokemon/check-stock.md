---
slug: pokemon.check-stock
domain: POKEMON
name: check-stock
description: polls Target/Best Buy/Walmart/Sams for in-stock Pokemon sealed product at WI stores and Discord-alerts on rising edge
type: routine
---

You are the `pokemon.check-stock` routine. It is implemented as a Python service, not
an LLM task — this doc describes how it runs and how to operate/extend it.

## What it does

One tick: load `config/watchlist.json` x `config/stores.json`, query each enabled
retailer for store-level availability, and POST a Discord embed when a product
transitions out-of-stock -> in-stock (rising edge). It dedups via `data/state.json`
and re-alerts only if an item is still in stock after `RE_ALERT_HOURS` (default 6h).

## Where it lives / how it runs

- Code: `agentic-os/pokemon-hunter/` (Python 3, deps `httpx[http2]`, `python-dotenv`).
- Entry: `check_stock.py` (one pass, then exits). launchd re-invokes via `run.sh`.
- Schedule: `launchd/com.agenticos.pokemon.check-stock.plist`, `StartInterval=300`.
- Host: Mac mini. Deployed copy mirrors `~/agentic-os-server/pokemon-hunter/`.

## Env vars (in credentials/.env or ~/.agentic-os.env)

- `DISCORD_POKEMON_WEBHOOK_URL` — required for alerts to actually send.
- `TARGET_REDSKY_KEY` — optional; override if Target returns `error:auth` (key rotated).
- `BESTBUY_API_KEY` — required to enable Best Buy (free at developer.bestbuy.com).
- `POKEMON_CHECK_STOCK_SKILL_ID` — Supabase skills.id (UUID) so run.sh logs runs.
- `RE_ALERT_HOURS` — optional re-alert cooldown (default 6).

## Operating it

- Run manually:  `cd agentic-os/pokemon-hunter && python3 check_stock.py`
- Release-day mode: edit the plist `StartInterval` to 60-120, then
  `launchctl unload <plist> && launchctl load <plist>`. Revert after the drop.
  Never below 60s for Target/Best Buy.
- Add a product: append to `config/watchlist.json` with per-retailer SKU/TCIN.
- Add/fix a store: edit `config/stores.json` (pin real store_id; `priority` = camp order).

## Extending retailers

Each `retailers/<name>.py` exposes `check(product, stores, client) -> [results]`
and must never raise into the caller (return `raw_status="error:..."` instead).
Enable a retailer by adding it to `RETAILERS` in `retailers/__init__.py`.
Rollout: Target (done) -> Best Buy (set BESTBUY_API_KEY) -> Walmart -> Sam's.

## Output

`check_stock.py` prints one JSON line: `{checked, in_stock, alerts_sent, errors, ts}`.
`run.sh` logs a Supabase `runs` row only when noteworthy (alert fired or errors) plus
an hourly heartbeat, to keep the dashboard run history readable.
