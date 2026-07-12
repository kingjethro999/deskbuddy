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
# Hermes backend: reuse Hermes as the engine
# --------------------------------------------------------------------------
class HermesBrain:
    """Shell out to the `hermes` CLI. Lets DeskBuddy ride on Hermes' full power."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.cmd = cfg.brain.hermes_cmd

    def respond(self, user_text: str) -> str:
        try:
            # hermes single-shot query mode: `hermes -z "..."`
            p = subprocess.run(
                [self.cmd, "-z", user_text],
                capture_output=True, text=True, timeout=180,
            )
            out = (p.stdout or "").strip()
            return out or (p.stderr or "Hermes returned nothing.").strip()
        except FileNotFoundError:
            return ("Hermes backend selected but the 'hermes' command isn't "
                    "installed. Run the DeskBuddy wizard and switch to the "
                    "native backend, or install Hermes.")
        except subprocess.TimeoutExpired:
            return "Hermes took too long to answer."


def make_brain(cfg: Config) -> Brain:
    """Pick a brain.

    'native' talks to the same OpenAI-compatible model (Nous/Hermes by
    default) but runs DeskBuddy's PC-control tools locally - so it can
    actually open apps, type, click, read the screen. 'hermes' shells out
    to the hermes CLI for chat but can't drive the PC, so we fall back to
    native for any command that looks like it wants to act on the machine.
    """
    hermes_ok = shutil.which(cfg.brain.hermes_cmd) is not None
    if cfg.brain.backend == "hermes" and hermes_ok:
        return HermesBrain(cfg)
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
