"""FACE - the styled, floating voice companion window launched by `buddy`.

The premium face is a real WebView (HTML/CSS/JS) window via pywebview, so it
can deliver the Siri/Gemini-level look (glass, fluid motion, bubbly chat) that
tkinter cannot. tkinter is kept only as a last-resort fallback when pywebview
or a WebView backend is unavailable.

The text input stays CONDITIONAL - it only appears when DeskBuddy asks a
decisive question (the 'prompt' event), never as a permanent box.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

from deskbuddy.config import Config
from deskbuddy.runtime import Session

# pywebview's GTK backend needs PyGObject (`gi`). On Debian/Ubuntu the system
# provides it (python3-gi) but it's often NOT inside a venv. Auto-discover the
# system dist-packages so `buddy` works without manual PYTHONPATH.
_GI_CANDIDATES = [
    "/usr/lib/python3/dist-packages",
    "/usr/lib/python3/site-packages",
]
for _p in _GI_CANDIDATES:
    if Path(_p, "gi").exists() and _p not in sys.path:
        sys.path.insert(0, _p)
        break

HERE = Path(__file__).parent
HAS_WEBVIEW = False
try:
    import webview  # noqa: F401
    HAS_WEBVIEW = True
except Exception:  # noqa: BLE001
    pass


class _Api:
    """Bridge object exposed to JS as window.pywebview.api."""

    def __init__(self, gui: "WebViewFace"):
        self._gui = gui

    def dom_ready(self):
        # called by JS once buddyEvent is defined and the DOM is ready
        self._gui._ready.set()
        self._gui._event("buddy",
                         f"Hi, I'm DeskBuddy. Say '{self._gui.cfg.voice.wake_word}' "
                         f"to wake me, then speak or type.")
        import threading
        threading.Thread(target=self._gui._voice_loop, daemon=True).start()

    def user_text(self, text: str):
        self._gui._on_user_text(text)

    def minimize(self):
        try:
            self._gui._window.minimize()
        except Exception:  # noqa: BLE001
            pass

    def close(self):
        try:
            self._gui._window.destroy()
        except Exception:  # noqa: BLE001
            pass


class WebViewFace:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._ready = threading.Event()
        self._window = None
        self.session = Session(cfg, on_event=self._event)

    # ---- Session -> JS ----
    def _event(self, kind: str, text: str):
        if self._window is None or not self._ready.is_set():
            return
        # push over the pywebview JS bridge
        self._window.evaluate_js(
            f"window.buddyEvent({kind!r}, {text!r})")

    def _on_user_text(self, text: str):
        self._set_status("thinking")
        threading.Thread(target=self._run_turn, args=(text,), daemon=True).start()

    def _run_turn(self, text: str):
        self.session.handle(text)
        self._set_status("ready")

    def _set_status(self, s: str):
        if self._window and self._ready.is_set():
            self._window.evaluate_js(f"window.buddyEvent('status', {s!r})")

    # ---- launch ----
    def run(self):
        import webview
        from deskbuddy.hands import safety
        import tkinter.messagebox as mb

        def _approve(action, args):
            if not self.cfg.hands.confirm_destructive:
                return True
            label = f"{action}: {args}" if args else action
            return bool(mb.askyesno("Allow this?", f"DeskBuddy wants to:\n{label}"))

        safety.set_approval_callback(_approve)

        html = (HERE / "index.html").read_text()
        self._window = webview.create_window(
            "DeskBuddy", html=html,
            js_api=_Api(self),
            width=380, height=560,
            frameless=True, on_top=True,
            x=None, y=None,
        )
        # The greeting + voice loop are triggered by JS calling api.dom_ready()
        # once buddyEvent is defined (avoids the async-asset race), so we do NOT
        # also hook events.loaded here.
        webview.start(debug=False)

    def _voice_loop(self):
        try:
            from deskbuddy.voice.wakeword import WakeWordEngine
        except Exception as e:  # noqa: BLE001
            self._event("buddy", f"[voice unavailable: {e}]")
            return
        eng = WakeWordEngine(self.cfg.voice.wake_word)
        if not eng.trained:
            self._event("buddy",
                        f"I don't know my wake word yet. Run 'buddy enroll' "
                        f"to teach me to hear '{self.cfg.voice.wake_word}'.")
            return
        try:
            if hasattr(self.session.stt, "on_level"):
                # forward mic RMS to the JS waveform
                orig = self.session.stt.on_level
                def _fwd(lvl):
                    if self._window and self._ready.is_set():
                        self._window.evaluate_js(
                            f"window.buddyEvent('level', {lvl!r})")
                    if callable(orig):
                        orig(lvl)
                self.session.stt.on_level = _fwd
            self.session.loop()
        except Exception as e:  # noqa: BLE001
            self._event("buddy", f"[voice loop stopped: {e}]")


def launch(cfg: Config) -> None:
    if HAS_WEBVIEW:
        WebViewFace(cfg).run()
    else:
        # fallback to the plain tkinter window
        from deskbuddy.face import gui_tk as tkface
        tkface.launch(cfg)
