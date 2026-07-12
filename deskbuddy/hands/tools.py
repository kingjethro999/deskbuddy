"""HANDS - PC control layer.

Each tool is a plain Python function with a JSON schema the brain can call.
Input injection is abstracted so it works on both Wayland (ydotool/wtype) and
X11 (xdotool). Everything degrades gracefully when a helper is missing.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable


def _session_type() -> str:
    return os.environ.get("XDG_SESSION_TYPE", "").lower()


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# Per-tool availability probes (the Hermes `check_fn` idea): only advertise a
# tool when the machine can actually run it. Keeps the model from calling a
# tool that will just fail (e.g. type_text on Wayland with no ydotool).
def _type_text_ok() -> bool:
    from deskbuddy.hands.providers import get_provider
    return get_provider().available()[0]

def _press_key_ok() -> bool:
    return _type_text_ok() or _have("xdotool")

def _list_windows_ok() -> bool:
    return _have("wmctrl") or (_session_type() == "x11")

def _focus_window_ok() -> bool:
    return _have("wmctrl") or _have("xdotool")

def _click_ok() -> bool:
    return _type_text_ok()

def _screenshot_ok() -> bool:
    return _have("grim") or _have("gnome-screenshot") or _have("scrot")

def _vision_ok() -> bool:
    if not _screenshot_ok():
        return False
    try:
        import openai  # noqa: F401
        return bool(openai is not None)
    except Exception:
        return False


_TOOL_CHECKS: dict[str, Callable[[], bool]] = {
    "type_text": _type_text_ok,
    "press_key": _press_key_ok,
    "list_windows": _list_windows_ok,
    "focus_window": _focus_window_ok,
    "click_at": _click_ok,
    "look_and_click": _click_ok,
    "screenshot": _screenshot_ok,
    "see_screen": _vision_ok,
}


def tool_available(name: str) -> bool:
    """True if a tool's environment requirements are met right now."""
    check = _TOOL_CHECKS.get(name)
    return True if check is None else bool(check())


def _run(cmd: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"ok": p.returncode == 0, "stdout": p.stdout.strip(),
                "stderr": p.stderr.strip(), "code": p.returncode}
    except FileNotFoundError:
        return {"ok": False, "error": f"command not found: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timed out after {timeout}s"}


# ---- tool implementations -------------------------------------------------

def _resolve_app(name: str) -> str | None:
    """Resolve a human app name to a launchable command.

    Order: PATH binary -> .desktop id (gtk-launch) -> fuzzy match over
    installed .desktop files (so 'antigravity' finds 'com.antigravity' etc).
    """
    base = name.strip().lower()
    # 1) direct binary on PATH
    if _have(base.split()[0]):
        return name
    # 2) .desktop id passed directly
    if base.endswith(".desktop"):
        return f"gtk-launch {base}" if _have("gtk-launch") else None
    # 3) fuzzy scan of installed .desktop files
    search_dirs = [
        Path.home() / ".local/share/applications",
        Path("/usr/share/applications"),
        Path("/var/lib/flatpak/exports/share/applications"),
        Path.home() / ".local/share/flatpak/exports/share/applications",
    ]
    cands: list[tuple[float, str, str]] = []  # (score, launch_cmd, display)
    import re as _re
    norm = _re.compile(r"[^a-z0-9]+")
    for d in search_dirs:
        if not d.is_dir():
            continue
        for f in d.glob("*.desktop"):
            txt = f.read_text(errors="replace")
            if "NoDisplay=true" in txt:
                continue
            # pull Name= / GenericName= for matching
            names = []
            for line in txt.splitlines():
                if line.startswith("Name=") or line.startswith("GenericName="):
                    names.append(line.split("=", 1)[1].strip().lower())
            desktop_id = f.name
            hay = norm.sub(" ", desktop_id.lower() + " " + " ".join(names))
            if base in hay:
                score = 1.0
            else:
                # partial token overlap
                toks = set(base.split()) & set(hay.split())
                score = len(toks) / max(1, len(base.split()))
            if score > 0:
                launch = f"gtk-launch {desktop_id}" if _have("gtk-launch") else name
                cands.append((score, launch, desktop_id))
    if cands:
        cands.sort(reverse=True)
        return cands[0][1]
    return None


def open_app(name: str) -> dict[str, Any]:
    """Launch an application by name, command, or .desktop id.

    Resolves fuzzy human names (e.g. 'antigravity' -> its .desktop id)
    so voice commands like "open antigravity" actually work.
    """
    cmd = _resolve_app(name)
    if not cmd:
        return {"ok": False, "error": f"'{name}' not found as an app or command"}
    try:
        subprocess.Popen(cmd.split(), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "launched": name, "via": cmd}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def run_shell(command: str) -> dict[str, Any]:
    """Run a shell command and return its output."""
    return _run(["bash", "-lc", command], timeout=60)


def _provider():
    # lazy import to avoid a hard dependency at module load
    from deskbuddy.hands.providers import get_provider
    return get_provider()


def type_text(text: str) -> dict[str, Any]:
    """Type text into the currently focused window (via best input provider)."""
    return _provider().type_text(text)


def press_key(keys: str) -> dict[str, Any]:
    """Press a key or chord, e.g. 'Return', 'ctrl+c', 'super'."""
    return _provider().press_key(keys)


def list_windows() -> dict[str, Any]:
    """List open windows (provider-dependent; Wayland restricts this)."""
    return _provider().list_windows()


def focus_window(title: str) -> dict[str, Any]:
    """Bring a window matching `title` to the foreground."""
    return _provider().focus_window(title)


def read_file_tool(path: str, max_bytes: int = 4000) -> dict[str, Any]:
    """Read a text file so DeskBuddy can talk about its contents."""
    p = Path(path).expanduser()
    if not p.exists():
        return {"ok": False, "error": f"no such file: {path}"}
    try:
        data = p.read_text(errors="replace")[:max_bytes]
        return {"ok": True, "path": str(p), "content": data}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}


def list_dir(path: str = "~") -> dict[str, Any]:
    """List the contents of a directory."""
    p = Path(path).expanduser()
    if not p.is_dir():
        return {"ok": False, "error": f"not a directory: {path}"}
    return {"ok": True, "path": str(p), "entries": sorted(os.listdir(p))[:200]}


def screenshot(path: str = "~/deskbuddy-screen.png") -> dict[str, Any]:
    """Capture the screen to a PNG (for the vision model to inspect later)."""
    out = str(Path(path).expanduser())
    for tool, args in (
        ("grim", [out]),                       # wayland
        ("gnome-screenshot", ["-f", out]),
        ("scrot", [out]),                      # x11
        ("import", ["-window", "root", out]),  # imagemagick x11
    ):
        if _have(tool):
            r = _run([tool, *args])
            if r.get("ok"):
                return {"ok": True, "path": out, "via": tool}
    return {"ok": False, "error": "no screenshot tool (install grim on Wayland)"}


def use_skill(name: str) -> dict[str, Any]:
    """Load the full instructions for one of DeskBuddy's skills by name."""
    from deskbuddy.skills import discover, get_body
    skills = discover()
    if name not in skills:
        return {"ok": False, "error": f"no skill '{name}'",
                "available": list(skills)}
    return {"ok": True, "name": name, "instructions": get_body(name, skills)}


def see_screen(question: str = "Describe what is on screen.") -> dict[str, Any]:
    """Screenshot the screen and ask the configured vision model about it.

    Enables hands-off 'look and act': the brain can ask where a button is, read
    on-screen text, or decide what to click next. Uses the same OpenAI-compatible
    endpoint as the native brain (vision-capable model required).
    """
    shot = screenshot("~/.deskbuddy/last-screen.png")
    if not shot.get("ok"):
        return shot
    try:
        import base64
        from deskbuddy.config import Config
        from openai import OpenAI
        cfg = Config.load()
        img = Path(shot["path"]).read_bytes()
        b64 = base64.b64encode(img).decode()
        client = OpenAI(base_url=cfg.brain.base_url,
                        api_key=cfg.api_key() or "not-needed")
        resp = client.chat.completions.create(
            model=cfg.brain.model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": question},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
        )
        return {"ok": True, "answer": resp.choices[0].message.content,
                "screenshot": shot["path"]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"vision failed: {e}",
                "screenshot": shot.get("path")}


def click_at(x: int, y: int, button: str = "left") -> dict[str, Any]:
    """Move the pointer to (x, y) and click. Uses the runtime input provider."""
    return _provider().click_at(int(x), int(y), button)


def look_and_click(target: str) -> dict[str, Any]:
    """Vision-guided click: screenshot, ask the model WHERE `target` is, click it.

    The model returns pixel coordinates; we click them. This is DeskBuddy's
    hands-off 'see the button, press the button' primitive.
    """
    shot = screenshot("~/.deskbuddy/last-screen.png")
    if not shot.get("ok"):
        return shot
    try:
        import base64
        import json as _json
        import re
        from PIL import Image  # pillow ships with most stacks; optional
        from deskbuddy.config import Config
        from openai import OpenAI
        cfg = Config.load()
        img_path = Path(shot["path"])
        b64 = base64.b64encode(img_path.read_bytes()).decode()
        try:
            w, h = Image.open(img_path).size
        except Exception:  # noqa: BLE001
            w = h = None
        client = OpenAI(base_url=cfg.brain.base_url,
                        api_key=cfg.api_key() or "not-needed")
        prompt = (
            f"The screenshot is {w}x{h} pixels. Find the UI element best matching: "
            f"\"{target}\". Respond ONLY with compact JSON "
            f"{{\"x\": <int>, \"y\": <int>, \"found\": <bool>}} giving the pixel "
            f"center to click. If not visible, found=false.")
        resp = client.chat.completions.create(
            model=cfg.brain.model,
            messages=[{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}],
        )
        raw = resp.choices[0].message.content or ""
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return {"ok": False, "error": "model gave no coordinates", "raw": raw}
        coords = _json.loads(m.group(0))
        if not coords.get("found", True):
            return {"ok": False, "error": f"'{target}' not visible on screen"}
        x, y = int(coords["x"]), int(coords["y"])
        res = _provider().click_at(x, y)
        res.update({"target": target, "x": x, "y": y})
        return res
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"look_and_click failed: {e}"}


# ---- registry -------------------------------------------------------------

# Each entry: (callable, json-schema description for the LLM)
REGISTRY: dict[str, tuple[Callable[..., dict], dict]] = {
    "open_app": (open_app, {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Launch a desktop application by command name.",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string", "description": "app command, e.g. firefox"}},
                "required": ["name"]},
        }}),
    "run_shell": (run_shell, {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a bash command on the user's PC and return output.",
            "parameters": {"type": "object", "properties": {
                "command": {"type": "string"}}, "required": ["command"]},
        }}),
    "type_text": (type_text, {
        "type": "function",
        "function": {
            "name": "type_text",
            "description": "Type text into the currently focused window.",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string"}}, "required": ["text"]},
        }}),
    "press_key": (press_key, {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "Press a key or chord like 'Return' or 'ctrl+c'.",
            "parameters": {"type": "object", "properties": {
                "keys": {"type": "string"}}, "required": ["keys"]},
        }}),
    "list_windows": (list_windows, {
        "type": "function",
        "function": {"name": "list_windows",
            "description": "List open windows.",
            "parameters": {"type": "object", "properties": {}}},
        }),
    "focus_window": (focus_window, {
        "type": "function",
        "function": {
            "name": "focus_window",
            "description": "Bring a window matching a title to the foreground.",
            "parameters": {"type": "object", "properties": {
                "title": {"type": "string"}}, "required": ["title"]},
        }}),
    "read_file": (read_file_tool, {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file's contents.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}}, "required": ["path"]},
        }}),
    "list_dir": (list_dir, {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List a directory's contents.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}}},
        }}),
    "screenshot": (screenshot, {
        "type": "function",
        "function": {
            "name": "screenshot",
            "description": "Capture the screen to a PNG file.",
            "parameters": {"type": "object", "properties": {
                "path": {"type": "string"}}},
        }}),
    "see_screen": (see_screen, {
        "type": "function",
        "function": {
            "name": "see_screen",
            "description": "Look at the screen: screenshot it and ask a vision "
                           "model a question (what's shown, where a button is, "
                           "read text). Use before clicking to decide what to do.",
            "parameters": {"type": "object", "properties": {
                "question": {"type": "string"}}},
        }}),
    "use_skill": (use_skill, {
        "type": "function",
        "function": {
            "name": "use_skill",
            "description": "Load the full step-by-step instructions for one of "
                           "DeskBuddy's skills (see the skill catalog in your "
                           "system prompt), then follow them.",
            "parameters": {"type": "object", "properties": {
                "name": {"type": "string"}}, "required": ["name"]},
        }}),
    "click_at": (click_at, {
        "type": "function",
        "function": {
            "name": "click_at",
            "description": "Click the mouse at exact pixel coordinates (x, y). "
                           "Use when you already know where to click.",
            "parameters": {"type": "object", "properties": {
                "x": {"type": "integer"}, "y": {"type": "integer"},
                "button": {"type": "string", "enum": ["left", "right", "middle"]}},
                "required": ["x", "y"]},
        }}),
    "look_and_click": (look_and_click, {
        "type": "function",
        "function": {
            "name": "look_and_click",
            "description": "Vision-guided click: describe a UI element (e.g. "
                           "'the blue Sign In button') and DeskBuddy screenshots "
                           "the screen, finds it with the vision model, and clicks "
                           "it. The hands-off way to press on-screen things.",
            "parameters": {"type": "object", "properties": {
                "target": {"type": "string"}}, "required": ["target"]},
        }}),
}


def tool_schemas() -> list[dict]:
    """OpenAI-style tools array for the brain."""
    return [schema for _, schema in REGISTRY.values()]


def call_tool(name: str, arguments: dict) -> dict[str, Any]:
    if name not in REGISTRY:
        return {"ok": False, "error": f"unknown tool: {name}"}
    fn, _ = REGISTRY[name]
    try:
        return fn(**(arguments or {}))
    except TypeError as e:
        return {"ok": False, "error": f"bad arguments: {e}"}
