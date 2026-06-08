# agentic-os/discord-bot/tests/test_idealog.py
import os
import idealog


def test_capture_idea_writes_note(tmp_path):
    p = idealog.capture_idea(str(tmp_path), "Add streak counter to Nexum",
                             "https://discord.com/channels/1/2/3")
    assert "command-center/ideas/" in p
    c = open(p).read()
    assert "type: idea" in c
    assert "source: discord" in c
    assert "discord.com/channels/1/2/3" in c


def test_log_activity_writes_note(tmp_path):
    p = idealog.log_activity(str(tmp_path), "success", "built it", branch="bot/x")
    c = open(p).read()
    assert "type: activity" in c
    assert "skill: command-center.bot" in c
    assert "status: success" in c
    assert "branch: bot/x" in c


def test_logging_never_raises(tmp_path, monkeypatch):
    # even if note writing fails, callers must not crash
    monkeypatch.setattr(idealog.notes, "write_idea",
                        lambda *a, **k: (_ for _ in ()).throw(IOError("boom")))
    assert idealog.capture_idea(str(tmp_path), "x", "u") is None
