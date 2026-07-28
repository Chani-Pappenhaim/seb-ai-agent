"""
Tag handlers — one function per @@TAG@@ type.
Each handler receives (content, full_text) and is responsible for its
own side effects (showing a popup, copying to clipboard, etc).

To add a new tag: write a handler function here and register it in HANDLERS.
"""

import re
from datetime import datetime
from pathlib import Path

import ui_window
import keyboard_input
from ai_provider import ask_ai
from clipboard_utils import copy_to_clipboard
from config import Settings
from constants import (
    ASKALL_CODE_CONTEXT_LIMIT,
    SOLVEALL_FIELD_LIMIT,
    FIX_CONTEXT_LIMIT,
    POPUP_CLIPBOARD_PREVIEW_LENGTH,
    ERROR_MESSAGE_MAX_LENGTH,
)


def _code_above_tag(full_text: str, tag_marker: str) -> str:
    """Return the text preceding the given tag marker (e.g. '@@ASKALL')."""
    tag_pos = full_text.upper().find(tag_marker)
    return full_text[:tag_pos].strip() if tag_pos > 0 else ""


def _truncate(text: str, limit: int, from_end: bool = True) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:] if from_end else text[:limit]


def _deliver_ai_response(tag_type: str, response: str):
    """Send an AI response to the user via the configured response mode."""
    mode = Settings.get("response_mode", "auto")
    if mode == "type":
        keyboard_input.append_below_tag(response)
    else:
        ui_window.show(tag_type, response)


def _format_error(e: Exception) -> str:
    err_str = str(e)
    if "<html" in err_str.lower() or "<!doctype" in err_str.lower():
        return "ה-API חסום ע\"י פילטר רשת (NetFree?)\nנסי API אחר או בדקי הגדרות NetFree."
    if len(err_str) > ERROR_MESSAGE_MAX_LENGTH:
        return err_str[:ERROR_MESSAGE_MAX_LENGTH] + "..."
    return err_str


# ── Handlers ───────────────────────────────────────────────────────────────

def handle_screenshot(content: str, full_text: str):
    try:
        import pyautogui
    except ImportError:
        ui_window.show("ERROR", "pyautogui לא מותקן. הריצי: pip install pyautogui")
        return

    try:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        save_path = Path(__file__).parent / filename
        img = pyautogui.screenshot()
        img.save(str(save_path))
        ui_window.show("SCREENSHOT", f"✅ צילום מסך נשמר:\n\n{save_path}")
        print(f"[Agent] Screenshot saved: {save_path}")
    except Exception as e:
        ui_window.show("ERROR", f"שגיאה בצילום מסך:\n{e}")


def handle_askall(content: str, full_text: str):
    code = _code_above_tag(full_text, "@@ASKALL")
    if not code:
        ui_window.show("ERROR", "⚠️ אין קוד מעל התגית\nדוגמה:\n  [הקוד שלך]\n  @@ASKALL: למה הלולאה לא עוצרת?@@")
        return
    if not content:
        ui_window.show("ERROR", "⚠️ כתבי שאלה בתוך התגית:\n@@ASKALL: השאלה שלך@@")
        return

    code = _truncate(code, ASKALL_CODE_CONTEXT_LIMIT)

    try:
        print("[Agent] שולח ל-AI (ASKALL)...")
        response = ask_ai("ASKALL", f"Code:\n{code}\n\nQuestion: {content}")
        print(f"[Agent] תשובה התקבלה ({len(response)} תווים)")
        ui_window.show("ASK", response)
    except Exception as e:
        ui_window.show("ERROR", f"שגיאה:\n{_format_error(e)}")


def handle_solveall(content: str, full_text: str):
    clean = re.sub(r'@@SOLVEALL@@', '', full_text).strip()
    if not clean:
        ui_window.show("ERROR", "⚠️ השדה ריק — אין תרגיל לקרוא")
        return

    clean = _truncate(clean, SOLVEALL_FIELD_LIMIT, from_end=False)

    try:
        print(f"[Agent] שולח ל-AI (SOLVEALL, {len(clean)} תווים)...")
        response = ask_ai("SOLVEALL", clean)
        print(f"[Agent] תשובה התקבלה ({len(response)} תווים)")
        ui_window.show("SOLVE", response)
    except Exception as e:
        ui_window.show("ERROR", f"שגיאה:\n{_format_error(e)}")


def handle_copyall(content: str, full_text: str):
    clean = re.sub(r'@@COPYALL@@', '', full_text).strip()
    if copy_to_clipboard(clean):
        ui_window.show("COPY", f"✅ הועתק ל-Clipboard:\n\n{clean[:POPUP_CLIPBOARD_PREVIEW_LENGTH]}")
    else:
        ui_window.show("ERROR", "שגיאה בהעתקה ל-Clipboard")


def handle_copyabove(content: str, full_text: str):
    above = _code_above_tag(full_text, "@@COPYABOVE@@")
    if not above:
        ui_window.show("COPY", "⚠️ אין טקסט מעל התגית")
        return
    if copy_to_clipboard(above):
        ui_window.show("COPY", f"✅ הועתק ל-Clipboard:\n\n{above[:POPUP_CLIPBOARD_PREVIEW_LENGTH]}")
    else:
        ui_window.show("ERROR", "שגיאה בהעתקה ל-Clipboard")


def handle_copy(content: str, full_text: str):
    if not content:
        ui_window.show("COPY", "⚠️ כתבי את הטקסט בתוך התגית: @@COPY: הטקסט@@")
        return
    if copy_to_clipboard(content):
        ui_window.show("COPY", f"✅ הועתק ל-Clipboard:\n\n{content[:POPUP_CLIPBOARD_PREVIEW_LENGTH]}")
    else:
        ui_window.show("ERROR", "שגיאה בהעתקה ל-Clipboard")


def handle_fix(content: str, full_text: str):
    context = _code_above_tag(full_text, "@@FIX")
    if context:
        context = _truncate(context, FIX_CONTEXT_LIMIT)

    if not content and not context:
        ui_window.show("ERROR", "⚠️ כתבי הוראה בתוך התגית:\n@@FIX: תאר את הבעיה@@\n\nהקוד שרוצה לתקן צריך להיות מעל התגית.")
        return

    _call_ai_and_deliver("FIX", content, context)


def handle_ask(content: str, full_text: str):
    if not content:
        ui_window.show("ERROR", "⚠️ התגית ריקה. דוגמה:\n@@ASK: מה ההבדל בין list ל-tuple?@@")
        return
    _call_ai_and_deliver("ASK", content, "")


def handle_solve(content: str, full_text: str):
    if not content:
        ui_window.show("ERROR", "⚠️ התגית ריקה. דוגמה:\n@@SOLVE: כתוב פונקציה שמחשבת עצרת@@")
        return
    _call_ai_and_deliver("SOLVE", content, "")


def _call_ai_and_deliver(tag_type: str, content: str, context: str):
    print("[Agent] שולח ל-AI...")
    try:
        response = ask_ai(tag_type, content, context)
        print(f"[Agent] תשובה התקבלה ({len(response)} תווים)")
    except Exception as e:
        ui_window.show("ERROR", f"שגיאה בתקשורת עם AI:\n\n{_format_error(e)}")
        print(f"[Agent] AI error: {e}")
        return

    _deliver_ai_response(tag_type, response)


# ── Registry ───────────────────────────────────────────────────────────────

HANDLERS = {
    "SCREENSHOT": handle_screenshot,
    "ASKALL":     handle_askall,
    "SOLVEALL":   handle_solveall,
    "COPYALL":    handle_copyall,
    "COPYABOVE":  handle_copyabove,
    "COPY":       handle_copy,
    "FIX":        handle_fix,
    "ASK":        handle_ask,
    "SOLVE":      handle_solve,
}


def dispatch(tag_type: str, content: str, full_text: str):
    """Look up and run the handler for tag_type. Logs unknown tags."""
    handler = HANDLERS.get(tag_type)
    if handler is None:
        print(f"[Agent] Unknown tag type: {tag_type}")
        return
    handler(content, full_text)
