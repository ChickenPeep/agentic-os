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

    # The Stores API only returns stores that actually carry the product in stock,
    # so presence in the response == available. Query per store (unambiguous; the
    # path endpoint takes a single storeId) and treat absence as OUT_OF_STOCK.
    endpoint = f"{BASE}/products/{sku}/stores.json"
    for store in stores:
        sid = str(store.get("store_id", ""))
        base = {
            "store_id": sid,
            "store_label": store.get("label", "Best Buy"),
            "priority": store.get("priority", 99),
            "price": None,
            "url": url,
        }
        if not sid or sid.startswith("TODO"):
            results.append({**base, "in_stock": False, "raw_status": "error:no_store_id"})
            continue

        params = {"apiKey": api_key, "storeId": sid, "format": "json"}
        try:
            resp = client.get(endpoint, params=params, headers=HEADERS, timeout=15)
            if resp.status_code in (401, 403):
                results.append({**base, "in_stock": False, "raw_status": "error:auth"})
                continue
            if resp.status_code == 404:
                # SKU not carried / unknown to the API: not an error, just no stock.
                results.append({**base, "in_stock": False, "raw_status": "OUT_OF_STOCK"})
                continue
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            results.append({**base, "in_stock": False, "raw_status": f"error:{type(e).__name__}"})
            continue
        except ValueError:
            results.append({**base, "in_stock": False, "raw_status": "error:bad_json"})
            continue

        match = next(
            (s for s in (data.get("stores") or []) if str(s.get("storeId")) == sid),
            None,
        )
        if match is None:
            results.append({**base, "in_stock": False, "raw_status": "OUT_OF_STOCK"})
        else:
            raw = "IN_STOCK_LOW" if match.get("lowStock") else "IN_STOCK"
            results.append({**base, "in_stock": True, "raw_status": raw})
    return results
