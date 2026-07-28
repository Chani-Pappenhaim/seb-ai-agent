"""
Floating response window (always-on-top).
Works alongside SEB when the exam allows other windows.
Includes a countdown button that types the response into the focused editor.
"""

import threading
import time
import tkinter as tk
from tkinter import scrolledtext
from typing import Optional

import keyboard_input
from clipboard_utils import copy_to_clipboard
from constants import POPUP_GEOMETRY, TYPE_BUTTON_COUNTDOWN_SECONDS, FOCUS_REGAIN_DELAY

_lock = threading.Lock()
_active_root: Optional[tk.Tk] = None

TAG_COLORS = {
    "ASK":   "#89dceb",  # light blue
    "SOLVE": "#a6e3a1",  # green
    "FIX":   "#fab387",  # orange
    "COPY":  "#cba6f7",  # purple
    "ERROR": "#f38ba8",  # red
}

BG      = "#1e1e2e"
SURFACE = "#313244"
FG      = "#cdd6f4"
MUTED   = "#6c7086"

TYPE_ELIGIBLE_TAGS = ("SOLVE", "FIX")


def _build_window(tag_type: str, content: str) -> tk.Tk:
    root = tk.Tk()
    root.title(f"SEB Bot · {tag_type}")
    root.configure(bg=BG)
    root.attributes("-topmost", True)
    root.geometry(POPUP_GEOMETRY)
    root.resizable(True, True)

    accent = TAG_COLORS.get(tag_type, FG)

    # ── Header ───────────────────────────────────────────────────────────────
    hdr = tk.Frame(root, bg=SURFACE, pady=6)
    hdr.pack(fill="x")
    tk.Label(hdr, text=f"  [{tag_type}]", bg=SURFACE, fg=accent,
             font=("Consolas", 11, "bold")).pack(side="left")
    tk.Button(hdr, text="✖", command=root.destroy,
              bg=SURFACE, fg=MUTED, relief="flat",
              font=("Consolas", 10), bd=0, padx=8).pack(side="right")

    # ── Content ───────────────────────────────────────────────────────────────
    txt = scrolledtext.ScrolledText(
        root, wrap=tk.WORD, bg=BG, fg=FG,
        font=("Consolas", 10), relief="flat",
        padx=10, pady=8, insertbackground=FG,
    )
    txt.pack(fill="both", expand=True, padx=4, pady=4)
    txt.insert("1.0", content)
    txt.config(state="disabled")

    # ── Buttons ───────────────────────────────────────────────────────────────
    btn_frame = tk.Frame(root, bg=BG)
    btn_frame.pack(fill="x", padx=6, pady=(0, 6))

    def copy_clip():
        copy_to_clipboard(content)

    def make_type_btn():
        """Button that counts down then types the content into the editor."""
        btn = tk.Button(
            btn_frame,
            text=f"⌨️  כתוב בעורך ({TYPE_BUTTON_COUNTDOWN_SECONDS}...)",
            bg=SURFACE, fg=accent, relief="flat", padx=10,
            font=("Consolas", 9),
        )
        btn.pack(side="left", padx=3)

        def countdown():
            for i in range(TYPE_BUTTON_COUNTDOWN_SECONDS - 1, 0, -1):
                time.sleep(1)
                try:
                    btn.config(text=f"⌨️  כתוב בעורך ({i}...)")
                except Exception:
                    return
            time.sleep(1)
            try:
                root.destroy()
            except Exception:
                pass
            time.sleep(FOCUS_REGAIN_DELAY)  # let SEB editor regain focus
            keyboard_input.type_text(content)

        def on_click():
            btn.config(state="disabled")
            threading.Thread(target=countdown, daemon=True).start()

        btn.config(command=on_click)

    tk.Button(btn_frame, text="📋 העתק", command=copy_clip,
              bg=SURFACE, fg=FG, relief="flat", padx=10,
              font=("Consolas", 9)).pack(side="left", padx=3)

    if tag_type in TYPE_ELIGIBLE_TAGS:
        make_type_btn()

    return root


def show(tag_type: str, content: str):
    """Open (or replace) the floating popup. Thread-safe."""
    global _active_root

    def _run():
        global _active_root
        with _lock:
            if _active_root:
                try:
                    _active_root.destroy()
                except Exception:
                    pass
            root = _build_window(tag_type, content)
            _active_root = root
        root.mainloop()
        with _lock:
            if _active_root is root:
                _active_root = None

    threading.Thread(target=_run, daemon=True).start()
