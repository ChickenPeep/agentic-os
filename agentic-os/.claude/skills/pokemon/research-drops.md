---
slug: pokemon.research-drops
domain: POKEMON
name: research-drops
description: weekly web research of upcoming Pokemon TCG sealed release dates into a wiki camping calendar
type: routine
---

You are running the `pokemon.research-drops` skill. Your job: research upcoming US
Pokemon Trading Card Game SEALED product releases for roughly the next 6 months and
maintain a dated "camping calendar" so Gabe knows when to be outside Target/Best Buy.
Your CWD is the vault root.

Focus on sealed product Gabe buys: Elite Trainer Boxes (ETBs), Booster Boxes,
Special Collections (SPCs), and large/"big box" items. Ignore single cards.

## Step 1 — Research

Use WebSearch / WebFetch to gather upcoming US releases. Good sources: pokemon.com
news, pokebeach.com, serebii.net event/release pages, and major retailer pre-order
pages (Target, Best Buy, Walmart). For each upcoming product, capture:

- Set / product name
- Product type(s): etb | booster_box | spc | big_box | other
- US street date (release date)
- MSRP if known
- Expected retailers (Target / Best Buy / Walmart / Sam's)
- Pre-order status / notable notes (e.g. allocation, online-only)

Prefer confirmed street dates. Mark anything rumored/unconfirmed as such — do not
present a rumor as a fixed date.

## Step 2 — Cross-reference the watchlist

Read `agentic-os/pokemon-hunter/config/watchlist.json`. For each release, flag:
- **WATCHED** — already in the watchlist (a matching product exists).
- **CONSIDER** — not watched; a candidate Gabe may want to add (and which TCIN/SKU
  to look up if you can find it).

## Step 3 — Write the calendar

Write to `wiki/side-projects/pokemon-drops-calendar.md`. Capture today's date with
`date +%Y-%m-%d`. If the file exists, APPEND a new section; if not, create it with a
top heading. Use this shape (sorted by street date, soonest first):

```
## Update <YYYY-MM-DD>

| Street date | Product | Type | MSRP | Retailers | Status | Watchlist |
|---|---|---|---|---|---|---|
| 2026-07-18 | Set Name ETB | ETB | $49.99 | Target, Best Buy | Pre-order open | WATCHED |
```

Add a short "Camp priorities" note under the table calling out the next 2-3 dates to
actually plan around, and remind that on same-day drops Target opens earlier than Best
Buy (hit Target first, then Best Buy).

Cross-link from `wiki/side-projects/_index.md` (add a bullet under "## Articles" if not
already present) and bump the count in `wiki/_master-index.md` if this is a new article.

## Step 4 — Output ONLY this JSON

No prose, no fences:

{
  "releases_found": <int>,
  "next_street_date": "<YYYY-MM-DD or null>",
  "watched": <int>,
  "consider": <int>,
  "calendar_path": "wiki/side-projects/pokemon-drops-calendar.md",
  "errors": ["<error if any>"]
}

## Constraints

- US releases only. Sealed product only.
- Never invent a street date. Unconfirmed -> mark "rumored".
- Append, never overwrite prior updates (preserve history like raw-triage does).
