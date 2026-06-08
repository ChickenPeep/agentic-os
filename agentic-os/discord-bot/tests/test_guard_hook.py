import guard_hook


def D(tool, **inp):
    return guard_hook.decide(tool, inp)


def test_read_write_edit_allowed():
    assert D("Read", file_path="/x")["allow"] is True
    assert D("Write", file_path="/x", content="y")["allow"] is True
    assert D("Edit", file_path="/x")["allow"] is True


def test_git_commit_and_branch_allowed():
    assert D("Bash", command="git add -A && git commit -m 'wip'")["allow"] is True
    assert D("Bash", command="git checkout -b bot/foo")["allow"] is True
    assert D("Bash", command="git diff --stat")["allow"] is True


def test_git_push_denied():
    r = D("Bash", command="git push -u origin bot/foo")
    assert r["allow"] is False
    assert "approve" in r["reason"].lower()


def test_merge_to_main_denied():
    assert D("Bash", command="git merge bot/foo")["allow"] is False
    assert D("Bash", command="git checkout main")["allow"] is False


def test_deploy_and_launchctl_denied():
    assert D("Bash", command="bash deploy.sh")["allow"] is False
    assert D("Bash", command="launchctl load ~/Library/LaunchAgents/x.plist")["allow"] is False


def test_external_send_denied_but_get_allowed():
    assert D("Bash", command="curl -X POST https://api.x.com/send -d @p")["allow"] is False
    assert D("Bash", command="gh pr create --fill")["allow"] is False
    assert D("Bash", command="curl -s https://redsky.target.com/x")["allow"] is True


def test_unknown_bash_allowed_by_default():
    assert D("Bash", command="python3 -m pytest -q")["allow"] is True


import json
import subprocess
import sys
import os

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "guard_hook.py")


def _run_hook(event: dict) -> dict:
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(event),
                       capture_output=True, text=True, timeout=10)
    return json.loads(p.stdout)


def test_cli_allows_write():
    out = _run_hook({"tool_name": "Write", "tool_input": {"file_path": "/x"}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"


def test_cli_denies_push():
    out = _run_hook({"tool_name": "Bash", "tool_input": {"command": "git push origin x"}})
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "ship it" in out["hookSpecificOutput"]["permissionDecisionReason"].lower()
