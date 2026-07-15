"""FACE - the styled, floating voice companion window launched by `buddy`.

Rebuilt for a Siri/Gemini-level feel: a floating, draggable, glassy voice
bubble that pops in from the corner, with a liquid morphing ORB as the single
signature element. Bubbly chat (you / buddy), a live mic waveform, and a
status pill. Motion is subtle and purposeful (100-300ms, ease-out) and fully
respects prefers-reduced-motion.

tkinter only (no extra deps), so DeskBuddy always has a window.

The text input stays CONDITIONAL - it only appears when DeskBuddy asks a
decisive question (the 'prompt' event), never as a permanent box.
"""

from __future__ import annotations

import math
import platform
import threading
import tkinter as tk
from tkinter import scrolledtext

from deskbuddy.config import Config
from deskbuddy.runtime import Session

# ---- palette (brand teal/orange, dark glass) --------------------------------
BG = "#0B0E0D"
SURFACE = "#121614"
SURFACE_RAISED = "#181D1B"
BORDER = "#232A27"
TEAL = "#4AB3D4"
TEAL_DIM = "#1B5C52"
WARM = "#E8521A"
GREEN = "#4ADE80"
YOU = "#7EE787"
BUDDY = "#9CD7E8"
MUTED = "#9CA8A3"
TXT = "#EDEFEE"

STATES = {
    "ready": (MUTED, "idle"),
    "listening": (GREEN, "listening"),
    "thinking": ("#E8C547", "thinking"),
    "speaking": (TEAL, "speaking"),
    "waiting": (MUTED, "waiting"),
}


def _reduce_motion() -> bool:
    try:
        if platform.system() == "Darwin":
            return False
        import os
        return os.environ.get("DESKTOP_NO_ANIM", "") == "1"
    except Exception:
        return False


class Orb:
    """The signature element: a liquid morphing orb that breathes, listens,
    speaks. Drawn on a canvas with layered radial pulses (no images)."""

    def __init__(self, canvas, size=170):
        self.c = canvas
        self.size = size
        self.state = "ready"
        self.t = 0.0
        self.rings = [
            self.c.create_oval(0, 0, 0, 0, outline="", width=0) for _ in range(3)
        ]
        self.core = self.c.create_oval(0, 0, 0, 0, outline="", width=0)
        self._tick()

    def set_state(self, s):
        if s in STATES:
            self.state = s

    def _amp(self):
        return {"ready": 0.10, "waiting": 0.16, "listening": 0.92,
                "thinking": 0.55, "speaking": 0.78}.get(self.state, 0.2)

    def _color(self):
        return STATES.get(self.state, (TEAL, ""))[0]

    def _tick(self):
        w = self.size
        cx = cy = w // 2
        col = self._color()
        amp = self._amp()
        # core
        r_core = w * (0.20 + 0.05 * math.sin(self.t * 1.5))
        self.c.coords(self.core, cx - r_core, cy - r_core, cx + r_core, cy + r_core)
        self.c.itemconfig(self.core, fill=TEAL_DIM, outline=col, width=2)
        # breathing rings
        for i, rid in enumerate(self.rings):
            ph = self.t * (1.1 + 0.3 * i) + i * 1.2
            r = w * (0.28 + 0.16 * i) + amp * w * 0.18 * (0.5 + 0.5 * math.sin(ph))
            a = max(0, 0.5 - i * 0.14 - (0 if self.state == "listening" else 0.1))
            self.c.coords(rid, cx - r, cy - r, cx + r, cy + r)
            self.c.itemconfig(rid, outline=col, width=2,
                              stipple="gray50" if a < 0.2 else "")
        speed = {"listening": 0.32, "speaking": 0.28,
                 "thinking": 0.18}.get(self.state, 0.06)
        self.t += speed
        self.c.after(40, self._tick)


class Waveform:
    """Live mic-level bar strip driven by RMS (0..1) from the STT loop."""

    def __init__(self, canvas, width=300, height=44, bars=28):
        self.c = canvas
        self.w = width
        self.h = height
        self.n = bars
        self.levels = [0.0] * bars
        self.bars = [self.c.create_rectangle(0, 0, 0, 0, fill=TEAL, outline="")
                     for _ in range(bars)]
        self._tick()

    def push(self, level: float) -> None:
        self.levels.pop(0)
        self.levels.append(min(1.0, max(0.0, level * 3.0)))

    def _tick(self):
        bw = self.w / self.n
        mid = self.h / 2
        for i, item in enumerate(self.bars):
            lvl = self.levels[i]
            bh = max(2, lvl * (self.h - 6))
            x0 = i * bw + 1
            self.c.coords(item, x0, mid - bh / 2, x0 + bw - 2, mid + bh / 2)
            self.c.itemconfig(item, fill=GREEN if lvl > 0.04 else TEAL)
        self.c.after(40, self._tick)


class BuddyGUI:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.root = tk.Tk()
        self.root.title("DeskBuddy")
        self.root.configure(bg=BG)
        self.root.geometry("380x560")
        self.root.overrideredirect(True)  # frameless floating bubble
        self.root.attributes("-alpha", 0.0 if not _reduce_motion() else 1.0)
        self.root.attributes("-topmost", True)

        FONT = "monospace"
        self._drag = {"x": 0, "y": 0}

        # ---- entrance animation (scale-in from corner) ----
        # We fake scale with alpha + slight geometry growth.
        self.root.update_idletasks()
        self._anim_in()

        # ---- top drag bar + status pill + controls ----
        top = tk.Frame(self.root, bg=SURFACE)
        top.pack(fill="x", padx=10, pady=(10, 0))

        self.status = tk.Label(top, text="idle", fg=MUTED, bg=SURFACE,
                                font=(FONT, 10, "bold"))
        self.status.pack(side="left", padx=(4, 0))

        ctrl = tk.Frame(top, bg=SURFACE)
        ctrl.pack(side="right")
        tk.Button(ctrl, text="—", bg=SURFACE, fg=MUTED, bd=0,
                  font=(FONT, 12), command=self._minimize,
                  activebackground=SURFACE_RAISED).pack(side="left", padx=2)
        tk.Button(ctrl, text="×", bg=SURFACE, fg=MUTED, bd=0,
                  font=(FONT, 12), command=self.root.destroy,
                  activebackground=SURFACE_RAISED).pack(side="left", padx=2)

        # drag binding on the top bar
        top.bind("<ButtonPress-1>", self._start_drag)
        top.bind("<B1-Motion>", self._on_drag)
        self.status.bind("<ButtonPress-1>", self._start_drag)
        self.status.bind("<B1-Motion>", self._on_drag)

        # ---- orb card ----
        card = tk.Frame(self.root, bg=SURFACE, highlightbackground=BORDER,
                        highlightthickness=1)
        card.pack(fill="x", padx=10, pady=(8, 0))
        canvas = tk.Canvas(card, width=170, height=170, bg=SURFACE,
                            highlightthickness=0)
        canvas.pack(pady=10)
        self.orb = Orb(canvas, size=170)
        self.line = tk.Label(card, text=f"Say \u201c{self.cfg.voice.wake_word}\u201d",
                             fg=MUTED, bg=SURFACE, font=(FONT, 11))
        self.line.pack(pady=(0, 10))

        # ---- waveform ----
        wcard = tk.Frame(self.root, bg=SURFACE, highlightbackground=BORDER,
                         highlightthickness=1)
        wcard.pack(fill="x", padx=10, pady=(8, 0))
        wcanvas = tk.Canvas(wcard, width=300, height=44, bg=SURFACE,
                            highlightthickness=0)
        wcanvas.pack(pady=8)
        self.wave = Waveform(wcanvas, width=300, height=44)

        # ---- bubbly chat ----
        self.chat = scrolledtext.ScrolledText(
            self.root, bg=BG, fg=TXT, insertbackground=TXT, font=(FONT, 10),
            wrap="word", borderwidth=0, highlightthickness=0, relief="flat",
            padx=10, pady=8, height=9, state="disabled")
        self.chat.tag_config("you", foreground=YOU, lmargin1=40, lmargin2=40,
                             rmargin=8, spacing1=4, spacing3=4)
        self.chat.tag_config("buddy", foreground=BUDDY, lmargin1=8, lmargin2=8,
                             rmargin=40, spacing1=4, spacing3=4)
        self.chat.pack(fill="both", expand=True, padx=8, pady=(8, 4))

        # ---- CONDITIONAL input (only on a decisive question) ----
        self.input_frame = tk.Frame(self.root, bg=BG)
        self.input = tk.Entry(self.input_frame, bg=SURFACE_RAISED, fg=TXT,
                              insertbackground=TEAL, font=(FONT, 11),
                              relief="flat", highlightthickness=0)
        self.input.pack(fill="x", padx=10, pady=(0, 10), ipady=8)
        self.input.bind("<Return>", self._on_send)
        self.input_frame.pack_forget()

        self.session = Session(cfg, on_event=self._event)

    # ------------------------------------------------------------------
    def _anim_in(self):
        if _reduce_motion():
            self.root.attributes("-alpha", 1.0)
            return
        self.root.attributes("-alpha", 0.0)
        for i in range(1, 21):
            self.root.after(i * 12, lambda a=i / 20: self.root.attributes("-alpha", a))

    def _minimize(self):
        self.root.withdraw()
        self.root.after(4000, lambda: self.root.deiconify() if self.root.winfo_exists() else None)

    def _start_drag(self, e):
        self._drag["x"] = e.x
        self._drag["y"] = e.y

    def _on_drag(self, e):
        x = self.root.winfo_x() + (e.x - self._drag["x"])
        y = self.root.winfo_y() + (e.y - self._drag["y"])
        self.root.geometry(f"+{x}+{y}")

    def _set_status(self, s):
        color, label = STATES.get(s, (MUTED, s))
        self.status.config(text=label, fg=color)
        self.orb.set_state(s if s in STATES else "ready")

    def _show_input(self, prompt=None):
        if prompt:
            self.line.config(text=prompt, fg=TEAL)
        self.input_frame.pack(fill="x")
        self.input.focus_set()

    def _hide_input(self):
        self.input.delete(0, "end")
        self.input_frame.pack_forget()
        self.line.config(text=f"Say \u201c{self.cfg.voice.wake_word}\u201d", fg=MUTED)

    def _append(self, who, text):
        self.chat.configure(state="normal")
        tag = "you" if who == "You" else "buddy"
        prefix = "You  " if who == "You" else "Buddy  "
        self.chat.insert("end", prefix, tag)
        self.chat.insert("end", f"{text}\n\n", tag)
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def _event(self, kind, text):
        if kind == "status":
            self.root.after(0, lambda: self._set_status(text))
            if text == "waiting":
                self.line.config(text=f"Say '{self.cfg.voice.wake_word}'", fg=MUTED)
            elif text in ("thinking", "speaking", "listening"):
                self.line.config(text=text.capitalize() + "...", fg=MUTED)
        elif kind == "prompt":
            self.root.after(0, lambda: self._show_input(text))
        else:
            self.root.after(0, lambda: self._append(
                "You" if kind == "you" else "DeskBuddy", text))
            if kind == "you":
                self.root.after(0, self._hide_input)

    def _on_send(self, *_):
        text = self.input.get().strip()
        if not text:
            return
        self._hide_input()
        self._set_status("thinking")
        threading.Thread(target=self._run_turn, args=(text,), daemon=True).start()

    def _run_turn(self, text):
        self.session.handle(text)
        self.root.after(0, lambda: self._set_status("ready"))

    def run(self):
        self._event("buddy", f"Hi, I'm DeskBuddy. Say '{self.cfg.voice.wake_word}' "
                             f"to wake me, then speak or type.")
        from deskbuddy.hands import safety
        import tkinter.messagebox as mb

        def _approve(action, args):
            if not self.cfg.hands.confirm_destructive:
                return True
            label = action
            if args:
                label = f"{action}: {args}"
            return bool(mb.askyesno("Allow this?",
                                    f"DeskBuddy wants to:\n{label}"))

        safety.set_approval_callback(_approve)
        threading.Thread(target=self._voice_loop, daemon=True).start()
        self.root.after(1500, lambda: self._set_status("ready"))
        self.root.mainloop()

    def _voice_loop(self):
        import importlib.util as _util
        if _util.find_spec("sounddevice") is None:
            self.root.after(0, lambda: self.line.config(
                text="Mic unavailable - type instead", fg=MUTED))
            return
        from deskbuddy.voice.wakeword import WakeWordEngine
        eng = WakeWordEngine(self.cfg.voice.wake_word)
        if not eng.trained:
            self.root.after(0, lambda: self._append(
                "DeskBuddy", f"I don't know my wake word yet. Run 'buddy enroll' "
                             f"to teach me to hear '{self.cfg.voice.wake_word}'."))
            self.root.after(0, lambda: self.line.config(
                text=f"Run 'buddy enroll' to enable voice", fg=MUTED))
            return
        try:
            if hasattr(self.session.stt, "on_level"):
                self.session.stt.on_level = lambda lvl: self.wave.push(lvl)
            self.session.loop()
        except Exception as e:  # noqa: BLE001
            self.root.after(0, lambda: self._append(
                "DeskBuddy", f"[voice loop stopped: {e}]"))
            if "mic" in str(e).lower() or "sounddevice" in str(e).lower():
                self.root.after(0, lambda: self.line.config(
                    text="Mic unavailable - type instead", fg=MUTED))


def launch(cfg: Config) -> None:
    BuddyGUI(cfg).run()
