"""Retailer stock-check modules.

Each module exposes:

    check(product: dict, stores: list[dict], client: httpx.Client) -> list[dict]

returning one result per store:

    {
        "store_id": str,
        "store_label": str,
        "priority": int,
        "in_stock": bool,
        "price": float | None,
        "url": str | None,
        "raw_status": str,   # retailer-native status or an error marker
    }

Modules MUST NOT raise into the caller. On error, return results with
in_stock=False and raw_status set to an error marker (e.g. "error:403") so one
retailer failing never kills the tick or the other retailers.
"""

from . import target  # noqa: F401

# Imported lazily by check_stock.py via RETAILERS; add new modules here as built.
RETAILERS = {
    "target": "retailers.target",
    # "bestbuy": "retailers.bestbuy",   # enabled at M3
    # "walmart": "retailers.walmart",   # M6
    # "samsclub": "retailers.samsclub", # M7
}
