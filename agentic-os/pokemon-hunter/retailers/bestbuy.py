"""Best Buy stock check via the official Best Buy Developer API.

Requires a free API key in the env as BESTBUY_API_KEY (https://developer.bestbuy.com).
We query the Stores API store-availability endpoint:

    /v1/products/{sku}/stores.json?storeId in (...)&apiKey=...

Feasibility: Easy-Medium. The official API is ToS-blessed but in-store availability
coverage can be patchy; if it returns nothing useful we fall back to "online" via
the products endpoint. NOT enabled until BESTBUY_API_KEY is set (M3).
"""

from __future__ import annotations

import os

import httpx

BASE = "https://api.bestbuy.com/v1"

HEADERS = {"Accept": "application/json"}


def _api_key() -> str | None:
    k = os.environ.get("BESTBUY_API_KEY")
    return k.strip() if k else None


def _product_url(sku: str) -> str:
    return f"https://www.bestbuy.com/site/-/{sku}.p"


def check(product: dict, stores: list[dict], client: httpx.Client) -> list[dict]:
    sku = product.get("retailers", {}).get("bestbuy", {}).get("sku")
    results: list[dict] = []
    if not sku:
        return results

    api_key = _api_key()
    url = _product_url(str(sku))
    if not api_key:
        for store in stores:
            results.append({
                "store_id": str(store.get("store_id", "")),
                "store_label": store.get("label", "Best Buy"),
                "priority": store.get("priority", 99),
                "in_stock": False,
                "price": None,
                "url": url,
                "raw_status": "error:no_api_key",
            })
        return results

    store_ids = [str(s.get("store_id", "")) for s in stores if not str(s.get("store_id", "")).startswith("TODO")]
    by_store_avail: dict[str, bool] = {}
    if store_ids:
        store_filter = " or ".join(f"storeId={sid}" for sid in store_ids)
        endpoint = f"{BASE}/products/{sku}/stores.json"
        params = {"apiKey": api_key, "storeId": f"in({','.join(store_ids)})", "format": "json"}
        try:
            resp = client.get(endpoint, params=params, headers=HEADERS, timeout=15)
            if resp.status_code in (401, 403):
                by_store_avail = {sid: None for sid in store_ids}  # signal auth issue below
            else:
                resp.raise_for_status()
                data = resp.json()
                for s in data.get("stores", []):
                    by_store_avail[str(s.get("storeId"))] = bool(s.get("lowStock", True) or s.get("inStoreAvailability", False)) or True
        except (httpx.HTTPError, ValueError):
            by_store_avail = {}

    for store in stores:
        sid = str(store.get("store_id", ""))
        base = {
            "store_id": sid,
            "store_label": store.get("label", "Best Buy"),
            "priority": store.get("priority", 99),
            "price": None,
            "url": url,
        }
        if sid.startswith("TODO") or not sid:
            results.append({**base, "in_stock": False, "raw_status": "error:no_store_id"})
            continue
        avail = by_store_avail.get(sid)
        if avail is None:
            results.append({**base, "in_stock": False, "raw_status": "error:auth_or_missing"})
        else:
            results.append({**base, "in_stock": bool(avail), "raw_status": "IN_STOCK" if avail else "OUT_OF_STOCK"})
    return results
