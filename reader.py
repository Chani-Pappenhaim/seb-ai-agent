"""
Read text from the active window via Windows UIAutomation.
Optimization: first do a cheap focused-control check.
Only search the full tree if @@ is found.
"""

_IGNORE_TITLES = ("seb agent", "cmd.exe", "command prompt", "powershell",
                  "windows terminal", "visual studio code", "notepad++",
                  "notepad", "wordpad", ".txt", ".py", "tags_guide", "project_summary")


def _should_ignore(title: str) -> bool:
    t = (title or "").lower()
    return any(x in t for x in _IGNORE_TITLES)


def _extract(ctrl) -> str | None:
    for getter in [
        lambda c: c.GetValuePattern().Value,
        lambda c: c.GetTextPattern().DocumentRange.GetText(-1),
        lambda c: c.Name,
    ]:
        try:
            v = getter(ctrl)
            if v and v.strip():
                return v
        except Exception:
            pass
    return None


def _search_tree(ctrl, depth: int) -> str | None:
    if depth > 7:
        return None
    try:
        v = _extract(ctrl)
        if v and "@@" in v:
            return v
        for child in ctrl.GetChildren():
            result = _search_tree(child, depth + 1)
            if result:
                return result
    except Exception:
        pass
    return None


def read_focused_text() -> str | None:
    """
    1. Quick check: read focused control only.
    2. If @@ found → return it.
    3. If not → search full foreground window tree.
    4. Ignore our own terminal window.
    """
    try:
        import uiautomation as auto

        fg = auto.GetForegroundControl()
        if fg and _should_ignore(fg.Name):
            return None

        # ── Step 1: cheap focused-control read ───────────────────────────────
        ctrl = auto.GetFocusedControl()
        if ctrl:
            v = _extract(ctrl)
            if v and "@@" in v:
                return v

            # Walk up parents (Monaco editor wraps text in divs)
            parent = ctrl.GetParentControl()
            for _ in range(5):
                if parent is None:
                    break
                v = _extract(parent)
                if v and "@@" in v:
                    return v
                try:
                    parent = parent.GetParentControl()
                except Exception:
                    break

        # ── Step 2: full tree search only if quick check found nothing ───────
        if fg:
            return _search_tree(fg, depth=0)

    except Exception as e:
        if "Catastrophic" not in str(e):
            print(f"[reader] error: {e}")

    return None
