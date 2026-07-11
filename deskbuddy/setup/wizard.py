"""Terminal setup wizard - Hermes-style, runs in the terminal.

Invoked by `buddy setup` (and automatically on first run if no config exists).
Writes ~/.deskbuddy/config.yaml and ~/.deskbuddy/.env.

Flow:
  1. Brain mode: standalone (own brain + your model key) vs link-to-Hermes.
  2. If standalone: pick a provider preset, enter model/key, then a LIVE
     connection test so you never save a broken config.
  3. Voice: wake word, STT, TTS.
  4. Hands: permissions.
  5. Summary panel + optional-helper tips.
"""
from __future__ import annotations

import shutil
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from deskbuddy.config import Config, set_env_var, CONFIG_PATH

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
    # The wizard needs an interactive terminal. Refuse cleanly if stdin is piped.
    if not sys.stdin.isatty():
        raise SystemExit(
            "DeskBuddy setup needs an interactive terminal.\n"
            "Run it directly (not piped): buddy setup")
    _banner()
    cfg = Config.load()

    # --- Step 1: brain mode ----------------------------------------------
    console.print("\n[bold]1. How should DeskBuddy think?[/]")
    console.print("   [cyan]standalone[/] = DeskBuddy's own brain, linked directly")
    console.print("                to a model provider (Ollama, Nous, OpenAI...).")
    console.print("                Fully independent - you bring your own key.")
    console.print("   [cyan]hermes[/]     = ride on your installed Hermes as the engine.")
    console.print("                Best if you already use and love Hermes.")
    hermes_here = shutil.which(cfg.brain.hermes_cmd) is not None
    console.print(f"   [dim](hermes on PATH: {'yes' if hermes_here else 'no'})[/]")
    mode = Prompt.ask("   choose",
                      choices=["standalone", "hermes"],
                      default="hermes" if hermes_here else "standalone")

    if mode == "hermes":
        cfg.brain.backend = "hermes"
        cfg.brain.hermes_cmd = Prompt.ask("   hermes command",
                                          default=cfg.brain.hermes_cmd)
        if not shutil.which(cfg.brain.hermes_cmd):
            console.print("   [yellow]Warning: that command isn't on PATH yet. "
                          "Install Hermes or switch to standalone later.[/]")
    else:
        _configure_standalone(cfg)

    # --- Step 2: voice --------------------------------------------------
    console.print("\n[bold]2. Voice[/]")
    cfg.voice.wake_word = Prompt.ask("   wake word", default=cfg.voice.wake_word)
    cfg.voice.stt = Prompt.ask("   speech-to-text",
                               choices=["whisper", "none"], default=cfg.voice.stt)
    cfg.voice.tts = Prompt.ask("   text-to-speech",
                               choices=["auto", "none"], default=cfg.voice.tts)

    # --- Step 3: hands --------------------------------------------------
    console.print("\n[bold]3. Hands - PC control[/]")
    cfg.hands.allow_shell = Confirm.ask("   allow running shell commands?",
                                        default=cfg.hands.allow_shell)
    cfg.hands.confirm_destructive = Confirm.ask(
        "   confirm before destructive actions?",
        default=cfg.hands.confirm_destructive)

    cfg.save()

    if cfg.voice.wake_word:
        console.print(f"\n[dim]Tip: run 'buddy enroll' to teach DeskBuddy "
                      f"to hear '{cfg.voice.wake_word}'.[/]")

    _report_helpers()
    _summary(cfg)
    console.print(Panel.fit(
        "[green]Setup complete![/]\n"
        "Run [bold]buddy[/] to launch the GUI, or [bold]buddy --text[/] to type.",
        border_style="green"))
    return cfg


def _configure_standalone(cfg: Config) -> None:
    """Pick a model provider preset, link it, then LIVE-TEST the connection."""
    from deskbuddy.brain import PROVIDERS, apply_provider, list_presets
    from deskbuddy.brain.agent import connection_test

    console.print("\n[bold]Link a model[/] (standalone brain)")
    presets = list_presets()
    for i, p in enumerate(presets, 1):
        tag = "  (no key)" if not p.needs_key else "  (needs API key)"
        console.print(f"   [cyan]{i}[/]. {p.label}{tag}")
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

    # LIVE connection test - never save a config that can't reach the model.
    console.print("   [dim]testing connection...[/]")
    ok, msg = connection_test(cfg)
    if ok:
        console.print(f"   [green]Linked & verified:[/] {cfg.brain.provider} "
                      f"· {cfg.brain.model}\n   [dim]{msg}[/]")
    else:
        console.print(f"   [yellow]Linked, but the model didn't respond:[/]\n"
                      f"   {msg}\n"
                      f"   [dim]You can still save this and fix the key/model "
                      f"later, or re-run 'buddy setup'.[/]")
        if Confirm.ask("   keep this config anyway?", default=True):
            pass
        else:
            cfg.brain.model = ""  # force re-setup next run


def _report_helpers() -> None:
    tips = _detect_helpers()
    if tips:
        console.print(Panel(
            "For full hands-off control, install these system helpers:\n\n"
            + "\n".join(f"  - {t}" for t in tips)
            + "\n\n[dim]e.g. sudo apt install ydotool wtype grim espeak-ng[/]",
            title="[yellow]Optional helpers[/]", border_style="yellow"))


def _summary(cfg: Config) -> None:
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="bold cyan")
    t.add_column()
    t.add_row("Brain", cfg.brain.backend)
    if cfg.brain.backend == "hermes":
        t.add_row("Hermes cmd", cfg.brain.hermes_cmd)
    else:
        t.add_row("Provider", f"{cfg.brain.provider} · {cfg.brain.model}")
        t.add_row("Base URL", cfg.brain.base_url or "(default)")
    t.add_row("Wake word", cfg.voice.wake_word or "(disabled)")
    t.add_row("STT / TTS", f"{cfg.voice.stt} / {cfg.voice.tts}")
    t.add_row("Shell", "allowed" if cfg.hands.allow_shell else "blocked")
    t.add_row("Config", str(CONFIG_PATH))
    console.print(Panel(t, title="[green]Summary[/]", border_style="green"))
