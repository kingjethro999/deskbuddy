"""EARS - speech to text.

Primary: faster-whisper (offline). Records from the mic with sounddevice,
transcribes locally. Falls back to a keyboard prompt if unavailable, so the
loop always works.
"""
from __future__ import annotations

import queue
import sys

SAMPLE_RATE = 16000


def _record_until_silence(max_seconds: float = 10.0, silence_secs: float = 1.8):
    """Voice-triggered capture: wait for speech, record until a silence gap.

    Returns float32 numpy audio or None on mic failure. This makes the GUI
    feel responsive - it only transcribes once you actually speak.
    """
    try:
        import numpy as np
        import sounddevice as sd
    except Exception:  # noqa: BLE001
        return None
    try:
        chunk = int(0.03 * SAMPLE_RATE)  # 30ms blocks
        buf = []
        triggered = False
        silent_for = 0.0
        spoke_for = 0.0
        # RMS threshold (~ambient). Tuned for typical mic levels.
        threshold = 0.012
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            blocksize=chunk) as stream:
            import time
            start = time.time()
            while time.time() - start < max_seconds:
                data, _ = stream.read(chunk)
                rms = float(np.sqrt(np.mean(data ** 2)))
                buf.append(data.copy())
                if rms > threshold:
                    triggered = True
                    silent_for = 0.0
                    spoke_for += len(data) / SAMPLE_RATE
                elif triggered:
                    silent_for += len(data) / SAMPLE_RATE
                    if silent_for >= silence_secs or spoke_for > max_seconds:
                        break
        if not triggered or not buf:
            return None
        return np.concatenate(buf).flatten()
    except Exception as e:  # noqa: BLE001
        print(f"[mic error] {e}", file=sys.stderr)
        return None


class WhisperSTT:
    def __init__(self, model_name: str = "base.en"):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def listen(self, seconds: float = 5.0) -> str:
        audio = _record_until_silence()
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
