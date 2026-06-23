"""
SEB Agent — main entry point.
Reads focused control via UIAutomation (no screenshot/OCR unless needed).
Only calls the AI when @@TAG@@ patterns are detected.
"""

import sys
import json
import time
import threading
import re
from pathlib import Path

# ── First-run: create settings.json if missing ────────────────────────────────
_SETTINGS_PATH = Path(__file__).parent / "settings.json"
if not _SETTINGS_PATH.exists():
    _SETTINGS_PATH.write_text(json.dumps({
        "api_key": "YOUR_GOOGLE_GEMINI_API_KEY_HERE",
        "poll_interval": 1.0,
        "response_mode": "auto",
        "model": "gemini-1.5-flash",
        "type_speed": 0.015,
        "language": "he",
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("✅ נוצר settings.json — הוסיפי את ה-Gemini API key ואז הריצי שוב.")
    sys.exit(0)

from config import Settings

if not Settings.get("api_key") or "YOUR_" in Settings["api_key"]:
    print("❌  חסר API key ב-settings.json")
    print("   קבלי מפתח חינמי בכתובת: https://aistudio.google.com/apikey")
    print("   הכניסי אותו בשדה api_key ב-settings.json, ואז הריצי שוב.")
    sys.exit(1)

from reader        import read_focused_text
from detector      import peek_tag, is_new, mark_processed
from claude_client import ask_ai
import popup_window
import typer
import pyperclip


# ── Clipboard helper (reads via UIAutomation, not Ctrl+C) ─────────────────────

def _copy_to_clipboard(text: str, label: str):
    try:
        pyperclip.copy(text)
        popup_window.show("COPY", f"✅ הועתק ל-Clipboard:\n\n{text[:300]}")
        print(f"[Agent] Clipboard ← {label} ({len(text)} תווים)")
    except Exception as e:
        popup_window.show("ERROR", f"שגיאה בהעתקה ל-Clipboard:\n{e}")


# ── Tag processing ────────────────────────────────────────────────────────────

def _handle(tag_type: str, content: str, full_text: str):
    print(f"[Agent] @@{tag_type}@@ ← '{content[:50]}{'...' if len(content)>50 else ''}'")

    # ── SCREENSHOT: take OS-level screenshot (bypasses SEB block) ───────────
    if tag_type == "SCREENSHOT":
        try:
            import pyautogui
            from datetime import datetime
            from pathlib import Path
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            save_path = Path(__file__).parent / filename
            img = pyautogui.screenshot()
            img.save(str(save_path))
            popup_window.show("SCREENSHOT", f"✅ צילום מסך נשמר:\n\n{save_path}")
            print(f"[Agent] Screenshot saved: {save_path}")
        except Exception as e:
            popup_window.show("ERROR", f"שגיאה בצילום מסך:\n{e}")
        return

    # ── ASKALL: ask a question about the full code in the field ─────────────
    if tag_type == "ASKALL":
        tag_pos = full_text.upper().find("@@ASKALL")
        code = full_text[:tag_pos].strip() if tag_pos > 0 else ""
        if not code:
            popup_window.show("ERROR", "⚠️ אין קוד מעל התגית\nדוגמה:\n  [הקוד שלך]\n  @@ASKALL: למה הלולאה לא עוצרת?@@")
            return
        if not content:
            popup_window.show("ERROR", "⚠️ כתבי שאלה בתוך התגית:\n@@ASKALL: השאלה שלך@@")
            return
        if len(code) > 2000:
            code = code[-2000:]
        try:
            print(f"[Agent] שולח ל-AI (ASKALL)...")
            response = ask_ai("ASKALL", f"Code:\n{code}\n\nQuestion: {content}")
            print(f"[Agent] תשובה התקבלה ({len(response)} תווים)")
            popup_window.show("ASK", response)
        except Exception as e:
            popup_window.show("ERROR", f"שגיאה:\n{e}")
        return

    # ── SOLVEALL: read full field content and solve the exercise ────────────
    if tag_type == "SOLVEALL":
        clean = re.sub(r'@@SOLVEALL@@', '', full_text).strip()
        if not clean:
            popup_window.show("ERROR", "⚠️ השדה ריק — אין תרגיל לקרוא")
            return
        if len(clean) > 3000:
            clean = clean[:3000]
        try:
            print(f"[Agent] שולח ל-AI (SOLVEALL, {len(clean)} תווים)...")
            response = ask_ai("SOLVEALL", clean)
            print(f"[Agent] תשובה התקבלה ({len(response)} תווים)")
            popup_window.show("SOLVE", response)
        except Exception as e:
            popup_window.show("ERROR", f"שגיאה:\n{e}")
        return

    # ── COPYALL: copy the entire text of the current field ──────────────────
    if tag_type == "COPYALL":
        # Remove the @@COPYALL@@ tag itself before copying
        clean = re.sub(r'@@COPYALL@@', '', full_text).strip()
        _copy_to_clipboard(clean, "כל השדה")
        return

    # ── COPYABOVE: copy everything above the @@COPYABOVE@@ tag ─────────────
    if tag_type == "COPYABOVE":
        tag_pos = full_text.upper().find("@@COPYABOVE@@")
        above = full_text[:tag_pos].strip() if tag_pos > 0 else ""
        if above:
            _copy_to_clipboard(above, "טקסט מעל התגית")
        else:
            popup_window.show("COPY", "⚠️ אין טקסט מעל התגית")
        return

    # ── COPY: copy the specific text written inside the tag ─────────────────
    if tag_type == "COPY":
        if content:
            _copy_to_clipboard(content, "טקסט מהתגית")
        else:
            popup_window.show("COPY", "⚠️ כתבי את הטקסט בתוך התגית: @@COPY: הטקסט@@")
        return

    # ── FIX: pass code above the tag as context ─────────────────────────────
    context = ""
    if tag_type == "FIX":
        tag_pos = full_text.upper().find("@@FIX")
        if tag_pos > 0:
            context = full_text[:tag_pos].rstrip()
            if len(context) > 1500:
                context = context[-1500:]
        # For FIX, we need at least the context or content
        if not content and not context:
            popup_window.show("ERROR", "⚠️ כתבי הוראה בתוך התגית:\n@@FIX: תאר את הבעיה@@\n\nהקוד שרוצה לתקן צריך להיות מעל התגית.")
            return

    # ── Validate content for ASK / SOLVE ────────────────────────────────────
    if tag_type in ("ASK", "SOLVE") and not content:
        examples = {
            "ASK":   "@@ASK: מה ההבדל בין list ל-tuple?@@",
            "SOLVE": "@@SOLVE: כתוב פונקציה שמחשבת עצרת@@",
        }
        popup_window.show("ERROR", f"⚠️ התגית ריקה. דוגמה:\n{examples[tag_type]}")
        return

    # ── Call AI (ASK / SOLVE / FIX) ─────────────────────────────────────────
    print(f"[Agent] שולח ל-AI...")
    try:
        response = ask_ai(tag_type, content, context)
        print(f"[Agent] תשובה התקבלה ({len(response)} תווים)")
    except Exception as e:
        popup_window.show("ERROR", f"שגיאה בתקשורת עם AI:\n\n{e}")
        print(f"[Agent] AI error: {e}")
        return

    mode = Settings.get("response_mode", "auto")

    if mode == "type":
        typer.append_below_tag(response)
    else:
        popup_window.show(tag_type, response)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  SEB Agent — פועל ברקע")
    print(f"  מודל: {Settings['model']} (חינמי)")
    print(f"  מצב תגובה: {Settings['response_mode']}")
    print("=" * 55)
    print()
    print("תגיות זמינות:")
    print("  @@ASK: שאלה@@        → הסבר קצר (ללא קוד מלא)")
    print("  @@SOLVE: משימה@@     → קוד מלא")
    print("  @@FIX: הוראה@@       → תיקון הקוד שמעל התגית")
    print("  @@COPY: טקסט@@       → שים טקסט ספציפי ב-Clipboard")
    print("  @@COPYABOVE@@        → שים את כל הטקסט שמעל ב-Clipboard")
    print("  @@COPYALL@@          → שים את כל תוכן השדה ב-Clipboard")
    print("  @@SCREENSHOT@@       → צלם מסך ושמור לקובץ PNG")
    print()
    print("ממתין לתגיות... (Ctrl+C להפסקה)")
    print()

    _last_read_preview = None
    _pending_key   = None   # "TAG:content" currently pending
    _pending_since = None   # when this key was first seen
    _pending_data  = None   # (tag_type, content, text) to pass to handler

    DEBOUNCE_WITH_CONTENT = 1.5   # wait for user to finish typing
    DEBOUNCE_BARE         = 0.5   # bare tags (SCREENSHOT, COPYALL etc.) — fire faster

    while True:
        try:
            text = read_focused_text()

            # Debug: only print when text changes
            preview = (text[:80].replace('\n', '↵') if text else "—")
            if preview != _last_read_preview:
                print(f"[reader] {preview}")
                _last_read_preview = preview

            if text and "@@" in text:
                result = peek_tag(text)
                if result:
                    tag_type, content = result
                    key = f"{tag_type}:{content}"

                    # Repeatable tags: always allowed to re-fire when rewritten
                    REPEATABLE = {"SCREENSHOT", "COPYALL", "COPYABOVE"}
                    if not is_new(tag_type, content) and tag_type not in REPEATABLE:
                        pass  # already processed, skip
                    elif key != _pending_key:
                        # New or changed tag — start debounce timer
                        _pending_key   = key
                        _pending_since = time.time()
                        _pending_data  = (tag_type, content, text)
                        print(f"[debounce] ממתין לתגית: {key[:40]}")
                    else:
                        debounce = DEBOUNCE_BARE if not content else DEBOUNCE_WITH_CONTENT
                        elapsed = time.time() - _pending_since
                        if elapsed >= debounce:
                            # Stable long enough — fire!
                            print(f"[debounce] יורה! {key[:40]}")
                            mark_processed(tag_type, content)
                            _pending_key   = None
                            _pending_since = None
                            threading.Thread(
                                target=_handle,
                                args=_pending_data,
                                daemon=True,
                            ).start()
            # NOTE: we do NOT reset pending when text disappears —
            # user may have just switched to another window temporarily.

        except KeyboardInterrupt:
            print("\n[Agent] נעצר.")
            sys.exit(0)
        except Exception as e:
            print(f"[Agent] שגיאה: {e}")

        time.sleep(0.3)


if __name__ == "__main__":
    main()
