# tests/test_idealog.py
import os
import idealog


def test_log_idea_writes_raw_file(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    path = idealog.log_idea("Add a streak counter to Nexum",
                            "https://discord.com/channels/1/2/3",
                            str(raw), now="2026-06-08T12:00:00Z")
    assert os.path.exists(path)
    body = open(path).read()
    assert "Add a streak counter to Nexum" in body
    assert "discord.com/channels/1/2/3" in body


def test_log_run_returns_none_without_env(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("COMMAND_CENTER_BOT_SKILL_ID", raising=False)
    assert idealog.log_run("2026-06-08T12:00:00Z", "received", "hi") is None


def test_log_run_swallows_network_errors(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "http://127.0.0.1:1")  # nothing listening
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "x")
    monkeypatch.setenv("COMMAND_CENTER_BOT_SKILL_ID", "skill-1")
    # Must not raise even though the connection fails.
    assert idealog.log_run("2026-06-08T12:00:00Z", "received", "hi") is None
