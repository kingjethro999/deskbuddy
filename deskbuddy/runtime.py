"""The DeskBuddy runtime loop: wake -> listen -> think -> act -> speak.

Exposed as run_conversation() so both the headless CLI and the GUI can drive it.
An optional `on_event` callback lets the GUI show live status.
"""
from __future__ import annotations

from typing import Callable

from deskbuddy.config import Config
from deskbuddy.brain import make_brain
from deskbuddy.voice import speak, make_stt


def _is_tty_stdin() -> bool:
    import sys
    return sys.stdin.isatty()

Event = Callable[[str, str], None]  # (kind, text)


def _noop(kind: str, text: str) -> None:
    pass


class Session:
    def __init__(self, cfg: Config, on_event: Event = _noop):
        self.cfg = cfg
        self.on_event = on_event
        self.brain = make_brain(cfg)
        self.stt = make_stt(cfg)
        self.speaking = cfg.voice.tts != "none"

    def _say(self, text: str) -> None:
        self.on_event("buddy", text)
        if self.speaking:
            speak(text, self.cfg.voice.tts_voice)

    def handle(self, user_text: str) -> str:
        """One turn: given user text, think/act and speak the reply."""
        self.on_event("you", user_text)
        reply = self.brain.respond(user_text)
        self._say(reply)
        return reply

    def loop(self, text_mode: bool = False) -> None:
        """Continuous loop. In text mode, reads typed input; else listens."""
        # Pipeed/non-TTY stdin has no persistent prompt - read one line, then exit.
        if text_mode and not _is_tty_stdin():
            line = self.stt.listen()
            if line:
                self.on_event("status", "thinking")
                self.handle(line)
            return
        self._say(f"Hi, I'm DeskBuddy. Say '{self.cfg.voice.wake_word}' or just talk.")
        while True:
            try:
                self.on_event("status", "listening")
                user_text = self.stt.listen()
            except (KeyboardInterrupt, EOFError):
                break
            if not user_text:
                continue
            low = user_text.lower()
            if low in {"quit", "exit", "goodbye", "bye"}:
                self._say("Goodbye!")
                break
            self.on_event("status", "thinking")
            self.handle(user_text)

    def wake_loop(self) -> None:
        """Fully voice-first: wait for the wake word, then take one command.

        wake ('buddy') -> listen -> think -> act -> speak -> back to waiting.
        Uses DeskBuddy's own wake-word engine (no Porcupine).
        """
        from deskbuddy.voice.wakeword import WakeWordEngine, record
        eng = WakeWordEngine(self.cfg.voice.wake_word)
        if not eng.trained:
            self._say(f"I don't know my wake word yet. Run 'buddy enroll' to teach "
                      f"me to hear '{self.cfg.voice.wake_word}'.")
            return
        self._say(f"Listening for '{self.cfg.voice.wake_word}'.")
        while True:
            try:
                self.on_event("status", f"waiting for '{self.cfg.voice.wake_word}'")
                audio = record(1.3)
                if audio is None or not eng.detect(audio):
                    continue
                self.on_event("status", "awake - listening")
                self._say("Yes?")
                command = self.stt.listen()
                if not command:
                    continue
                if command.lower() in {"quit", "exit", "goodbye", "bye", "stop"}:
                    self._say("Goodbye!")
                    break
                self.on_event("status", "thinking")
                self.handle(command)
            except KeyboardInterrupt:
                break
