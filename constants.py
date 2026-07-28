"""
Central location for all configuration constants and magic numbers.
"""

# ── Debounce timing (seconds) ─────────────────────────────────────────────────
DEBOUNCE_WITH_CONTENT = 1.5   # Tags with content (e.g. @@ASK: ...@@) — wait for typing to finish
DEBOUNCE_BARE = 0.5           # Bare tags (e.g. @@SCREENSHOT@@) — fire faster
MAIN_LOOP_POLL_INTERVAL = 0.3 # How often the main loop reads the focused window

# ── Text length limits (characters) ───────────────────────────────────────────
TEXT_PREVIEW_LENGTH = 80        # Console log preview length
POPUP_CLIPBOARD_PREVIEW_LENGTH = 300  # Popup preview when copying to clipboard
ASKALL_CODE_CONTEXT_LIMIT = 2000      # Max code length sent for @@ASKALL@@
SOLVEALL_FIELD_LIMIT = 3000           # Max field length sent for @@SOLVEALL@@
FIX_CONTEXT_LIMIT = 1500              # Max code length sent for @@FIX@@

# ── UIAutomation tree search ──────────────────────────────────────────────────
MAX_TREE_SEARCH_DEPTH = 7    # Max depth when searching the full window tree
MAX_PARENT_WALK_UP = 5       # Max levels to walk up from focused control

# ── Popup window ───────────────────────────────────────────────────────────────
POPUP_GEOMETRY = "480x320+40+40"  # width x height + x_offset + y_offset
TYPE_BUTTON_COUNTDOWN_SECONDS = 3
FOCUS_REGAIN_DELAY = 0.4          # Wait after closing popup for editor to regain focus

# ── Keyboard simulation ───────────────────────────────────────────────────────
KEY_PRESS_DELAY = 0.15
KEY_PRESS_DELAY_SHORT = 0.1

# ── AI request defaults ───────────────────────────────────────────────────────
RETRY_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 15

# ── Error message truncation ──────────────────────────────────────────────────
ERROR_MESSAGE_MAX_LENGTH = 300
