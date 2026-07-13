"""DeskBuddy CLI - the `buddy` command.

    buddy            launch the GUI (auto-runs setup on first run)
    buddy --text     headless text loop in the terminal (no GUI, no mic)
    buddy --voice    headless voice loop in the terminal
    buddy setup      run the setup wizard
    buddy doctor     check the environment
"""
from __future__ import annotations

import argparse
import shutil
import sys

from deskbuddy.config import Config, CONFIG_PATH


def _doctor() -> int:
    import os
    print("DeskBuddy doctor\n----------------")
    print(f"config: {CONFIG_PATH} {'(exists)' if CONFIG_PATH.exists() else '(missing - run: buddy setup)'}")
    session = os.environ.get("XDG_SESSION_TYPE", "unknown")
    print(f"session: {session}")
    checks = {
        "python-openai": _mod("openai"),
        "sounddevice (mic)": _mod("sounddevice"),
        "faster-whisper (STT)": _mod("faster_whisper"),
        "arecord": bool(shutil.which("arecord")),
        "aplay": bool(shutil.which("aplay")),
        "tts: piper/espeak-ng/edge-tts": any(shutil.which(c) for c in
            ("piper", "espeak-ng", "edge-tts")),
        "input: ydotool/wtype/xdotool": any(shutil.which(c) for c in
            ("ydotool", "wtype", "xdotool")),
        "screenshot: grim/scrot/gnome-screenshot": any(shutil.which(c) for c in
            ("grim", "scrot", "gnome-screenshot")),
    }
    for name, ok in checks.items():
        print(f"  [{'x' if ok else ' '}] {name}")
    # wake word status
    try:
        from deskbuddy.config import Config
        from deskbuddy.voice.wakeword import WakeWordEngine
        w = Config.load().voice.wake_word
        trained = WakeWordEngine(w).trained
        print(f"  [{'x' if trained else ' '}] wake word '{w}' enrolled"
              + ("" if trained else "  (run: buddy enroll)"))
    except Exception:  # noqa: BLE001
        pass
    return 0


def _mod(name: str) -> bool:
    import importlib.util
    return importlib.util.find_spec(name) is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="buddy", description="DeskBuddy - Alexa for your PC")
    parser.add_argument("command", nargs="?", default="gui",
                        choices=["gui", "setup", "doctor", "enroll", "listen",
                                 "daemon", "voice"])
    parser.add_argument("voice_id", nargs="?", default=None,
                        help="with 'voice': set preferred voice id")
    parser.add_argument("--text", action="store_true", help="headless text loop")
    parser.add_argument("--voice", action="store_true", help="headless voice loop")
    args = parser.parse_args(argv)

    if args.command == "doctor":
        return _doctor()

    from deskbuddy.config import Config as _Cfg
    from deskbuddy.voice import tts as _tts

    if args.command == "voice":
        cfg = _Cfg.load()
        if args.voice_id:
            if args.voice_id not in _tts.list_voices():
                print(f"Unknown voice '{args.voice_id}'. Available:")
                for v in _tts.list_voices():
                    print(f"  - {v}")
                return 1
            cfg.voice.tts_voice = args.voice_id
            cfg.save()
            print(f"Preferred voice set to '{args.voice_id}'. It takes effect on next launch.")
        else:
            print(f"Current preferred voice: {cfg.voice.tts_voice}")
            print("Available:")
            for v in _tts.list_voices():
                print(f"  - {v}")
            print("\nSet with:  buddy voice <id>")
        return 0

    if args.command == "enroll":
        cfg = _Cfg.load()
        from deskbuddy.voice.wakeword import enroll_interactive
        enroll_interactive(cfg.voice.wake_word)
        return 0

    if args.command == "listen":
        cfg = _Cfg.load()
        from deskbuddy.voice.wakeword import WakeWordEngine, listen_for_wake
        eng = WakeWordEngine(cfg.voice.wake_word)
        if not eng.trained:
            print(f"Wake word '{cfg.voice.wake_word}' not enrolled. "
                  f"Run: buddy enroll")
            return 1
        print(f"Listening for '{cfg.voice.wake_word}'... (Ctrl+C to stop)")
        try:
            listen_for_wake(eng, on_detect=lambda: print("  ● wake word detected!"))
        except KeyboardInterrupt:
            pass
        return 0

    if args.command == "daemon":
        # Always-on wake word: persistently listen in the background and launch
        # the GUI on detection. Uses DeskBuddy's OWN MFCC+DTW engine (offline,
        # free, no paid SDK) - not openWakeWord, which has no Linux build.
        import os
        from pathlib import Path
        cfg = _Cfg.load()
        pid = os.getpid()
        pidfile = Path.home() / ".deskbuddy" / "buddy-daemon.pid"
        try:
            from deskbuddy.voice.wakeword import WakeWordEngine, listen_for_wake
        except Exception as e:  # noqa: BLE001
            print(f"[daemon] wake-word engine unavailable: {e}")
            return 1
        eng = WakeWordEngine(cfg.voice.wake_word)
        if not eng.trained:
            print(f"Wake word '{cfg.voice.wake_word}' not enrolled. Run: buddy enroll")
            return 1
        pidfile.parent.mkdir(parents=True, exist_ok=True)
        pidfile.write_text(str(pid))
        print(f"[daemon] always-on wake word active (pid {pid}). "
              f"Say '{cfg.voice.wake_word}'. Stop with: buddy daemon --stop")
        try:
            listen_for_wake(
                eng,
                on_detect=lambda: os.system(
                    f"{shutil.which('buddy') or 'buddy'} gui >/dev/null 2>&1 &") or
                print("  ● wake word detected -> launching GUI"),
            )
        except KeyboardInterrupt:
            pass
        finally:
            try:
                pidfile.unlink()
            except Exception:  # noqa: BLE001
                pass
        return 0

    from deskbuddy.setup import run_wizard

    if args.command == "setup" or (not CONFIG_PATH.exists() and sys.stdin.isatty()):
        cfg = run_wizard()
        if args.command == "setup":
            return 0
    elif not CONFIG_PATH.exists():
        # headless mode with no config: don't auto-launch the wizard
        # (it needs an interactive terminal). Use defaults, but if Hermes
        # is installed, prefer riding on it (proven to work here).
        cfg = _Cfg.load()  # defaults
        if shutil.which("hermes"):
            cfg.brain.backend = "hermes"
            print("No config found; Hermes detected - using it as the engine.\n"
                  "Run 'buddy setup' to configure DeskBuddy's own brain.")
        else:
            print("No config found. Run 'buddy setup' to configure, "
                  "or I'll use standalone defaults for this session.")
    else:
        cfg = _Cfg.load()

    # headless modes
    if args.text or args.voice:
        from deskbuddy.runtime import Session
        sess = Session(cfg, on_event=lambda k, t: _print_event(k, t))
        if args.text:
            cfg.voice.stt = "none"  # keyboard input
            sess.stt = _keyboard_stt()
            sess.loop(text_mode=True)
        else:
            sess.wake_loop()  # fully voice-first: wake word -> command
        return 0

    # default: GUI
    from deskbuddy.face import launch
    launch(cfg)
    return 0


def _print_event(kind: str, text: str) -> None:
    if kind == "status":
        return
    who = "you" if kind == "you" else "buddy"
    print(f"{who}> {text}")


def _keyboard_stt():
    from deskbuddy.voice.stt import KeyboardSTT
    return KeyboardSTT()


if __name__ == "__main__":
    sys.exit(main())
