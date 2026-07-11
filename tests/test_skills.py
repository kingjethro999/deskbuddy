"""Skills system: frontmatter parsing, discovery, catalog, body loading."""
from pathlib import Path


def _write_skill(base: Path, cat: str, name: str, desc: str, triggers, body):
    d = base / cat / name
    d.mkdir(parents=True)
    trig = "[" + ", ".join(triggers) + "]"
    (d / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {desc}\ntriggers: {trig}\n---\n{body}\n")


def test_frontmatter_parse():
    from deskbuddy.skills.loader import _parse_frontmatter
    fm, body = _parse_frontmatter(
        "---\nname: x\ndescription: hi\ntriggers: [a, b]\n---\nBODY HERE\n")
    assert fm["name"] == "x"
    assert fm["description"] == "hi"
    assert fm["triggers"] == ["a", "b"]
    assert body.strip() == "BODY HERE"


def test_no_frontmatter_returns_body():
    from deskbuddy.skills.loader import _parse_frontmatter
    fm, body = _parse_frontmatter("just text")
    assert fm == {} and body == "just text"


def test_discover_and_catalog(tmp_path):
    from deskbuddy.skills.loader import discover, catalog, get_body
    _write_skill(tmp_path, "web", "s1", "does one thing", ["a"], "step one")
    _write_skill(tmp_path, "sys", "s2", "does another", ["b"], "step two")
    skills = discover(tmp_path)
    assert set(skills) == {"s1", "s2"}
    cat = catalog(skills)
    assert "s1: does one thing" in cat and "s2: does another" in cat
    assert get_body("s1", skills).strip() == "step one"


def test_bundled_skills_ship():
    """The package must ship its starter skills."""
    from deskbuddy.skills import discover, BUNDLED_SKILLS_DIR
    skills = discover(BUNDLED_SKILLS_DIR)
    assert "web-search" in skills
    assert "system-status" in skills


def test_user_overrides_bundled(tmp_path):
    from deskbuddy.skills.loader import discover
    a = tmp_path / "a"
    b = tmp_path / "b"
    _write_skill(a, "c", "dup", "bundled version", ["x"], "old")
    _write_skill(b, "c", "dup", "user version", ["x"], "new")
    skills = discover(a, b)  # b listed last -> wins
    assert skills["dup"].description == "user version"
    assert skills["dup"].body.strip() == "new"
