"""BRAIN - the agent. Pluggable backends behind one interface.

Backend protocol:
    class Brain:
        def respond(self, user_text: str) -> str: ...   # returns spoken reply

Two implementations:
    NativeBrain  - our own OpenAI-compatible tool-calling loop (option 1).
    HermesBrain  - shells out to the `hermes` CLI as the engine (option 2).

The wizard picks one via config.brain.backend.
"""
from __future__ import annotations

import json
import subprocess
from typing import Protocol

from deskbuddy.config import Config
from deskbuddy.hands import tool_schemas, call_tool


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
        self.client = OpenAI(base_url=cfg.brain.base_url, api_key=key)
        self.model = cfg.brain.model
        # inject DeskBuddy's own skill catalog so the brain knows what it can do
        sys_prompt = cfg.brain.system_prompt
        try:
            from deskbuddy.skills import discover, catalog
            skills = discover()
            if skills:
                sys_prompt += ("\n\nYou have these SKILLS (reusable procedures). "
                               "When one fits, call use_skill(name) to load its "
                               "full steps, then follow them:\n" + catalog(skills))
        except Exception:  # noqa: BLE001
            pass
        self.messages: list[dict] = [{"role": "system", "content": sys_prompt}]

    def respond(self, user_text: str, max_steps: int = 6) -> str:
        self.messages.append({"role": "user", "content": user_text})
        tools = tool_schemas()

        for _ in range(max_steps):
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=tools,
                tool_choice="auto",
            )
            msg = resp.choices[0].message
            self.messages.append(msg.model_dump(exclude_none=True))

            if not msg.tool_calls:
                return msg.content or "(no reply)"

            # execute each requested tool, feed results back
            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = call_tool(name, args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)[:4000],
                })
        return "I hit my step limit working on that - want me to keep going?"


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
    if cfg.brain.backend == "hermes":
        return HermesBrain(cfg)
    return NativeBrain(cfg)
