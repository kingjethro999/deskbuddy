"""HANDS safety - ported from Hermes' computer_use guard model.

Three tiers (same philosophy as Hermes):
  * SAFE     - read-only actions, always allowed (capture, list, wait).
  * DESTRUCTIVE - mutate visible state; go through approval when
               cfg.hands.confirm_destructive is on (click, type, key, shell).
  * BLOCKED   - hard-refused regardless of approval (logout, force-quit,
               empty-trash, 'curl ... | bash', 'sudo rm -rf', fork-bombs).

Why this matters: DeskBuddy can drive your PC. Without guards it would
happily run `sudo rm -rf /` or log you out via a key combo. These
checks are the floor, not the ceiling.
"""
from __future__ import annotations

import re
from typing import Callable

# Hard-blocked key chords (canonicalized to lower-case tokens).
# Mirrors Hermes' _BLOCKED_KEY_COMBOS - destructive system shortcuts.
_BLOCKED_KEY_COMBOS = {
    frozenset({"cmd", "shift", "backspace"}),    # empty trash
    frozenset({"cmd", "option", "backspace"}),    # force delete
    frozenset({"cmd", "ctrl", "q"}),             # lock screen
    frozenset({"cmd", "shift", "q"}),            # log out
    frozenset({"cmd", "option", "shift", "q"}),  # force log out
    frozenset({"option", "f4"}),                   # win close / log out
    frozenset({"ctrl", "option", "delete"}),        # win task mgr / reset
    frozenset({"ctrl", "option", "del"}),           # alias of above
}

_KEY_ALIASES = {
    "command": "cmd", "control": "ctrl", "alt": "option",
    "windows": "win", "super": "win", "meta": "win",
    "mod": "cmd", "option": "option",
}

# Destructive text patterns for the `type` action. Same intent as Hermes'
# _BLOCKED_TYPE_PATTERNS - refuse shell-killer one-liners.
_BLOCKED_TYPE_PATTERNS = [
    re.compile(r"curl\s+[^|]*\|\s*bash", re.IGNORECASE),
    re.compile(r"curl\s+[^|]*\|\s*sh", re.IGNORECASE),
    re.compile(r"wget\s+[^|]*\|\s*bash", re.IGNORECASE),
    re.compile(r"\bsudo\s+rm\s+-[rf]", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\s+/\s*$", re.IGNORECASE),
    re.compile(r":\s*\(\s*\)\s*\{\s*:|\s*&\s*\}", re.IGNORECASE),  # fork bomb
]


def _canon_key_combo(keys: str) -> frozenset:
    parts = [p.strip().lower() for p in re.split(r"\s*\+\s*", keys) if p.strip()]
    return frozenset(_KEY_ALIASES.get(p, p) for p in parts)


def is_blocked_key_combo(keys: str) -> bool:
    combo = _canon_key_combo(keys)
    return any(b.issubset(combo) and len(b) <= len(combo) for b in _BLOCKED_KEY_COMBOS)


def blocked_type_pattern(text: str) -> str | None:
    for pat in _BLOCKED_TYPE_PATTERNS:
        if pat.search(text or ""):
            return pat.pattern
    return None


# Approval hook. The GUI sets this to pop a confirm dialog; the CLI sets
# it to auto-allow (or prompt). Returns True if allowed to proceed.
_approval_callback: Callable[[str, dict], bool] | None = None


def set_approval_callback(cb: Callable[[str, dict], bool]) -> None:
    global _approval_callback
    _approval_callback = cb


def request_approval(action: str, args: dict) -> str | None:
    """Return None if allowed, else a human-readable refusal reason."""
    cb = _approval_callback
    if cb is None:
        # No callback wired -> default allow (headless/CLI convenience).
        return None
    try:
        allowed = cb(action, args)
    except Exception:
        allowed = False
    return None if allowed else f"denied by user: {action}"


# Actions that mutate user-visible state (need approval when enabled).
DESTRUCTIVE_ACTIONS = frozenset({
    "click", "double_click", "right_click", "middle_click",
    "drag", "scroll", "type", "key", "focus_window", "run_shell",
})
