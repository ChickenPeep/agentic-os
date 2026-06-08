# tests/test_helpers.py
import helpers


def test_is_approval_matches_words():
    for t in ["ship it", "Ship It", "go", "  do it ", "approved"]:
        assert helpers.is_approval(t) is True
    for t in ["what about ships", "don't ship it yet", "research go-karts"]:
        assert helpers.is_approval(t) is False


def test_slugify():
    assert helpers.slugify("Add a Streak Counter to Nexum!") == "add-a-streak-counter-to-nexum"
    assert helpers.slugify("   spaced   out  ") == "spaced-out"
    assert len(helpers.slugify("word " * 40)) <= 40


def test_format_progress_truncates_and_lists():
    msg = helpers.format_progress(["Edit a.py", "$ git commit -m x"], final=None)
    assert "Edit a.py" in msg
    assert "git commit" in msg
    done = helpers.format_progress(["Edit a.py"], final="All done.")
    assert "All done." in done
