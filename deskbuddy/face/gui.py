"""FACE - the styled GUI window, launched by `buddy`.

tkinter (always present) so DeskBuddy has a real window with zero extra deps.
Modernized: glass card, calm palette, the voice-orb you liked kept as the
centerpiece. The text input is CONDITIONAL - it only appears when DeskBuddy
asks a decisive question (the 'prompt' event), never as a permanent box.
Spoken turns show as a brief, auto-fading transcript line, not a chat dump.
Swappable for Electron/Tauri later without touching brain/voice/hands.
"""
from __future__ import annotations

import math
import threading
import tkinter as tk
from tkinter import scrolledtext

from deskbuddy.config import Config
from deskbuddy.runtime import Session

BG     = "#0b0e14"   # near-black navy
CARD   = "#121722"
LINE   = "#1f2733"
ACCENT = "#5b8cff"   # calm blue
YOU    = "#7ee787"
BUDDY  = "#c4a7ff"
MUTED  = "#6b7785"
TXT    = "#e6edf3"

STATES = {
    "ready":     (MUTED,  "idle"),
    "listening": ("#3fb950", "listening"),
    "thinking":  ("#d29922", "thinking"),
    "speaking": (BUDDY,   "speaking"),
}


class Orb:
    """The pulsing ring of bars you liked - a lightweight voice orb."""

    def __init__(self, canvas, size=150):
        self.c = canvas
        self.size = size
        self.n = 40
        self.phase = 0.0
        self.state = "ready"
        self.bars = [self.c.create_line(0, 0, 0, 0, width=3, fill=ACCENT)
                     for _ in range(self.n)]
        self._tick()

    def set_state(self, s):
        self.state = s if s in STATES else "ready"

    def _amp(self):
        return {"ready": 0.12, "listening": 0.95,
                "thinking": 0.5, "speaking": 0.78}.get(self.state, 0.2)

    def _tick(self):
        cx = cy = self.size // 2 + 8
        r0 = self.size * 0.30
        color = STATES.get(self.state, (ACCENT, ""))[0]
        amp = self._amp()
        for i, item in enumerate(self.bars):
            ang = (i / self.n) * 2 * math.pi
            wob = amp * (0.5 + 0.5 * math.sin(self.phase * 2 + i * 0.5))
            r1 = r0 + self.size * 0.17 * wob
            x0, y0 = cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)
            x1, y1 = cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)
            self.c.coords(item, x0, y0, x1, y1)
            self.c.itemconfig(item, fill=color)
        speed = {"listening": 0.35, "speaking": 0.3,
                 "thinking": 0.2}.get(self.state, 0.07)
        self.phase += speed
        self.c.after(40, self._tick)


class BuddyGUI:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.root = tk.Tk()
        self.root.title("DeskBuddy")
        self.root.configure(bg=BG)
        self.root.geometry("460x680")
        self.root.resizable(False, False)
        self.root.option_add("*Font", "JetBrains Mono 11")

        # ---- header ----
        hd = tk.Frame(self.root, bg=BG)
        hd.pack(fill="x", padx=22, pady=(22, 6))
        tk.Label(hd, text="DeskBuddy", fg=ACCENT, bg=BG,
                 font=("JetBrains Mono", 17, "bold")).pack(side="left")
        self.status = tk.Label(hd, text="idle", fg=MUTED, bg=BG,
                               font=("JetBrains Mono", 10))
        self.status.pack(side="right")

        # ---- orb card ----
        card = tk.Frame(self.root, bg=CARD, highlightbackground=LINE,
                         highlightthickness=1)
        card.pack(fill="x", padx=22, pady=10)
        canvas = tk.Canvas(card, width=180, height=180, bg=CARD,
                            highlightthickness=0)
        canvas.pack(pady=18)
        self.orb = Orb(canvas, size=150)
        self.line = tk.Label(card, text="Say \u201cbuddy\u201d",
                            fg=MUTED, bg=CARD,
                            font=("JetBrains Mono", 11))
        self.line.pack(pady=(0, 18))

        # ---- transcript (brief, fades - NOT a permanent textarea) ----
        self.transcript = scrolledtext.ScrolledText(
            self.root, bg=BG, fg=TXT, insertbackground=TXT,
            font=("JetBrains Mono", 10), wrap="word", borderwidth=0,
            highlightthickness=0, relief="flat", padx=22, pady=8,
            height=7, state="disabled")
        self.transcript.tag_config("you", foreground=YOU)
        self.transcript.tag_config("buddy", foreground=BUDDY)
        self.transcript.pack(fill="both", expand=True, padx=14, pady=(6, 4))

        # ---- CONDITIONAL input (only on a decisive question) ----
        self.input_frame = tk.Frame(self.root, bg=BG)
        self.input = tk.Entry(self.input_frame, bg=CARD, fg=TXT,
                              insertbackground=ACCENT,
                              font=("JetBrains Mono", 11),
                              relief="flat", highlightthickness=0)
        self.input.pack(fill="x", padx=22, pady=(0, 18), ipady=9)
        self.input.bind("<Return>", self._on_send)
        self.input_frame.pack_forget()  # hidden until asked

        self.session = Session(cfg, on_event=self._event)

    # ------------------------------------------------------------------
    def _set_status(self, s):
        color, label = STATES.get(s, (MUTED, s))
        self.status.config(text=label, fg=color)
        self.orb.set_state(s if s in STATES else "ready")

    def _show_input(self, prompt=None):
        if prompt:
            self.line.config(text=prompt, fg=ACCENT)
        self.input_frame.pack(fill="x")  # reveal ONLY now
        self.input.focus_set()

    def _hide_input(self):
        self.input.delete(0, "end")
        self.input_frame.pack_forget()
        self.line.config(text="Say \u201cbuddy\u201d", fg=MUTED)

    def _append(self, who, text):
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{who}: ", who.lower())
        self.transcript.insert("end", f"{text}\n\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def _event(self, kind, text):
        if kind == "status":
            self.root.after(0, lambda: self._set_status(text))
            if text in ("thinking", "speaking", "listening"):
                self.line.config(text=text.capitalize() + "...", fg=MUTED)
        elif kind == "prompt":
            # decisive question -> reveal the input just for this
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
        threading.Thread(target=self._run_turn, args=(text,),
                          daemon=True).start()

    def _run_turn(self, text):
        self.session.handle(text)
        self.root.after(0, lambda: self._set_status("ready"))

    def run(self):
        self._event("buddy", "Hi, I'm DeskBuddy. Speak or type to me.")
        self.root.after(1500, lambda: self._set_status("ready"))
        self.root.mainloop()


def launch(cfg: Config) -> None:
    BuddyGUI(cfg).run()
