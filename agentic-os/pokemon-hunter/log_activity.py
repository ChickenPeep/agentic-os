#!/usr/bin/env python3
"""Write a command-center activity note for a pokemon check tick.

Usage: log_activity.py <status> <summary>
Vault is taken from $VAULT_PATH (set by run.sh). Best-effort; never fails the tick.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import notes
    vault = os.environ.get("VAULT_PATH", "")
    status = sys.argv[1] if len(sys.argv) > 1 else "success"
    summary = sys.argv[2] if len(sys.argv) > 2 else ""
    if vault:
        notes.write_activity(vault, "pokemon.check-stock", status, summary)
except Exception as e:
    print(f"[log_activity] {e}")
