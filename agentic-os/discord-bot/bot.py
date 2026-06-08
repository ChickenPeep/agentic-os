# bot.py
"""Discord Command Center bot: phone -> Claude Code on the Mac mini.

Listens in one allowlisted channel for the owner's messages, logs each idea,
runs Claude headless on a per-conversation branch with the guard hook, streams
progress back, and handles the 'ship it' approval to push + open a PR.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
import uuid

import discord

import helpers
import idealog
import runner
from state import Store

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_config() -> dict:
    with open(os.path.join(HERE, "config.json")) as f:
        return json.load(f)


CFG = _load_config()
VAULT = os.environ.get("VAULT_PATH",
                       "/Users/gabri/Library/Mobile Documents/com~apple~CloudDocs/agentic-os-vault")
TOKEN = os.environ["DISCORD_BOT_TOKEN"]
OWNER_ID = int(os.environ["DISCORD_OWNER_ID"])
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])
SETTINGS_PATH = os.path.join(HERE, "bridge-settings.json")
RAW_DIR = os.path.join(VAULT, "raw")
STATE = Store(os.path.join(HERE, "data", "state.json"))

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
_locks: dict[int, asyncio.Lock] = {}


def _lock(cid: int) -> asyncio.Lock:
    return _locks.setdefault(cid, asyncio.Lock())


@client.event
async def on_ready():
    print(f"command-center bot online as {client.user}")


@client.event
async def on_message(message: discord.Message):
    if message.author.id != OWNER_ID or message.channel.id != CHANNEL_ID:
        return
    text = (message.content or "").strip()
    if not text:
        return

    lock = _lock(message.channel.id)
    if lock.locked():
        await message.channel.send("⏳ queued behind the current task…")
    async with lock:
        if helpers.is_approval(text):
            await _handle_approval(message)
        else:
            await _handle_task(message, text)


async def _handle_task(message: discord.Message, text: str):
    # Best-effort logging (never blocks chat).
    try:
        idealog.log_idea(text, message.jump_url, RAW_DIR)
    except Exception as e:
        print(f"[idealog raw] {e}")
    started = idealog._utcnow()
    run_id = await asyncio.to_thread(idealog.log_run, started, "running", text)

    rec = STATE.get(message.channel.id)
    session_id = rec.get("session_id") or str(uuid.uuid4())
    resume = bool(rec.get("session_id"))
    branch = rec.get("branch") or (CFG["branch_prefix"] + (helpers.slugify(text) or "task"))
    STATE.update(message.channel.id, session_id=session_id, branch=branch)

    placeholder = await message.channel.send("🤔 on it…")

    progress: list[str] = []
    last_edit = {"t": 0.0}

    def on_progress(line: str):
        progress.append(line)
        now = time.time()
        if now - last_edit["t"] >= CFG["progress_edit_min_interval_seconds"]:
            last_edit["t"] = now
            # Future is intentionally not awaited — best-effort edit from the worker thread.
            asyncio.run_coroutine_threadsafe(
                placeholder.edit(content=helpers.format_progress(progress, None)[:1900]),
                client.loop,
            )

    try:
        runner.ensure_branch(VAULT, branch)

        start_ts = time.time()
        hb_stop = asyncio.Event()

        async def _heartbeat():
            while not hb_stop.is_set():
                try:
                    await asyncio.wait_for(hb_stop.wait(), timeout=CFG["heartbeat_seconds"])
                except asyncio.TimeoutError:
                    elapsed = int(time.time() - start_ts)
                    try:
                        await placeholder.edit(
                            content=(helpers.format_progress(progress, None)[:1850]
                                     + f"\n\n⏱️ {elapsed // 60}m{elapsed % 60}s")
                        )
                    except Exception:
                        pass

        hb_task = asyncio.create_task(_heartbeat())
        try:
            result = await asyncio.to_thread(
                runner.run_claude, text,
                session_id=session_id, resume=resume, cwd=VAULT,
                settings_path=SETTINGS_PATH, model=CFG.get("model", ""),
                timeout=CFG["claude_timeout_seconds"], on_progress=on_progress,
            )
        finally:
            hb_stop.set()
            await hb_task

    except Exception as e:
        await placeholder.edit(content=f"⚠️ run failed: {e}")
        if run_id:
            await asyncio.to_thread(idealog.update_run, run_id, "failure", str(e))
        return

    if result.session_id:
        STATE.update(message.channel.id, session_id=result.session_id)

    diff_proc = await asyncio.to_thread(
        subprocess.run,
        ["git", "-C", VAULT, "diff", "--stat", "main...HEAD"],
        capture_output=True, text=True,
    )
    diffstat = diff_proc.stdout.strip()
    summary = result.final_text or "(no output)"
    footer = ""
    if diffstat:
        STATE.update(message.channel.id, pending_action={"type": "push", "branch": branch})
        footer = f"\n\n📦 staged on `{branch}`:\n```\n{diffstat[:600]}\n```\nReply **ship it** to push + open a PR."
    final_msg = helpers.format_progress(progress, summary)[:1700] + footer
    await placeholder.edit(content=final_msg[:1990])
    if run_id:
        await asyncio.to_thread(idealog.update_run, run_id, "failure" if result.is_error else "success", summary)


async def _handle_approval(message: discord.Message):
    rec = STATE.get(message.channel.id)
    pending = rec.get("pending_action")
    if not pending or pending.get("type") != "push":
        await message.channel.send("Nothing staged to ship right now.")
        return
    branch = pending["branch"]
    await message.channel.send(f"🚀 pushing `{branch}` and opening a PR…")
    push = await asyncio.to_thread(
        subprocess.run,
        ["git", "-C", VAULT, "push", "-u", "origin", branch],
        capture_output=True, text=True,
    )
    if push.returncode != 0:
        await message.channel.send(f"⚠️ push failed:\n```\n{push.stderr[-500:]}\n```")
        return
    pr = await asyncio.to_thread(
        subprocess.run,
        ["gh", "pr", "create", "--fill", "--head", branch],
        capture_output=True, text=True,
    )
    STATE.clear_pending(message.channel.id)
    link = pr.stdout.strip() or "(PR created)"
    await message.channel.send(f"✅ shipped. {link}")


if __name__ == "__main__":
    client.run(TOKEN)
