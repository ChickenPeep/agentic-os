"""Target stock check via RedSky fulfillment API.

Store-level availability by TCIN + store_id. The anonymous web `key` occasionally
rotates; override via TARGET_REDSKY_KEY in the env if Target starts returning auth
errors (you'll see raw_status="error:auth").

Feasibility: Easy. This is the most reliable unattended source.
"""

from __future__ import annotations

import os

import httpx

# NOTE: Target retired pdp_fulfillment_v1 (now returns HTTP 410 Gone). The current
# store-level fulfillment operation is product_fulfillment_v1 (same response shape:
# data.product.fulfillment.store_options[].{in_store_only,order_pickup,ship_to_store}).
FULFILLMENT_URL = "https://redsky.target.com/redsky_aggregations/v1/web/product_fulfillment_v1"

# Known anonymous web key. Rotates occasionally -> override with TARGET_REDSKY_KEY.
DEFAULT_KEY = "9f36aeafbe60771e321a7cc95a78140772ab3e96"

# Wisconsin defaults for the fulfillment query context.
DEFAULT_ZIP = os.environ.get("TARGET_ZIP", "53132")  # Franklin WI
DEFAULT_STATE = os.environ.get("TARGET_STATE", "WI")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Origin": "https://www.target.com",
    "Referer": "https://www.target.com/",
}


def _key() -> str:
    return os.environ.get("TARGET_REDSKY_KEY", DEFAULT_KEY)


def _product_url(tcin: str) -> str:
    return f"https://www.target.com/p/-/A-{tcin}"


def _parse_store_option(opt: dict) -> tuple[bool, str]:
    """Return (in_stock, raw_status) for one store_option entry."""
    statuses = []
    for channel in ("in_store_only", "order_pickup", "curbside", "ship_to_store"):
        node = opt.get(channel)
        if isinstance(node, dict):
            s = node.get("availability_status")
            if s:
                statuses.append(s)
    in_stock = any(s == "IN_STOCK" for s in statuses)
    raw = ",".join(statuses) if statuses else "UNKNOWN"
    return in_stock, raw


def check(product: dict, stores: list[dict], client: httpx.Client) -> list[dict]:
    tcin = product.get("retailers", {}).get("target", {}).get("tcin")
    results: list[dict] = []
    if not tcin:
        return results

    url = _product_url(str(tcin))
    for store in stores:
        store_id = str(store.get("store_id", ""))
        base = {
            "store_id": store_id,
            "store_label": store.get("label", f"Target {store_id}"),
            "priority": store.get("priority", 99),
            "price": None,
            "url": url,
        }
        if not store_id or store_id.startswith("TODO"):
            results.append({**base, "in_stock": False, "raw_status": "error:no_store_id"})
            continue

        params = {
            "key": _key(),
            "tcin": str(tcin),
            "store_id": store_id,
            "pricing_store_id": store_id,
            "zip": DEFAULT_ZIP,
            "state": DEFAULT_STATE,
            "has_required_store_id": "true",
        }
        try:
            resp = client.get(FULFILLMENT_URL, params=params, headers=HEADERS, timeout=15)
            if resp.status_code in (401, 403):
                results.append({**base, "in_stock": False, "raw_status": "error:auth"})
                continue
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            results.append({**base, "in_stock": False, "raw_status": f"error:{type(e).__name__}"})
            continue
        except ValueError:
            results.append({**base, "in_stock": False, "raw_status": "error:bad_json"})
            continue

        fulfillment = (
            data.get("data", {})
            .get("product", {})
            .get("fulfillment", {})
        )
        store_options = fulfillment.get("store_options") or []
        match = next(
            (o for o in store_options if str(o.get("location_id")) == store_id),
            store_options[0] if store_options else None,
        )
        if match is None:
            results.append({**base, "in_stock": False, "raw_status": "no_store_option"})
            continue
        in_stock, raw = _parse_store_option(match)
        results.append({**base, "in_stock": in_stock, "raw_status": raw})

    return results
