"""Input-control providers - the cross-platform abstraction.

Per the design lesson: Wayland deliberately blocks input injection, X11 allows
it via xdotool, and other OSes need their own APIs. So we expose ONE interface
and pick the right provider at runtime. The rest of DeskBuddy stays
platform-agnostic.

    Provider.type_text(text)
    Provider.press_key(keys)
    Provider.list_windows()
    Provider.focus_window(title)
    Provider.available() -> (ok, reason)

Providers:
    X11Provider       - xdotool + wmctrl (works great under Xorg / XWayland apps)
    WaylandProvider   - ydotool if ydotoold+uinput available, else honest error
    NullProvider      - no injection possible; explains why (e.g. GNOME Wayland)
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(cmd: list[str], timeout: int = 15) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"ok": p.returncode == 0, "stdout": p.stdout.strip(),
                "stderr": p.stderr.strip()}
    except FileNotFoundError:
        return {"ok": False, "error": f"not found: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timed out"}


class Provider:
    name = "base"

    def available(self) -> tuple[bool, str]:
        return False, "not implemented"

    def type_text(self, text: str) -> dict[str, Any]:
        return {"ok": False, "error": "unsupported"}

    def press_key(self, keys: str) -> dict[str, Any]:
        return {"ok": False, "error": "unsupported"}

    def list_windows(self) -> dict[str, Any]:
        return {"ok": False, "error": "unsupported"}

    def focus_window(self, title: str) -> dict[str, Any]:
        return {"ok": False, "error": "unsupported"}

    def click_at(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        return {"ok": False, "error": "unsupported"}


class X11Provider(Provider):
    name = "x11"

    def available(self) -> tuple[bool, str]:
        if not _have("xdotool"):
            return False, "xdotool not installed"
        if not os.environ.get("DISPLAY"):
            return False, "no DISPLAY (X11 not reachable)"
        return True, "xdotool ready"

    def type_text(self, text):
        return _run(["xdotool", "type", "--clearmodifiers", "--", text])

    def press_key(self, keys):
        return _run(["xdotool", "key", "--clearmodifiers", keys])

    def list_windows(self):
        if _have("wmctrl"):
            return _run(["wmctrl", "-l"])
        return _run(["xdotool", "search", "--name", ""])

    def focus_window(self, title):
        if _have("wmctrl"):
            return _run(["wmctrl", "-a", title])
        r = _run(["xdotool", "search", "--name", title])
        if r["ok"] and r["stdout"]:
            wid = r["stdout"].splitlines()[0]
            return _run(["xdotool", "windowactivate", wid])
        return {"ok": False, "error": f"window not found: {title}"}

    def click_at(self, x, y, button="left"):
        btn = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
        r = _run(["xdotool", "mousemove", str(x), str(y), "click", btn])
        return r if r.get("ok") else {"ok": False, "error": r.get("error") or r.get("stderr")}


class WaylandProvider(Provider):
    name = "wayland"

    def available(self) -> tuple[bool, str]:
        if not _have("ydotool"):
            return False, "ydotool not installed"
        # ydotool needs ydotoold + /dev/uinput; probe cheaply
        if not os.path.exists("/dev/uinput"):
            return False, "/dev/uinput missing (ydotoold can't inject)"
        probe = _run(["ydotool", "key", "0:0"])  # no-op-ish
        if not probe["ok"] and "uinput" in (probe.get("stderr", "") + probe.get("error", "")).lower():
            return False, "ydotoold backend unavailable (uinput not open)"
        return True, "ydotool ready"

    def type_text(self, text):
        if _have("wtype"):
            r = _run(["wtype", text])
            if r["ok"]:
                return r
        return _run(["ydotool", "type", text])

    def press_key(self, keys):
        return _run(["ydotool", "key", keys])

    def list_windows(self):
        # GNOME Wayland exposes windows only via extensions/DBus; not universal.
        return {"ok": False,
                "error": "Wayland hides window lists from apps (security). "
                         "Use X11 session or a GNOME extension for this."}

    def focus_window(self, title):
        return {"ok": False, "error": "window focus blocked under Wayland"}

    def click_at(self, x, y, button="left"):
        btn = {"left": "0xC0", "right": "0xC1", "middle": "0xC2"}.get(button, "0xC0")
        mv = _run(["ydotool", "mousemove", "--absolute", "-x", str(x), "-y", str(y)])
        if not mv.get("ok"):
            # older ydotool syntax fallback
            mv = _run(["ydotool", "mousemove", str(x), str(y)])
        clk = _run(["ydotool", "click", btn])
        if clk.get("ok"):
            return clk
        return {"ok": False, "error": clk.get("error") or clk.get("stderr")
                or "ydotool click failed (needs ydotoold + /dev/uinput)"}


class NullProvider(Provider):
    name = "null"

    def __init__(self, reason: str):
        self.reason = reason

    def available(self):
        return False, self.reason

    def _err(self, *_):
        return {"ok": False, "error": f"no input provider: {self.reason}"}

    type_text = press_key = list_windows = focus_window = click_at = _err  # type: ignore


def get_provider() -> Provider:
    """Pick the best input provider for this machine, right now."""
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    x11, wl = X11Provider(), WaylandProvider()

    # Prefer whichever actually works. On XWayland, xdotool often still works
    # for X11 apps even in a Wayland session, so try it regardless.
    x_ok, x_why = x11.available()
    w_ok, w_why = wl.available()

    if session == "wayland":
        if w_ok:
            return wl
        if x_ok:
            return x11  # XWayland fallback (X11 apps only)
        return NullProvider(
            f"Wayland session; ydotool: {w_why}; xdotool: {x_why}. "
            "Tip: log in with 'Ubuntu on Xorg' for full control, or set up "
            "ydotoold with /dev/uinput access.")
    # X11 (or unknown)
    if x_ok:
        return x11
    if w_ok:
        return wl
    return NullProvider(f"no usable provider (xdotool: {x_why})")
