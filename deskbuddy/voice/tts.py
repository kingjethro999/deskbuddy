"""MOUTH - text to speech, with fallbacks.

Order of preference: piper -> edge-tts -> espeak-ng -> spd-say -> print only.
DeskBuddy always speaks *something*; if no engine exists it prints the line so
the loop still works during setup.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def speak(text: str, voice: str = "en_US") -> None:
    text = (text or "").strip()
    if not text:
        return

    # 1. edge-tts (online, NATURAL, free) - preferred over robotic espeak
    if _have("edge-tts") and _have("ffplay"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                mp3 = f.name
            # a few voices; first that works
            for vt in ("en-US-AndrewNeural", "en-US-AriaNeural",
                        "en-GB-SoniaNeural", "en-US-GuyNeural"):
                p = subprocess.run(
                    ["edge-tts", "--voice", vt, "--text", text,
                     "--write-media", mp3],
                    capture_output=True)
                if p.returncode == 0:
                    subprocess.run(["ffplay", "-nodisp", "-autoexit",
                                     "-loglevel", "quiet", mp3])
                    Path(mp3).unlink(missing_ok=True)
                    return
            Path(mp3).unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    # 2. piper (high quality, offline) -> pipe to aplay
    if _have("piper") and _have("aplay"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                wav = f.name
            p = subprocess.run(["piper", "--output_file", wav],
                               input=text, text=True, capture_output=True)
            if p.returncode == 0:
                subprocess.run(["aplay", "-q", wav])
                Path(wav).unlink(missing_ok=True)
                return
        except Exception:  # noqa: BLE001
            pass

    # 2. edge-tts (online, natural)
    if _have("edge-tts") and _have("ffplay"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                mp3 = f.name
            p = subprocess.run(["edge-tts", "--text", text, "--write-media", mp3],
                               capture_output=True)
            if p.returncode == 0:
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-loglevel",
                               "quiet", mp3])
                Path(mp3).unlink(missing_ok=True)
                return
        except Exception:  # noqa: BLE001
            pass

    # 3. espeak-ng (robotic but universal, offline)
    if _have("espeak-ng"):
        subprocess.run(["espeak-ng", text])
        return
    if _have("espeak"):
        subprocess.run(["espeak", text])
        return

    # 4. speech-dispatcher
    if _have("spd-say"):
        subprocess.run(["spd-say", "-w", text])
        return

    # 5. last resort: print
    print(f"[DeskBuddy would say]: {text}")
