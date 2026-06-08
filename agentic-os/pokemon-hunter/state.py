"""Persistent last-seen stock state for rising-edge dedup.

State lives in data/state.json (gitignored), keyed by "product_id|retailer|store_id".
We only alert on an out_of_stock -> in_stock transition, and re-alert if a product
is still in stock after RE_ALERT_HOURS (so a drop we already pinged, that is still
sitting on the shelf hours later, nudges again).

Writes are crash-safe: write a temp file then os.replace (atomic on the same fs).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
STATE_PATH = DATA_DIR / "state.json"
RE_ALERT_HOURS = float(os.environ.get("RE_ALERT_HOURS", "6"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def key(product_id: str, retailer: str, store_id: str) -> str:
    return f"{product_id}|{retailer}|{store_id}"


def load() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        with STATE_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Corrupt/partial state should never crash a tick; start fresh.
        return {}


def save(state: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(tmp, STATE_PATH)


def should_alert(state: dict, k: str, in_stock: bool) -> bool:
    """Decide whether this observation is alert-worthy, given prior state."""
    prev = state.get(k)
    if not in_stock:
        return False
    if prev is None or not prev.get("in_stock"):
        # rising edge: was missing/out-of-stock, now in stock
        return True
    # Still in stock since last time -> only re-alert past the cooldown.
    last_alert = prev.get("last_alert_at")
    if not last_alert:
        return True
    try:
        last_dt = datetime.fromisoformat(last_alert)
    except ValueError:
        return True
    hours = (_now() - last_dt).total_seconds() / 3600.0
    return hours >= RE_ALERT_HOURS


def update(state: dict, k: str, in_stock: bool, alerted: bool) -> None:
    """Record the new observation for key k after a tick."""
    now_iso = _iso(_now())
    prev = state.get(k, {})
    if in_stock:
        since = prev.get("since") if prev.get("in_stock") else now_iso
        last_alert = now_iso if alerted else prev.get("last_alert_at")
        state[k] = {"in_stock": True, "since": since, "last_alert_at": last_alert}
    else:
        state[k] = {"in_stock": False, "since": None, "last_alert_at": prev.get("last_alert_at")}
