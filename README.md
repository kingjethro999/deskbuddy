# DeskBuddy

**Alexa, but for your PC.** A voice-powered desktop companion you install from
the terminal like Hermes — then say **"buddy"** and a styled GUI pops up,
listens to you, and operates your computer hands-off.

> Built by King Jethro Jerry. Inspired by how Hermes proved an agent can bridge
> to any interface — DeskBuddy makes *your own PC* the interactive, voice-first endpoint.

## Install (one line)

DeskBuddy is a **hybrid**: a voice/input skin over the real Hermes agent runtime.
The installer provisions both DeskBuddy and — if missing — the Hermes brain
(it runs Hermes's own installer, then `hermes setup`).

**Linux, macOS, WSL2:**

```bash
curl -fsSL https://raw.githubusercontent.com/kingjethro999/deskbuddy/main/scripts/install.sh | bash
```

**Windows (PowerShell):**

```powershell
iex (irm https://raw.githubusercontent.com/kingjethro999/deskbuddy/main/scripts/install.ps1)
```

Then:

```bash
buddy setup      # configure voice/input (and link to Hermes if you chose it)
buddy enroll     # teach it your wake word
buddy            # launch the GUI
```

> If Hermes wasn't already installed, the installer pulls it in automatically.
> After install, run `hermes setup` once to configure the brain (API key, provider).


## The idea

- Install via terminal (`curl | bash`), configure with a terminal setup wizard.
- Run `buddy` → the GUI loads.
- Talk to it. It listens (STT), thinks (LLM agent), acts on your PC (tools),
  and talks back (TTS).
- Opens apps, runs commands, types, presses keys, reads files, screenshots.

## Architecture (4 layers, cleanly separated)

```
deskbuddy/
  brain/   BRAIN  - the agent. Pluggable backends:
                    - native: our own OpenAI-compatible tool-calling loop
                    - hermes: shell out to the `hermes` CLI as the engine
  voice/   EARS+MOUTH - speech-to-text (Whisper) + text-to-speech (piper/edge/espeak)
  hands/   HANDS  - PC control tools (apps, shell, keyboard, mouse, files, screen)
  face/    FACE   - the styled GUI window (tkinter now; Electron/Tauri later)
  setup/   the terminal setup wizard
```

The **brain is pluggable on purpose** — DeskBuddy is its own product *and* can
ride on Hermes when you want its full power. Best of both.

## Quick start (dev)

```bash
cd ~/deskbuddy
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/buddy setup      # configure
.venv/bin/buddy doctor     # check environment + wake-word status
.venv/bin/buddy enroll     # teach it your wake word ("buddy")
.venv/bin/buddy --text     # terminal text loop (no mic/GUI needed)
.venv/bin/buddy --voice    # fully voice-first: wake word -> command
.venv/bin/buddy            # launch the GUI
.venv/bin/python -m pytest -q   # 21 tests
```

## Our own wake-word engine (no Porcupine, no paid SDK)

`voice/wakeword.py` implements keyword spotting from scratch with **MFCC
features + DTW template matching** (numpy only):

- `buddy enroll` — say your wake word a few times; it stores voice templates
  and self-calibrates a threshold.
- `buddy listen` / `buddy --voice` — streams the mic, matches against your
  templates, fires when it hears you. Offline, free, and it's *our code*.

## Runs on Linux, Windows, and macOS

DeskBuddy is cross-platform. The installer has one-liners for Linux/macOS
(`curl | bash`) and Windows PowerShell (`iex (irm ...)`), and the input-control
layer picks the right backend per OS at runtime:

- **Linux (X11)**: `xdotool` / `wmctrl` for full hands-off control.
- **Linux (Wayland)**: `ydotool` (+ `/dev/uinput`) for cross-window input.
  Wayland blocks apps from injecting input, so if `ydotool` isn't set up,
  DeskBuddy explains the limit and suggests an "Ubuntu on Xorg" session.
- **Windows**: PowerShell `SendKeys` for typing/keys, `nircmd` for clicks.
- **macOS**: AppleScript `System Events` for typing/keys, `cliclick` for clicks.

One interface (`hands/providers.py`), four backends. The brain (native or
Hermes) and the voice/wake-word layers are identical on every OS.

## Voice & hands-off (optional installs)

```bash
pip install 'deskbuddy[voice]'                    # wake word + local Whisper
sudo apt install ydotool wtype grim espeak-ng     # Wayland control + TTS
sudo apt install xdotool wmctrl scrot espeak-ng   # X11 control + TTS
```

## Status

Working now: project scaffold, pluggable brain (native + hermes), 8 PC-control
tools with cross-platform providers (Linux X11/Wayland, Windows, macOS),
STT/TTS with graceful fallbacks, terminal wizard, tkinter GUI, installer,
always-on wake word via our own MFCC+DTW engine (offline, free, no paid SDK),
streaming STT with WebRTC VAD silence detection, screen-vision (OCR + vision),
live GUI waveform, and packaging (PyInstaller binary + .deb).

Next: deeper native-brain tool use, richer GUI (Electron/Tauri), and a hosted
demo.
