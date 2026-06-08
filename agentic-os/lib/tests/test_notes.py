import re
import notes


def test_slugify():
    assert notes._slugify("Add a Streak Counter!") == "add-a-streak-counter"
    assert notes._slugify("   ") == "untitled"
    assert len(notes._slugify("word " * 40)) <= 50


def test_stamp_from_iso():
    assert notes._stamp("2026-06-08T14:30:00Z") == "2026-06-08-1430"
    # bad input falls back to a valid stamp shape
    assert re.match(r"\d{4}-\d{2}-\d{2}-\d{4}", notes._stamp("garbage"))


def test_write_note_roundtrip(tmp_path):
    p = notes._write_note(str(tmp_path / "a" / "n.md"),
                          {"type": "idea", "title": "Hi: there"}, "body text")
    content = open(p).read()
    assert content.startswith("---\n")
    assert 'title: "Hi: there"' in content   # value with ':' gets quoted
    assert "type: idea" in content
    assert content.rstrip().endswith("body text")
