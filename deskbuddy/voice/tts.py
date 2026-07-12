"""MOUTH - text to speech, with graceful fallbacks.

Tier order (best -> worst):
  1. kokoro   - FREE local neural TTS (studio quality, no API key, offline)
  2. edge-tts  - FREE online neural TTS (Microsoft natural voices)
  3. piper    - local neural, if installed
  4. espeak   - universal but robotic (last resort)

The voice config key `tts_voice` selects:
  - kokoro: a Kokoro voice id like "af_heart" / "am_adam" / "bf_emma"
  - edge-tts: a Microsoft voice like "en-US-AndrewNeural"
If unset, sensible defaults are chosen per engine.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

# Premium free voices worth knowing:
#   Kokoro:  af_heart (warm F), af_sky (bright F), am_adam (deep M),
#            bf_emma (UK F), bm_george (UK M)
#   edge-tts: en-US-AndrewNeural, en-GB-SoniaNeural, en-US-AriaNeural
KOKORO_VOICES = ("af_heart", "am_adam", "af_sky", "bf_emma")
EDGE_VOICES = ("en-US-AndrewNeural", "en-GB-SoniaNeural",
               "en-US-AriaNeural", "en-US-GuyNeural")


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


# Module-level preferred voice, set once at startup from config.
_PREFERRED: str = ""


def set_preferred(voice: str) -> None:
    """Set the preferred voice (called from config load / `buddy voice`)."""
    global _PREFERRED
    _PREFERRED = voice or ""


def list_voices() -> list[str]:
    """Voices the user can pick from."""
    return [*KOKORO_VOICES, *EDGE_VOICES]


def _play(path: str) -> bool:
    """Play an audio file; prefer ffplay, fall back to aplay."""
    if _have("ffplay"):
        r = subprocess.run(["ffplay", "-nodisp", "-autoexit",
                            "-loglevel", "quiet", path])
        return r.returncode == 0
    if _have("aplay"):
        r = subprocess.run(["aplay", "-q", path])
        return r.returncode == 0
    return False


def _kokoro_say(text: str, voice: str | None) -> bool:
    try:
        from kokoro_onnx import Kokoro
    except Exception:  # noqa: BLE001
        return False
    try:
        k = Kokoro()
        vid = voice if (voice and voice.startswith(("a", "b"))) else KOKORO_VOICES[0]
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav = f.name
        # Kokoro yields chunks; write the combined wav
        import soundfile as sf  # kokoro depends on it
        samples = []
        for _, audio in k.create(text, voice=vid, speed=1.0):
            samples.append(audio)
        if not samples:
            return False
        import numpy as np
        data = np.concatenate(samples)
        sf.write(wav, data, 24000)
        ok = _play(wav)
        Path(wav).unlink(missing_ok=True)
        return ok
    except Exception:  # noqa: BLE001
        return False


def _edge_say(text: str, voice: str | None) -> bool:
    try:
        import edge_tts
    except Exception:  # noqa: BLE001
        return False
    try:
        import asyncio
        vid = voice if voice else EDGE_VOICES[0]
        for try_v in (vid, *EDGE_VOICES):
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                mp3 = f.name
            try:
                async def go():
                    comm = edge_tts.Communicate(text, try_v)
                    await comm.save(mp3)
                asyncio.run(go())
                if Path(mp3).stat().st_size > 0 and _play(mp3):
                    Path(mp3).unlink(missing_ok=True)
                    return True
            except Exception:  # noqa: BLE001
                pass
            Path(mp3).unlink(missing_ok=True)
        return False
    except Exception:  # noqa: BLE001
        return False


def speak(text: str, voice: str = "") -> None:
    text = (text or "").strip()
    if not text:
        return
    voice = voice or _PREFERRED

    # 1. Kokoro - best free local neural voice
    if _kokoro_say(text, voice or None):
        return

    # 2. edge-tts - free online neural voice
    if _edge_say(text, voice or None):
        return

    # 3. piper (local neural) -> aplay
    if _have("piper") and _have("aplay"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav = f.name
            p = subprocess.run(["piper", "--output_file", wav],
                               input=text, text=True, capture_output=True)
            if p.returncode == 0 and _play(wav):
                Path(wav).unlink(missing_ok=True)
                return
            Path(wav).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    # 4. espeak-ng (robotic but universal, offline)
    if _have("espeak-ng"):
        subprocess.run(["espeak-ng", text])
        return
    if _have("espeak"):
        subprocess.run(["espeak", text])
        return

    # 5. speech-dispatcher
    if _have("spd-say"):
        subprocess.run(["spd-say", "-w", text])
        return

    # 6. last resort: print
    print(f"[DeskBuddy would say]: {text}")
