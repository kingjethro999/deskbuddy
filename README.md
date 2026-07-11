# DeskBuddy

**Alexa, but for your PC.** A voice-powered desktop companion you install from
the terminal like Hermes — then say **"buddy"** and a styled GUI pops up,
listens to you, and operates your computer hands-off.

> Built by King Jethro Jerry. Inspired by how Hermes proved an agent can bridge
> to any interface — DeskBuddy makes *your own PC* the interactive, voice-first endpoint.

## Install (one line)

```bash
curl -fsSL https://raw.githubusercontent.com/kingjethro999/deskbuddy/main/scripts/install.sh | bash
```

Then:

```bash
buddy setup      # choose standalone (Ollama/Nous/OpenAI...) or link to Hermes
buddy enroll     # teach it your wake word
buddy            # launch the GUI
```


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

## The Wayland lesson (baked into the design)

Wayland deliberately blocks apps from injecting input into other windows. So
`hands/providers.py` picks the best method at runtime — `X11Provider`
(xdotool/wmctrl), `WaylandProvider` (ydotool when `/dev/uinput` works), or a
`NullProvider` that explains the limitation and suggests logging into an
"Ubuntu on Xorg" session for full hands-off control.

## Voice & hands-off (optional installs)

```bash
pip install 'deskbuddy[voice]'                    # wake word + local Whisper
sudo apt install ydotool wtype grim espeak-ng     # Wayland control + TTS
sudo apt install xdotool wmctrl scrot espeak-ng   # X11 control + TTS
```

## Status

Working now: project scaffold, pluggable brain (native + hermes), 8 PC-control
tools, STT/TTS with graceful fallbacks, terminal wizard, tkinter GUI, installer.

Next: always-on wake-word detection ("buddy") via openWakeWord, streaming
STT with silence detection, screen-vision tool, richer GUI (waveform), packaging.
