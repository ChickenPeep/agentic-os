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


def test_write_activity(tmp_path):
    p = notes.write_activity(str(tmp_path), "pokemon.check-stock", "success",
                             "checked 6, 0 in stock", when="2026-06-08T14:30:00Z")
    assert p.endswith("command-center/activity/2026-06-08-1430-pokemon-check-stock.md")
    c = open(p).read()
    assert "type: activity" in c
    assert "skill: pokemon.check-stock" in c
    assert "status: success" in c
    assert "when: 2026-06-08T14:30:00Z" in c


def test_write_activity_with_branch(tmp_path):
    p = notes.write_activity(str(tmp_path), "command-center.bot", "staged",
                             "built streak counter", when="2026-06-08T14:30:00Z",
                             branch="bot/streak-counter")
    assert 'branch: bot/streak-counter' in open(p).read()


def test_write_idea(tmp_path):
    p = notes.write_idea(str(tmp_path), "Add a streak counter to Nexum",
                         "It should track consecutive workout days.",
                         source="discord", project="nexum",
                         created="2026-06-08T14:32:00Z")
    assert p.endswith("command-center/ideas/2026-06-08-1432-add-a-streak-counter-to-nexum.md")
    c = open(p).read()
    assert "type: idea" in c
    assert 'title: "Add a streak counter to Nexum"' in c
    assert "status: new" in c
    assert "source: discord" in c
    assert "project: nexum" in c
    assert "consecutive workout days" in c
