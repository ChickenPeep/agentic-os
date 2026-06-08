# tests/test_runner.py
import json
import runner


def _lines(*events):
    return [json.dumps(e) for e in events]


def test_parses_final_text_and_session():
    lines = _lines(
        {"type": "system", "subtype": "init", "session_id": "sess-9"},
        {"type": "result", "subtype": "success", "result": "Done. Staged on bot/x.",
         "session_id": "sess-9", "is_error": False},
    )
    out = runner.parse_stream_events(lines)
    assert out.final_text == "Done. Staged on bot/x."
    assert out.session_id == "sess-9"
    assert out.is_error is False


def test_collects_tool_use_progress():
    lines = _lines(
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": "a.py"}}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "git commit -m x"}}]}},
        {"type": "result", "subtype": "success", "result": "ok", "session_id": "s", "is_error": False},
    )
    out = runner.parse_stream_events(lines)
    assert "Edit a.py" in out.progress[0]
    assert "git commit" in out.progress[1]


def test_error_result_flagged():
    lines = _lines(
        {"type": "result", "subtype": "error_max_turns", "result": "stopped",
         "session_id": "s", "is_error": True},
    )
    out = runner.parse_stream_events(lines)
    assert out.is_error is True


def test_ignores_malformed_lines():
    out = runner.parse_stream_events(["not json", "", "{bad}"])
    assert out.final_text == ""
    assert out.session_id is None
