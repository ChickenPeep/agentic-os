"""Persistent per-channel conversation state (session id, branch, pending approval).

Stored as a single JSON file on local disk so memory and pending approvals survive
bot restarts. Keys are stringified channel ids.
"""
from __future__ import annotations

import json
import os
from typing import Any


class Store:
    def __init__(self, path: str):
        self.path = path
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    self._data = json.load(f)
            except (ValueError, OSError):
                self._data = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self._data, f, indent=2)
        os.replace(tmp, self.path)

    def get(self, channel_id: int) -> dict:
        return dict(self._data.get(str(channel_id), {}))

    def update(self, channel_id: int, **fields: Any) -> None:
        rec = self._data.setdefault(str(channel_id), {})
        rec.update(fields)
        self._save()

    def clear_pending(self, channel_id: int) -> None:
        rec = self._data.get(str(channel_id))
        if rec and "pending_action" in rec:
            rec["pending_action"] = None
            self._save()
