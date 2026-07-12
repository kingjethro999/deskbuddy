"""EARS - speech to text.

Primary: faster-whisper (offline). Records from the mic with sounddevice,
transcribes locally. Falls back to a keyboard prompt if unavailable, so the
loop always works.

Accent-aware: we pass an `initial_prompt` that tells the model the
speaker uses Nigerian English and the wake word, which materially improves
transcription for non-US/UK accents (Whisper is trained predominantly on
Western English and is otherwise biased against them).
"""
from __future__ import annotations

import queue
import sys
import time

SAMPLE_RATE = 16000

# Hint the model about the speaker's English variety + wake word. This is the
# single biggest lever for non-Western accents - without it Whisper guesses
# "Blue" for "bro", "F" for "earth", etc.
_INITIAL_PROMPT = (
    "The speaker uses Nigerian English (West African accent). "
    "Common words: 'bro' (friend), 'abeg' (please), 'wahala' (trouble), "
    "'wetin' (what). The wake word is 'jarvis'. Transcribe exactly what is "
    "said, phonetically, in plain English."
)


def _record_until_silence(max_seconds: float = 25.0, silence_secs: float = 1.8):
    """Voice-triggered capture: wait for speech, record until a silence gap.

    Returns float32 numpy audio or None on mic failure.
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
        threshold = 0.012
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                            blocksize=chunk) as stream:
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
    def __init__(self, model_name: str = "small.en"):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(model_name, device="cpu", compute_type="int8")

    def _clean(self, text: str) -> str:
        t = (text or "").strip().strip(".,!?\"' ").lower()
        junk = {"", "you", "yeah", "yes", "no", "ok", "okay", "uh", "um",
                "thank you", "thanks", "hello", "hi", "hey", "jarvis"}
        if t in junk:
            return ""
        if len(t) < 2:
            return ""
        return text.strip()

    def listen(self, seconds: float = 5.0,
               wake_word: str | None = None) -> str:
        audio = _record_until_silence()
        if audio is None:
            return ""
        # Accent-aware decode: hint variety + don't let prior text bias this turn.
        segments, _ = self.model.transcribe(
            audio,
            language="en",
            initial_prompt=_INITIAL_PROMPT,
            condition_on_previous_text=False,
            temperature=(0.0, 0.4, 0.8),  # fall back to sampling if greedy misreads
        )
        raw = " ".join(s.text for s in segments).strip()
        clean = self._clean(raw)
        # If the only thing said was the wake word, return a sentinel so the
        # loop can answer "Yes?" without reprocessing.
        if wake_word and clean.lower() == wake_word.lower():
            return f"__WAKEONLY__{wake_word}"
        return clean


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
