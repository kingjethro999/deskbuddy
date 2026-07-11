"""EARS - speech to text.

Primary: faster-whisper (offline). Records from the mic with sounddevice,
transcribes locally. Falls back to a keyboard prompt if unavailable, so the
loop always works.
"""
from __future__ import annotations

import queue
import sys

SAMPLE_RATE = 16000


def _record_until_silence(seconds: float = 5.0):
    """Record a fixed window from the mic. Returns float32 numpy audio or None."""
    try:
        import numpy as np
        import sounddevice as sd
    except Exception:  # noqa: BLE001
        return None
    try:
        frames = int(seconds * SAMPLE_RATE)
        audio = sd.rec(frames, samplerate=SAMPLE_RATE, channels=1, dtype="float32")
        sd.wait()
        return audio.flatten()
    except Exception as e:  # noqa: BLE001
        print(f"[mic error] {e}", file=sys.stderr)
        return None


class WhisperSTT:
    def __init__(self, model_name: str = "base.en"):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def listen(self, seconds: float = 5.0) -> str:
        audio = _record_until_silence(seconds)
        if audio is None:
            return ""
        segments, _ = self.model.transcribe(audio, language="en")
        return " ".join(s.text for s in segments).strip()


class KeyboardSTT:
    """Fallback 'ears': read a typed line. Keeps the loop testable with no mic."""
    def listen(self, seconds: float = 0.0) -> str:
        try:
            return input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            return ""


def make_stt(cfg):
    if cfg.voice.stt == "whisper":
        try:
            return WhisperSTT(cfg.voice.whisper_model)
        except Exception as e:  # noqa: BLE001
            print(f"[stt] whisper unavailable ({e}); falling back to keyboard.")
    return KeyboardSTT()
