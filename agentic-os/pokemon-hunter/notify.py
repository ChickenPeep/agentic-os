"""Discord webhook notifier.

v1 is webhook-only (one-way POST, zero hosting). The webhook URL lives in
credentials/.env as DISCORD_POKEMON_WEBHOOK_URL. A real bot (/check, /watch) is a
later upgrade; this module is intentionally simple.
"""

from __future__ import annotations

import os

import httpx

WEBHOOK_ENV = "DISCORD_POKEMON_WEBHOOK_URL"

# Discord embed color (green) as a decimal int.
COLOR_IN_STOCK = 5763719

TYPE_LABELS = {
    "etb": "Elite Trainer Box",
    "booster_box": "Booster Box",
    "spc": "Special Collection",
    "big_box": "Big Box",
    "other": "Sealed",
}


def _webhook_url() -> str | None:
    url = os.environ.get(WEBHOOK_ENV)
    return url.strip() if url else None


def camp_hint(hits: list[dict]) -> str:
    """Given all in-stock hits for ONE product this tick, build a camp-order hint.

    hits: [{store_label, retailer, priority}, ...]. Lower priority = hit first
    (Target opens earliest -> priority 1).
    """
    ordered = sorted(hits, key=lambda h: (h.get("priority", 99), h.get("store_label", "")))
    if len(ordered) == 1:
        return f"In stock at {ordered[0]['store_label']}. Go now."
    parts = [h["store_label"] for h in ordered]
    return "Hit " + " first, then ".join(parts) + "."


def build_embed(product: dict, hits: list[dict]) -> dict:
    """Build a single Discord embed for a product that just went in stock."""
    type_label = TYPE_LABELS.get(product.get("product_type", "other"), "Sealed")
    # Use the first hit for the headline store + product URL.
    primary = sorted(hits, key=lambda h: (h.get("priority", 99),))[0]
    stores_field = "\n".join(
        f"- {h['store_label']}" + (f" (${h['price']})" if h.get("price") else "")
        for h in sorted(hits, key=lambda h: (h.get("priority", 99),))
    )
    embed = {
        "title": f"IN STOCK: {product['name']}",
        "color": COLOR_IN_STOCK,
        "fields": [
            {"name": "Type", "value": type_label, "inline": True},
            {"name": "Retailer(s)", "value": ", ".join(sorted({h["retailer"] for h in hits})), "inline": True},
            {"name": "Where", "value": stores_field, "inline": False},
            {"name": "Go camp / hit first", "value": camp_hint(hits), "inline": False},
        ],
    }
    if primary.get("url"):
        embed["url"] = primary["url"]
    return embed


def send(product: dict, hits: list[dict], *, mention: bool = True) -> bool:
    """POST one embed to Discord for a product. Returns True on success.

    Never raises into the tick loop: a notifier failure is logged and swallowed.
    """
    url = _webhook_url()
    if not url:
        print(f"[notify] {WEBHOOK_ENV} not set; would alert: {product['name']} ({len(hits)} store hits)")
        return False
    payload = {
        "username": "Pokemon Stock Hunter",
        "embeds": [build_embed(product, hits)],
    }
    if mention:
        payload["content"] = "@here"
    try:
        resp = httpx.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        print(f"[notify] Discord POST failed: {e}")
        return False
