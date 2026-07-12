"""Configuration loading/saving for DeskBuddy.

Config lives at ~/.deskbuddy/config.yaml, secrets at ~/.deskbuddy/.env.
Mirrors the Hermes approach: a single YAML the wizard writes and the user can edit.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import yaml

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("DESKBUDDY_HOME", HOME / ".deskbuddy"))
CONFIG_PATH = CONFIG_DIR / "config.yaml"
ENV_PATH = CONFIG_DIR / ".env"


@dataclass
class BrainConfig:
    # backend: "native" (our own loop) or "hermes" (shell out to hermes)
    backend: str = "native"
    provider: str = "nous"                       # openai-compatible provider label
    base_url: str = "https://inference-api.nousresearch.com/v1"
    model: str = "hermes-4-70b"
    api_key_env: str = "DESKBUDDY_API_KEY"       # name of env var holding the key
    system_prompt: str = (
        "You are DeskBuddy, a friendly voice-powered desktop companion living on "
        "the user's PC. You can operate the computer on their behalf using tools: "
        "open apps, run commands, control the keyboard and mouse, manage files, and "
        "read the screen. Keep spoken replies short and natural - you are being read "
        "aloud. Confirm before doing anything destructive."
    )
    # for backend == "hermes"
    hermes_cmd: str = "hermes"


@dataclass
class VoiceConfig:
    wake_word: str = "buddy"
    stt: str = "whisper"        # whisper | vosk | none (text mode)
    tts: str = "auto"           # auto | kokoro | edge | piper | espeak | none
    tts_voice: str = "af_heart" # valid Kokoro id; used as-is for kokoro,
                                # or a Microsoft voice (en-US-AndrewNeural) for edge
    mic_device: str | None = None
    speaker_device: str | None = None
    whisper_model: str = "small.en"  # better accuracy than base.en (less garble)
    wake_required: bool = True       # require wake word before listening for commands


@dataclass
class HandsConfig:
    # input backend: auto-detected. wayland -> ydotool/wtype, x11 -> xdotool
    input_backend: str = "auto"
    allow_shell: bool = True
    confirm_destructive: bool = True


@dataclass
class Config:
    brain: BrainConfig = field(default_factory=BrainConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    hands: HandsConfig = field(default_factory=HandsConfig)

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            return cls()
        raw = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        return cls(
            brain=BrainConfig(**(raw.get("brain") or {})),
            voice=VoiceConfig(**(raw.get("voice") or {})),
            hands=HandsConfig(**(raw.get("hands") or {})),
        )

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(yaml.safe_dump(asdict(self), sort_keys=False))

    def api_key(self) -> str | None:
        """Resolve the API key from the environment or the .env file."""
        load_env()
        return os.environ.get(self.brain.api_key_env)


def load_env() -> None:
    """Minimal .env loader (no external dependency)."""
    if not ENV_PATH.exists():
        return
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def set_env_var(key: str, value: str) -> None:
    """Persist a secret to ~/.deskbuddy/.env."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    found = False
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.strip().startswith(f"{key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n")
    os.chmod(ENV_PATH, 0o600)
