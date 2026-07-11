"""FACE - the styled GUI window, launched by `buddy`.

tkinter (always present) so DeskBuddy has a real window with zero extra deps.
Now with a live waveform/orb visualizer that reflects mic/listening/thinking/
speaking states, plus the conversation log. Runs the Session on a background
thread so the UI stays responsive. Swappable for Electron/Tauri later without
touching brain/voice/hands.
"""
from __future__ import annotations

import math
import threading
import tkinter as tk
from tkinter import scrolledtext

from deskbuddy.config import Config
from deskbuddy.runtime import Session

BG = "#0d1117"
FG = "#e6edf3"
ACCENT = "#58a6ff"
YOU = "#7ee787"
BUDDY = "#d2a8ff"
MUTED = "#8b949e"

# state -> (color, label)
STATES = {
    "ready":     (MUTED,   "ready"),
    "listening": ("#3fb950", "listening"),
    "thinking":  ("#d29922", "thinking"),
    "speaking":  (BUDDY,    "speaking"),
}


class Visualizer:
    """A pulsing ring of bars - a lightweight 'voice orb' driven by state."""

    def __init__(self, canvas: tk.Canvas, size: int = 120):
        self.c = canvas
        self.size = size
        self.n = 32
        self.phase = 0.0
        self.state = "ready"
        self.bars = [self.c.create_line(0, 0, 0, 0, width=3, fill=ACCENT)
                     for _ in range(self.n)]
        self._tick()

    def set_state(self, state: str):
        self.state = state if state in STATES else "ready"

    def _amp(self) -> float:
        return {"ready": 0.15, "listening": 0.9, "thinking": 0.5,
                "speaking": 0.75}.get(self.state, 0.2)

    def _tick(self):
        cx = cy = self.size // 2 + 10
        r0 = self.size * 0.28
        color = STATES.get(self.state, (ACCENT, ""))[0]
        amp = self._amp()
        for i, item in enumerate(self.bars):
            ang = (i / self.n) * 2 * math.pi
            wobble = amp * (0.5 + 0.5 * math.sin(self.phase * 2 + i * 0.6))
            r1 = r0 + self.size * 0.18 * wobble
            x0, y0 = cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)
            x1, y1 = cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)
            self.c.coords(item, x0, y0, x1, y1)
            self.c.itemconfig(item, fill=color)
        speed = {"listening": 0.35, "speaking": 0.3, "thinking": 0.2}.get(
            self.state, 0.08)
        self.phase += speed
        self.c.after(40, self._tick)


class BuddyGUI:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.root = tk.Tk()
        self.root.title("DeskBuddy")
        self.root.configure(bg=BG)
        self.root.geometry("560x720")

        tk.Label(self.root, text="DeskBuddy", fg=ACCENT, bg=BG,
                 font=("JetBrains Mono", 20, "bold")).pack(pady=(16, 2))

        canvas = tk.Canvas(self.root, width=160, height=160, bg=BG,
                           highlightthickness=0)
        canvas.pack(pady=4)
        self.viz = Visualizer(canvas, size=140)

        self.status = tk.Label(self.root, text="ready", fg=MUTED, bg=BG,
                               font=("JetBrains Mono", 10))
        self.status.pack()

        self.log = scrolledtext.ScrolledText(
            self.root, bg="#010409", fg=FG, insertbackground=FG,
            font=("JetBrains Mono", 11), wrap="word", borderwidth=0,
            padx=12, pady=12)
        self.log.pack(fill="both", expand=True, padx=12, pady=12)
        self.log.tag_config("you", foreground=YOU)
        self.log.tag_config("buddy", foreground=BUDDY)
        self.log.configure(state="disabled")

        entry_frame = tk.Frame(self.root, bg=BG)
        entry_frame.pack(fill="x", padx=12, pady=(0, 12))
        self.entry = tk.Entry(entry_frame, bg="#161b22", fg=FG,
                              insertbackground=FG, font=("JetBrains Mono", 12),
                              relief="flat")
        self.entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        self.entry.bind("<Return>", self._on_send)
        tk.Button(entry_frame, text="Send", command=self._on_send, bg=ACCENT,
                  fg="#0d1117", relief="flat",
                  font=("JetBrains Mono", 11, "bold")).pack(
                      side="right", ipadx=10, ipady=4)

        self.session = Session(cfg, on_event=self._event)

    def _set_status(self, text: str):
        label = STATES.get(text, (MUTED, text))[1]
        self.status.config(text=label, fg=STATES.get(text, (MUTED, ""))[0])
        self.viz.set_state(text if text in STATES else "ready")

    def _event(self, kind: str, text: str):
        if kind == "status":
            self.root.after(0, lambda: self._set_status(text))
            return
        who = "You" if kind == "you" else "DeskBuddy"
        tag = "you" if kind == "you" else "buddy"
        if kind == "buddy":
            self.root.after(0, lambda: self._set_status("speaking"))
        def append():
            self.log.configure(state="normal")
            self.log.insert("end", f"{who}: ", tag)
            self.log.insert("end", f"{text}\n\n")
            self.log.see("end")
            self.log.configure(state="disabled")
        self.root.after(0, append)

    def _on_send(self, *_):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        self._set_status("thinking")
        threading.Thread(target=self._run_turn, args=(text,), daemon=True).start()

    def _run_turn(self, text: str):
        self.session.handle(text)
        self.root.after(0, lambda: self._set_status("ready"))

    def run(self):
        self._event("buddy", "Hi! I'm DeskBuddy. Type or talk to me.")
        self.root.after(1500, lambda: self._set_status("ready"))
        self.root.mainloop()


def launch(cfg: Config) -> None:
    BuddyGUI(cfg).run()
