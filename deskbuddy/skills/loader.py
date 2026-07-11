"""DeskBuddy skills - reusable procedural knowledge, Hermes-style.

A skill is a folder with a SKILL.md file:

    skills/<category>/<name>/SKILL.md

SKILL.md has YAML frontmatter + a markdown body:

    ---
    name: open-and-search
    description: Open a browser and search the web for something.
    triggers: [search, google, look up, find online]
    ---
    # Open and search
    1. open_app firefox
    2. wait, then type the query...

Discovery is a recursive glob (like Hermes). The brain gets a compact catalog
(name + description) in its system prompt; when a skill is relevant it loads the
full body via the `use_skill` tool. This works identically whether the brain is
native or the Hermes backend - skills are DeskBuddy's own, not borrowed.

User skills live at ~/.deskbuddy/skills/ ; bundled skills ship with the package.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deskbuddy.config import CONFIG_DIR

USER_SKILLS_DIR = CONFIG_DIR / "skills"
BUNDLED_SKILLS_DIR = Path(__file__).parent / "bundled"


@dataclass
class Skill:
    name: str
    description: str
    triggers: list[str]
    body: str
    path: Path


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body). Minimal YAML: key: value / [a, b]."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_raw = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    fm: dict = {}
    for line in fm_raw.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if val.startswith("[") and val.endswith("]"):
            fm[key] = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
        else:
            fm[key] = val.strip("\"'")
    return fm, body


def _load_one(skill_md: Path) -> Skill | None:
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    fm, body = _parse_frontmatter(text)
    name = fm.get("name") or skill_md.parent.name
    triggers = fm.get("triggers") or []
    if isinstance(triggers, str):
        triggers = [triggers]
    return Skill(
        name=name,
        description=fm.get("description", ""),
        triggers=triggers,
        body=body,
        path=skill_md,
    )


def discover(*dirs: Path) -> dict[str, Skill]:
    """Find all skills under the given dirs (default: bundled + user)."""
    search = list(dirs) or [BUNDLED_SKILLS_DIR, USER_SKILLS_DIR]
    found: dict[str, Skill] = {}
    for base in search:
        if not base.exists():
            continue
        for skill_md in base.rglob("SKILL.md"):
            skill = _load_one(skill_md)
            if skill:
                found[skill.name] = skill  # user dir (later) overrides bundled
    return found


def catalog(skills: dict[str, Skill]) -> str:
    """Compact name + description list for the brain's system prompt."""
    if not skills:
        return "(no skills installed)"
    return "\n".join(f"- {s.name}: {s.description}" for s in skills.values())


def get_body(name: str, skills: dict[str, Skill] | None = None) -> str:
    skills = skills or discover()
    s = skills.get(name)
    return s.body if s else f"(no skill named '{name}')"
