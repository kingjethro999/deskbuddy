"""DeskBuddy - Alexa for your PC.

A voice-powered desktop companion: terminal install, terminal setup wizard,
and a styled GUI launched with the `buddy` command. Fully voice-driven,
operates your PC hands-off.

Layers:
    brain/  - the agent: pluggable backends (native LLM loop, or Hermes).
    voice/  - ears + mouth: wake word, speech-to-text, text-to-speech.
    hands/  - PC control: apps, shell, keyboard/mouse, files, screen.
    face/   - the GUI window.
    setup/  - terminal setup wizard.
"""

__version__ = "0.1.0"
