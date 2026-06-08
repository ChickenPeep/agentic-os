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


def test_build_argv_first_message_uses_session_id():
    argv = runner.build_argv("hello", session_id="uuid-1", resume=False,
                             settings_path="/s.json", model="")
    assert "--session-id" in argv and "uuid-1" in argv
    assert "--resume" not in argv
    assert "-p" in argv and "hello" in argv
    assert argv[argv.index("--output-format") + 1] == "stream-json"
    assert argv[argv.index("--settings") + 1] == "/s.json"


def test_build_argv_resume_uses_resume_flag():
    argv = runner.build_argv("hi again", session_id="uuid-1", resume=True,
                             settings_path="/s.json", model="claude-opus-4-8")
    assert "--resume" in argv and "uuid-1" in argv
    assert "--session-id" not in argv
    assert "--model" in argv and "claude-opus-4-8" in argv
