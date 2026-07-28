"""
Clipboard operations — single source of truth for copy-to-clipboard logic.
Used by both the main tag handlers and the popup window's copy button.
"""


def copy_to_clipboard(text: str) -> bool:
    """
    Copy text to the system clipboard.
    Tries pyperclip first (works without a visible Tk window),
    falls back to a throwaway Tk instance if pyperclip is unavailable.

    Returns True on success, False on failure.
    """
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except Exception as e:
        print(f"[clipboard] pyperclip failed ({e}), trying Tk fallback...")

    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        return True
    except Exception as e:
        print(f"[clipboard] Tk fallback also failed: {e}")
        return False
