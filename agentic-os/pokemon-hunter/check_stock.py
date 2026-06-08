#!/usr/bin/env python3
"""Pokemon Stock Hunter — one tick.

Loops the watchlist x stores across all enabled retailers, alerts Discord on
rising-edge in-stock transitions, updates dedup state, and prints a one-line JSON
summary (consumed by run.sh for Supabase run logging).

Designed to be invoked by launchd on a schedule (it does one pass then exits).
Run manually for testing:  python3 check_stock.py
"""

from __future__ import annotations

import importlib
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

import notify
import state as state_mod
from retailers import RETAILERS

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_dotenv() -> None:
    """Best-effort: load credentials/.env so DISCORD/TARGET/BESTBUY vars are present.

    run.sh already sources env on the Mac; this makes manual runs work too.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for candidate in (ROOT.parent.parent / "credentials" / ".env", ROOT / ".env"):
        if candidate.exists():
            load_dotenv(candidate, override=False)


def _new_client() -> httpx.Client:
    """HTTP/2 helps blend in with browsers, but falls back if `h2` isn't installed."""
    try:
        return httpx.Client(http2=True, follow_redirects=True)
    except ImportError:
        return httpx.Client(http2=False, follow_redirects=True)


def run_tick() -> dict:
    watchlist = [p for p in _load_json(CONFIG / "watchlist.json") if p.get("active", True)]
    stores_by_retailer = _load_json(CONFIG / "stores.json")
    st = state_mod.load()

    checked = 0
    in_stock_count = 0
    alerts_sent = 0
    errors: list[str] = []

    with _new_client() as client:
        for retailer, module_path in RETAILERS.items():
            stores = [s for s in stores_by_retailer.get(retailer, []) if isinstance(s, dict)]
            if not stores:
                continue
            try:
                module = importlib.import_module(module_path)
            except ImportError as e:
                errors.append(f"{retailer}:import:{e}")
                continue

            for product in watchlist:
                if retailer not in product.get("retailers", {}):
                    continue
                try:
                    results = module.check(product, stores, client)
                except Exception as e:  # a retailer module must never kill the tick
                    errors.append(f"{retailer}:{product['id']}:{type(e).__name__}")
                    continue

                hits_to_alert: list[dict] = []
                for r in results:
                    checked += 1
                    if r.get("raw_status", "").startswith("error:"):
                        errors.append(f"{retailer}:{product['id']}:{r['store_id']}:{r['raw_status']}")
                    in_stock = bool(r.get("in_stock"))
                    if in_stock:
                        in_stock_count += 1
                    k = state_mod.key(product["id"], retailer, r["store_id"])
                    alert = state_mod.should_alert(st, k, in_stock)
                    if alert:
                        hits_to_alert.append({**r, "retailer": retailer})
                    state_mod.update(st, k, in_stock, alerted=alert)

                if hits_to_alert:
                    ok = notify.send(product, hits_to_alert)
                    if ok:
                        alerts_sent += 1

    state_mod.save(st)
    return {
        "checked": checked,
        "in_stock": in_stock_count,
        "alerts_sent": alerts_sent,
        "errors": errors,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    _load_dotenv()
    # Start jitter to avoid hammering retailers on a fixed cadence.
    if os.environ.get("HUNTER_NO_JITTER") != "1":
        time.sleep(random.uniform(0, 30))
    summary = run_tick()
    # Single-line JSON summary on stdout for run.sh / Supabase logging.
    print(json.dumps(summary))
    # Exit non-zero only on total failure (nothing checked), so launchd logs stay clean.
    return 0 if summary["checked"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
