"""
Floating response window (always-on-top).
Works alongside SEB when the exam allows other windows.
Includes a countdown button that types the response into the focused editor.
"""

import threading
import time
import tkinter as tk
from tkinter import scrolledtext

import typer

_lock = threading.Lock()
_active_root: tk.Tk | None = None

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


def _build_window(tag_type: str, content: str) -> tk.Tk:
    root = tk.Tk()
    root.title(f"סוכן AI · {tag_type}")
    root.configure(bg=BG)
    root.attributes("-topmost", True)
    root.geometry("480x320+40+40")
    root.resizable(True, True)

    accent = TAG_COLORS.get(tag_type, "#cdd6f4")

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
        try:
            import pyperclip
            pyperclip.copy(content)
        except Exception:
            root.clipboard_clear()
            root.clipboard_append(content)

    def make_type_btn():
        """Button that counts down 3s then types the content."""
        btn = tk.Button(btn_frame, text="⌨️  כתוב בעורך (3...)",
                        bg=SURFACE, fg=accent, relief="flat", padx=10,
                        font=("Consolas", 9))
        btn.pack(side="left", padx=3)

        def countdown():
            for i in (2, 1):
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
            time.sleep(0.4)   # let SEB editor regain focus
            typer.type_text(content)

        def on_click():
            btn.config(state="disabled", text="⌨️  כתוב בעורך (3...)")
            threading.Thread(target=countdown, daemon=True).start()

        btn.config(command=on_click)

    tk.Button(btn_frame, text="📋 העתק", command=copy_clip,
              bg=SURFACE, fg=FG, relief="flat", padx=10,
              font=("Consolas", 9)).pack(side="left", padx=3)

    if tag_type in ("SOLVE", "FIX"):
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
