"""
Type text directly into the focused window via keyboard simulation.
Used as fallback when popup windows are blocked by SEB.

Note: named keyboard_input.py (not typer.py) to avoid shadowing
the third-party 'typer' CLI framework package.
"""

import time
from config import Settings
from constants import KEY_PRESS_DELAY, KEY_PRESS_DELAY_SHORT


def type_text(text: str):
    """Simulate keystrokes to type text into the active window."""
    delay = Settings.get("type_speed", 0.015)

    # Prefer `keyboard` library — handles unicode + Hebrew better than pyautogui
    try:
        import keyboard
        keyboard.write(text, delay=delay)
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"[keyboard_input] keyboard library failed: {e}")

    # Fallback: pyautogui (ASCII only, may drop unicode)
    try:
        import pyautogui
        pyautogui.write(text, interval=delay)
    except ImportError:
        print("[keyboard_input] Neither 'keyboard' nor 'pyautogui' installed.")
    except Exception as e:
        print(f"[keyboard_input] Could not type text: {e}")


def append_below_tag(response: str):
    """
    Fallback mode when popup is blocked.
    Assumes cursor is on/near the @@TAG:...@@ line.
    Moves to end of that line and types response on new lines.
    """
    try:
        import keyboard
        keyboard.press_and_release("end")
        time.sleep(KEY_PRESS_DELAY)
        keyboard.press_and_release("enter")
        time.sleep(KEY_PRESS_DELAY_SHORT)
        keyboard.press_and_release("enter")
        time.sleep(KEY_PRESS_DELAY_SHORT)
        type_text(response)
    except ImportError:
        print("[keyboard_input] 'keyboard' library not installed — cannot append text.")
    except Exception as e:
        print(f"[keyboard_input] append_below_tag error: {e}")
