"""
Type text directly into the focused window via keyboard simulation.
Used as fallback when popup windows are blocked by SEB.
"""

import time
from config import Settings


def type_text(text: str):
    """Simulate keystrokes to type text into the active window."""
    delay = Settings.get("type_speed", 0.015)

    # Prefer `keyboard` library — handles unicode + Hebrew better than pyautogui
    try:
        import keyboard
        keyboard.write(text, delay=delay)
        return
    except Exception:
        pass

    # Fallback: pyautogui (ASCII only, may drop unicode)
    try:
        import pyautogui
        pyautogui.write(text, interval=delay)
    except Exception as e:
        print(f"[typer] Could not type text: {e}")


def append_below_tag(response: str):
    """
    Fallback mode when popup is blocked.
    Assumes cursor is on/near the @@TAG:...@@ line.
    Moves to end of that line and types response on new lines.
    """
    try:
        import keyboard
        keyboard.press_and_release("end")
        time.sleep(0.15)
        keyboard.press_and_release("enter")
        time.sleep(0.1)
        keyboard.press_and_release("enter")
        time.sleep(0.1)
        type_text(response)
    except Exception as e:
        print(f"[typer] append_below_tag error: {e}")
