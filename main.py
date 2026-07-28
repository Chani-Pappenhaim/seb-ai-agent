"""
SEB Bot — main entry point.
Reads focused control via UIAutomation (no screenshot/OCR unless needed).
Only calls the AI when @@TAG@@ patterns are detected.
"""

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import time
import threading

from constants import (
    DEBOUNCE_WITH_CONTENT,
    DEBOUNCE_BARE,
    MAIN_LOOP_POLL_INTERVAL,
    TEXT_PREVIEW_LENGTH,
)

REQUIRED_PACKAGES = {
    "uiautomation": "uiautomation",
    "pyperclip": "pyperclip",
}


def _check_dependencies():
    """Fail fast with a clear message if required packages are missing."""
    missing = []
    for module_name, pip_name in REQUIRED_PACKAGES.items():
        try:
            __import__(module_name)
        except ImportError:
            missing.append(pip_name)

    if missing:
        print("❌ חסרות ספריות נדרשות:")
        for pkg in missing:
            print(f"   pip install {pkg}")
        print("\nאו הריצי: pip install -r requirements.txt")
        sys.exit(1)


_check_dependencies()

try:
    from config import Settings, is_api_key_configured
except Exception as e:
    print(f"❌  שגיאה בקובץ settings.json: {e}")
    print("   תקני את הערך ונסי שוב.")
    sys.exit(1)

if not is_api_key_configured(Settings):
    print("❌  חסר API key ב-settings.json")
    print("   Gemini (חינמי): https://aistudio.google.com/apikey")
    print("   הכניסי אותו בשדה api_key ב-settings.json, ואז הריצי שוב.")
    sys.exit(1)

from reader import read_focused_text
from detector import peek_tag, is_new, mark_processed, reset as reset_hash
from tag_handlers import dispatch

REPEATABLE_TAGS = {"SCREENSHOT", "COPYALL", "COPYABOVE"}


def _safe_dispatch(tag_type: str, content: str, full_text: str):
    """Wrapper so exceptions inside a handler don't silently kill the thread."""
    print(f"[Agent] @@{tag_type}@@ <- '{content[:50]}{'...' if len(content) > 50 else ''}'")
    try:
        dispatch(tag_type, content, full_text)
    except Exception as e:
        print(f"[Agent] Unhandled error in handler for @@{tag_type}@@: {e}")
        try:
            import ui_window
            ui_window.show("ERROR", f"שגיאה לא צפויה:\n{e}")
        except Exception:
            pass


def _print_banner():
    print("=" * 55)
    print("  SEB Bot — פועל ברקע")
    print(f"  מודל: {Settings['model']}")
    print(f"  מצב תגובה: {Settings['response_mode']}")
    print("=" * 55)
    print()
    print("תגיות זמינות:")
    print("  @@ASK: שאלה@@        -> הסבר קצר (ללא קוד מלא)")
    print("  @@SOLVE: משימה@@     -> קוד מלא")
    print("  @@FIX: הוראה@@       -> תיקון הקוד שמעל התגית")
    print("  @@COPY: טקסט@@       -> שים טקסט ספציפי ב-Clipboard")
    print("  @@COPYABOVE@@        -> שים את כל הטקסט שמעל ב-Clipboard")
    print("  @@COPYALL@@          -> שים את כל תוכן השדה ב-Clipboard")
    print("  @@SCREENSHOT@@       -> צלם מסך ושמור לקובץ PNG")
    print()
    print("ממתין לתגיות... (Ctrl+C להפסקה)")
    print()


def main():
    _print_banner()

    last_read_preview = None
    pending_key = None        # "TAG:content" currently pending
    pending_since = None      # when this key was first seen
    pending_data = None       # (tag_type, content, text) to pass to handler
    last_processed_key = None # track last fired tag to detect when it's removed

    while True:
        try:
            text = read_focused_text()

            preview = (text[:TEXT_PREVIEW_LENGTH].replace('\n', '↵') if text else "—")
            if preview != last_read_preview:
                print(f"[reader] {preview}")
                last_read_preview = preview

            if text and "@@" in text:
                result = peek_tag(text)

                # If a different complete tag now appears, reset the hash so
                # it can fire again (but ignore momentary incomplete tags).
                if last_processed_key and result:
                    current_key = f"{result[0]}:{result[1]}"
                    if current_key != last_processed_key:
                        reset_hash()
                        last_processed_key = None

                if result:
                    tag_type, content = result
                    key = f"{tag_type}:{content}"

                    if not is_new(tag_type, content) and tag_type not in REPEATABLE_TAGS:
                        pass  # already processed, skip
                    elif key != pending_key:
                        pending_key = key
                        pending_since = time.time()
                        pending_data = (tag_type, content, text)
                        print(f"[debounce] ממתין לתגית: {key[:40]}")
                    else:
                        debounce = DEBOUNCE_BARE if not content else DEBOUNCE_WITH_CONTENT
                        elapsed = time.time() - pending_since
                        if elapsed >= debounce:
                            print(f"[debounce] יורה! {key[:40]}")
                            mark_processed(tag_type, content)
                            last_processed_key = key
                            pending_key = None
                            pending_since = None
                            threading.Thread(
                                target=_safe_dispatch,
                                args=pending_data,
                                daemon=True,
                            ).start()
            # NOTE: we do NOT reset pending when text disappears —
            # user may have just switched to another window temporarily.

        except KeyboardInterrupt:
            print("\n[Agent] נעצר.")
            sys.exit(0)
        except Exception as e:
            print(f"[Agent] שגיאה: {e}")

        time.sleep(MAIN_LOOP_POLL_INTERVAL)


if __name__ == "__main__":
    main()
