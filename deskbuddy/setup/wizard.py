"""Terminal setup wizard - Hermes-style, runs in the terminal.

Invoked by `buddy setup` (and automatically on first run if no config exists).
Writes ~/.deskbuddy/config.yaml and ~/.deskbuddy/.env.
"""
from __future__ import annotations

import shutil

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from deskbuddy.config import Config, set_env_var

console = Console()


def _banner() -> None:
    console.print(Panel.fit(
        "[bold cyan]DeskBuddy Setup[/]\n"
        "[dim]Alexa for your PC - voice-powered desktop companion.[/]",
        border_style="cyan"))


def _detect_helpers() -> list[str]:
    tips: list[str] = []
    import os
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland":
        if not shutil.which("ydotool"):
            tips.append("ydotool  (Wayland keyboard/mouse control)")
        if not shutil.which("wtype"):
            tips.append("wtype    (Wayland text typing)")
        if not shutil.which("grim"):
            tips.append("grim     (Wayland screenshots)")
    else:
        if not shutil.which("xdotool"):
            tips.append("xdotool  (X11 keyboard/mouse control)")
        if not shutil.which("wmctrl"):
            tips.append("wmctrl   (X11 window listing)")
    if not (shutil.which("piper") or shutil.which("espeak-ng")
            or shutil.which("edge-tts")):
        tips.append("piper or espeak-ng  (text-to-speech voice)")
    return tips


def run_wizard() -> Config:
    _banner()
    cfg = Config.load()

    # --- The big choice: stand alone, or link to Hermes? -------------------
    console.print("\n[bold]How should DeskBuddy think?[/]")
    console.print("   [cyan]standalone[/] = DeskBuddy's own brain, linked directly")
    console.print("                to a model provider (Ollama, Nous, OpenAI...).")
    console.print("                Fully independent - no Hermes needed.")
    console.print("   [cyan]hermes[/]     = ride on your installed Hermes as the engine.")
    console.print("                Great if you already use and love Hermes.")
    import shutil as _sh
    hermes_here = _sh.which(cfg.brain.hermes_cmd) is not None
    if hermes_here:
        console.print(f"   [dim](detected 'hermes' on your PATH)[/]")
    else:
        console.print(f"   [dim](no 'hermes' found on PATH - standalone recommended)[/]")
    mode = Prompt.ask("   choose", choices=["standalone", "hermes"],
                      default="hermes" if hermes_here else "standalone")

    if mode == "hermes":
        cfg.brain.backend = "hermes"
        cfg.brain.hermes_cmd = Prompt.ask("   hermes command", default=cfg.brain.hermes_cmd)
        if not _sh.which(cfg.brain.hermes_cmd):
            console.print("   [yellow]Warning: that command isn't on PATH yet. "
                          "Install Hermes or switch to standalone later.[/]")
    else:
        _configure_standalone(cfg)

    # --- Voice -------------------------------------------------------------
    console.print("\n[bold]Voice[/]")
    cfg.voice.wake_word = Prompt.ask("   wake word", default=cfg.voice.wake_word)
    cfg.voice.stt = Prompt.ask("   speech-to-text", choices=["whisper", "none"],
                               default=cfg.voice.stt)
    cfg.voice.tts = Prompt.ask("   text-to-speech", choices=["auto", "none"],
                               default=cfg.voice.tts)

    # --- Hands -------------------------------------------------------------
    console.print("\n[bold]Hands[/] - PC control")
    cfg.hands.allow_shell = Confirm.ask("   allow running shell commands?",
                                        default=cfg.hands.allow_shell)
    cfg.hands.confirm_destructive = Confirm.ask(
        "   confirm before destructive actions?", default=cfg.hands.confirm_destructive)

    cfg.save()

    if cfg.voice.wake_word:
        console.print(f"\n[dim]Tip: run 'buddy enroll' to teach DeskBuddy to hear "
                      f"'{cfg.voice.wake_word}'.[/]")

    _report_helpers()
    console.print(Panel.fit(
        "[green]Setup complete![/]\n"
        "Run [bold]buddy[/] to start, or [bold]buddy --text[/] to type.",
        border_style="green"))
    return cfg


def _configure_standalone(cfg: Config) -> None:
    """Pick a model provider preset and link it - easy model linking."""
    from deskbuddy.brain import PROVIDERS, apply_provider, list_presets
    from deskbuddy.config import set_env_var

    console.print("\n[bold]Link a model[/] (standalone brain)")
    presets = list_presets()
    for i, p in enumerate(presets, 1):
        key = "  (no key)" if not p.needs_key else "  (needs API key)"
        console.print(f"   [cyan]{i}[/]. {p.label}{key}")
        if p.note:
            console.print(f"      [dim]{p.note}[/]")
    choice = Prompt.ask("   provider #",
                        choices=[str(i) for i in range(1, len(presets) + 1)],
                        default="1")
    preset = presets[int(choice) - 1]

    base_url = None
    if preset.key == "custom":
        base_url = Prompt.ask("   base URL (OpenAI-compatible)")
    model = Prompt.ask("   model", default=preset.default_model or "")
    apply_provider(cfg, preset.key, model=model, base_url=base_url)

    if preset.needs_key:
        key = Prompt.ask("   API key", password=True, default="")
        if key:
            set_env_var(cfg.brain.api_key_env, key)
    console.print(f"   [green]Linked:[/] {cfg.brain.provider} · {cfg.brain.model}")


def _report_helpers() -> None:
    tips = _detect_helpers()
    if tips:
        console.print(Panel(
            "For full hands-off control, install these system helpers:\n\n"
            + "\n".join(f"  - {t}" for t in tips)
            + "\n\n[dim]e.g. sudo apt install ydotool wtype grim espeak-ng[/]",
            title="[yellow]Optional helpers[/]", border_style="yellow"))
