"""The DeskBuddy runtime loop: wake -> listen -> think -> act -> speak.

Exposed as run_conversation() so both the headless CLI and the GUI can drive
it. An optional on_event callback lets the GUI show live status.
"""
from __future__ import annotations

import time
from typing import Callable

from deskbuddy.config import Config
from deskbuddy.brain import make_brain
from deskbuddy.voice import speak, make_stt

Event = Callable[[str, str], None]  # (kind, text)


def _is_tty_stdin() -> bool:
    import sys
    return sys.stdin.isatty()


def _noop(kind: str, text: str) -> None:
    pass


class Session:
    def __init__(self, cfg: Config, on_event: Event = _noop):
        self.cfg = cfg
        self.on_event = on_event
        self.brain = make_brain(cfg)
        self.stt = make_stt(cfg)
        self.speaking = cfg.voice.tts != "none"
        # Echo guard: mic is muted for a moment after we speak so DeskBuddy
        # doesn't hear (and reply to) its own voice.
        self._mute_until = 0.0
        from deskbuddy.voice import tts as _tts
        _tts.set_preferred(cfg.voice.tts_voice)

    def _say(self, text: str) -> None:
        self.on_event("buddy", text)
        if self.speaking:
            speak(text, self.cfg.voice.tts_voice)
        # mute the mic briefly so we don't echo-catch our own speech
        self._mute_until = time.time() + 1.3

    def _mic_muted(self) -> bool:
        return time.time() < self._mute_until

    def _listen(self) -> str:
        if self._mic_muted():
            return ""
        return self.stt.listen(wake_word=self.cfg.voice.wake_word)

    def handle(self, user_text: str) -> str:
        """One turn: given user text, think/act and speak the reply."""
        self.on_event("you", user_text)
        # Interim feedback so the (slow) inference doesn't feel dead.
        self.on_event("status", "thinking")
        self._say("On it...")
        reply = self.brain.respond(user_text)
        self._say(reply)
        return reply

    def ask(self, question: str, options: list[str] | None = None) -> str:
        """Ask the USER a decisive question; returns their answer.

        The GUI uses the prompt event to show a conditional input box
        only for this moment (not a permanent text area). In text/voice
        mode it falls back to the STT/keyboard.
        """
        self.on_event("prompt", question)
        try:
            ans = self._listen()
        except (KeyboardInterrupt, EOFError):
            ans = ""
        self.on_event("you", ans)
        return ans

    def loop(self, text_mode: bool = False) -> None:
        """Continuous loop. In text mode, reads typed input; else listens."""
        if text_mode and not _is_tty_stdin():
            line = self.stt.listen()
            if line:
                self.on_event("status", "thinking")
                self.handle(line)
            return
        self._say(
            "Hi, I'm DeskBuddy. Say '%s' or just talk." % self.cfg.voice.wake_word
        )
        wake = self.cfg.voice.wake_word.lower()
        while True:
            try:
                self.on_event("status", "listening")
                user_text = self._listen()
            except (KeyboardInterrupt, EOFError):
                break
            if not user_text:
                continue
            # Wake gating: when required, only act on utterances that start
            # with the wake word (cheap, uses Whisper itself - no enroll needed).
            if self.cfg.voice.wake_required:
                low = user_text.lower()
                if low.startswith("__wakeonly__"):
                    self._say("Yes?")
                    continue
                if not low.startswith(wake):
                    # not addressed to us - stay quiet, don't burn a brain turn
                    continue
                user_text = user_text[len(wake):].strip(" ,.!?")
                if not user_text:
                    self._say("Yes?")
                    continue
            else:
                low = user_text.lower()
            if low in {"quit", "exit", "goodbye", "bye"}:
                self._say("Goodbye!")
                break
            self.on_event("status", "thinking")
            self.handle(user_text)

    def wake_loop(self) -> None:
        """Voice-first mode: wait for the wake word, then take one command.

        Flow: detect wake, listen, think, act, speak, wait again.
        Uses DeskBuddy's own wake-word engine, so no third-party service.
        """
        from deskbuddy.voice.wakeword import WakeWordEngine, record
        eng = WakeWordEngine(self.cfg.voice.wake_word)
        if not eng.trained:
            self._say(
                "I don't know my wake word yet. Run 'buddy enroll' to teach "
                "me to hear '%s'." % self.cfg.voice.wake_word
            )
            return
        self._say("Listening for '%s'." % self.cfg.voice.wake_word)
        while True:
            try:
                self.on_event("status", "waiting")
                audio = record(1.3)
                if audio is None or not eng.detect(audio):
                    continue
                self.on_event("status", "listening")
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
