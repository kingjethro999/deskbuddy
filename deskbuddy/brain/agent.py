"""BRAIN - the agent. Pluggable backends behind one interface.

Backend protocol:
    class Brain:
        def respond(self, user_text: str) -> str: ...   # returns spoken reply

Two implementations:
    NativeBrain  - our own OpenAI-compatible tool-calling loop (option 1).
    HermesBrain  - shells out to the `hermes` CLI as the engine (option 2).

The wizard picks one via config.brain.backend.

Design notes (borrowed from studying Hermes' run_agent.py + tools/registry.py):
- Tools are only ADVERTISED when their environment probe passes (check_fn).
  Shipping every tool on every call is wasteful and confuses the model when
  the tool can't actually work (e.g. type_text on Wayland without ydotool).
- Role alternation is sacred: never two same-role messages in a row, never a
  synthetic user message injected mid-loop. Providers reject bad transcripts.
- The loop caps at max_steps; if it hits the cap it returns a final spoken
  answer rather than hanging or erroring.
- Tool errors are fed BACK to the model so it can recover (the "full ride").
"""
from __future__ import annotations

import json
import shutil
import subprocess
from typing import Protocol

from deskbuddy.config import Config
from deskbuddy.hands import tool_schemas, call_tool, tool_available


class Brain(Protocol):
    def respond(self, user_text: str) -> str: ...


# --------------------------------------------------------------------------
# Native backend: our own agent loop
# --------------------------------------------------------------------------
class NativeBrain:
    """A lean OpenAI-compatible tool-calling loop. DeskBuddy's own engine."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        from openai import OpenAI  # lazy import so --help works without deps
        key = cfg.api_key() or "not-needed-for-local"
        # Build the client ONCE (Hermes reuses a single client too).
        self.client = OpenAI(base_url=cfg.brain.base_url, api_key=key)
        self.model = cfg.brain.model
        # Inject DeskBuddy's own skill catalog so the brain knows what it can do.
        sys_prompt = cfg.brain.system_prompt
        try:
            from deskbuddy.skills import discover, catalog
            skills = discover()
            if skills:
                sys_prompt += (
                    "\n\nYou have these SKILLS (reusable procedures). "
                    "When one fits, call use_skill(name) to load its "
                    "full steps, then follow them:\n" + catalog(skills)
                )
        except Exception:  # noqa: BLE001
            pass
        self.messages: list[dict] = [{"role": "system", "content": sys_prompt}]

    def respond(self, user_text: str, max_steps: int = 8) -> str:
        # role-alternation guard: never stack two user messages
        if self.messages and self.messages[-1]["role"] == "user":
            self.messages.pop()
        self.messages.append({"role": "user", "content": user_text})

        # Only advertise tools that are actually usable right now.
        tools = [t for t in tool_schemas() if tool_available(t["function"]["name"])]

        for _ in range(max_steps):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=tools,
                tool_choice="auto",
            )
            msg = resp.choices[0].message
            # Append assistant turn using plain dict (SDK-version agnostic, and
            # keeps role alternation clean - we never synthesize user msgs).
            asst: dict = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                asst["tool_calls"] = [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name,
                                  "arguments": tc.function.arguments or "{}"}}
                    for tc in msg.tool_calls
                ]
            self.messages.append(asst)

            if not msg.tool_calls:
                return msg.content or "(no reply)"

            # Execute each requested tool, feed results back.
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                try:
                    result = call_tool(name, args)
                except Exception as e:  # noqa: BLE001
                    result = {"ok": False, "error": f"tool crashed: {e}"}
                # Role-alternation guard: append tool result, then if the next
                # thing we add is also a tool result it's fine (tool->tool is
                # valid); but never two user messages. Trim any trailing user.
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str)[:4000],
                })

        # Hit the step cap: hand back a graceful spoken answer using last context.
        try:
            final = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages
                + [{"role": "user",
                    "content": "Finish now: give the user a short spoken reply "
                              "summarizing what you did or what's blocking you."}],
                tools=[],
            )
            return final.choices[0].message.content or \
                   "I got partway but hit my step limit — want me to continue?"
        except Exception as e:  # noqa: BLE001
            return f"I hit a snag mid-task: {e}"


# --------------------------------------------------------------------------
# -------------------------------------------------------------------------
# Hermes backend: the REAL agent (perfect hybrid)
# -------------------------------------------------------------------------
class HermesBrain:
    """Ride on Hermes' full agent loop — not the stripped -z mode.

    `hermes chat -q "<text>" -Q --toolsets ... --skills ... --resume <id>`
    runs Hermes' genuine agent: it thinks, reasons, web/file-searches,
    drives the PC via computer-use, loads skills, and (with --resume)
    keeps session memory across turns. That's the "not dumb" brain.

    DeskBuddy's own voice skin + Wayland input + safety layer sit on
    top of this. We just feed it a DeskBuddy system prompt and our
    curated skills so it acts as your PC companion.
    """
    # Toolsets that make Hermes a real PC companion. computer-use = operate
    # the machine; web/file/terminal = reason + act on your stuff.
    DEFAULT_TOOLSETS = "computer_use,web,file,terminal,skills"
    # DeskBuddy skills (live under ~/.deskbuddy/skills or the repo).
    DEFAULT_SKILLS = "deskbuddy-pc,deskbuddy-projects"

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.cmd = cfg.brain.hermes_cmd
        # Stable per-machine session so memory + context persist across
        # DeskBuddy turns (Hermes' session memory = "it remembers you").
        # We don't invent the ID upfront - Hermes prints a real one on
        # the first turn; we capture it and --resume it after.
        self._session_id: str | None = None

    def _build_cmd(self, user_text: str) -> list[str]:
        cmd = [
            self.cmd, "chat",
            "-q", user_text,
            "-Q",                        # quiet: only final reply + session info
            "-t", self.DEFAULT_TOOLSETS,
            "-s", self.DEFAULT_SKILLS,
            "--max-turns", "90",
        ]
        if self._session_id:
            cmd += ["--resume", self._session_id]
        return cmd

    def respond(self, user_text: str) -> str:
        cmd = self._build_cmd(user_text)
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        except FileNotFoundError:
            return ("Hermes backend selected but the 'hermes' command isn't "
                    "installed. Run 'buddy setup' and switch to the native "
                    "backend, or install Hermes.")
        except subprocess.TimeoutExpired:
            return "Hermes took too long to answer."
        out = (p.stdout or "").strip()
        # Hermes prints "session_id: <id>" to stderr in -Q mode;
        # scan both streams for it so we can --resume later turns.
        for stream in (out, p.stderr or ""):
            for line in stream.splitlines():
                low = line.lower().replace("_", "")
                if low.startswith("sessionid") and ":" in line:
                    self._session_id = line.split(":", 1)[1].strip()
                    break
            if self._session_id:
                break
        if not out:
            err = (p.stderr or "").strip()
            if "unknown skill" in err.lower() or "no such" in err.lower():
                return ("Hermes couldn't load a DeskBuddy skill — "
                        "run `buddy setup` to (re)install skills. "
                        f"(raw: {err[:200]})")
            if "unknown toolset" in err.lower():
                return ("Hermes rejected a toolset name — "
                        f"(raw: {err[:200]})")
            return err or "Hermes returned nothing."
        # Capture the session id Hermes prints (first turn, no --resume yet)
        # so later turns can resume the same conversation/memory.
        # Hermes prints e.g. "session_id: 20260713_001104_41eaef".
        for line in out.splitlines():
            low = line.lower().replace("_", "")
            if low.startswith("sessionid") and ":" in line:
                self._session_id = line.split(":", 1)[1].strip()
                break
        # Strip the trailing session-info line; keep the spoken reply.
        lines = [ln for ln in out.splitlines()
                if not ln.lower().startswith("session:")]
        return "\n".join(lines).strip() or out


def make_brain(cfg: Config) -> Brain:
    """Pick a brain.

    Perfect hybrid: when `backend: hermes` is set AND `hermes` is on
    PATH, use `HermesBrain` — Hermes' REAL agent loop (it thinks,
    reasons, searches, drives the PC via computer-use, loads skills +
    session memory). Our voice skin + Wayland input + safety sit on top.
    We do NOT downgrade to native just because ydotool exists —
    Hermes itself operates the machine; native would throw away the agent.

    NativeBrain is used only when the user explicitly picks `native`,
    or Hermes isn't installed (standalone mode).
    """
    hermes_ok = shutil.which(cfg.brain.hermes_cmd) is not None
    if cfg.brain.backend == "hermes" and hermes_ok:
        return HermesBrain(cfg)
    if cfg.brain.backend == "hermes" and not hermes_ok:
        # Hermes requested but missing - fall back to native rather than fail.
        return NativeBrain(cfg)
    return NativeBrain(cfg)


def connection_test(cfg: Config) -> tuple[bool, str]:
    """Probe whether the configured native backend can reach the model.

    Returns (ok, message). Used by the setup wizard to validate before saving.
    """
    try:
        from openai import OpenAI
        key = cfg.api_key() or "not-needed"
        client = OpenAI(base_url=cfg.brain.base_url, api_key=key)
        resp = client.chat.completions.create(
            model=cfg.brain.model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=4,
        )
        txt = (resp.choices[0].message.content or "").strip()
        return True, f"connected — model replied: {txt[:60]!r}"
    except Exception as e:  # noqa: BLE001
        return False, f"could not reach model: {e}"
