# tests/test_state.py
import os
import state


def test_get_returns_empty_for_unknown(tmp_path):
    s = state.Store(str(tmp_path / "state.json"))
    assert s.get(123) == {}


def test_update_persists_across_instances(tmp_path):
    path = str(tmp_path / "state.json")
    s = state.Store(path)
    s.update(123, session_id="sess-1", branch="bot/foo")
    s2 = state.Store(path)
    got = s2.get(123)
    assert got["session_id"] == "sess-1"
    assert got["branch"] == "bot/foo"


def test_update_merges_fields(tmp_path):
    s = state.Store(str(tmp_path / "state.json"))
    s.update(1, session_id="a")
    s.update(1, branch="bot/b")
    assert s.get(1) == {"session_id": "a", "branch": "bot/b"}


def test_pending_set_and_clear(tmp_path):
    s = state.Store(str(tmp_path / "state.json"))
    s.update(1, pending_action={"type": "push", "branch": "bot/b"})
    assert s.get(1)["pending_action"]["type"] == "push"
    s.clear_pending(1)
    assert s.get(1).get("pending_action") is None
