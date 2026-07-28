# SEB Bot — AI Assistant for Safe Exam Browser

A background agent that helps students work efficiently within Safe Exam Browser (SEB) environments by providing AI-powered code assistance, clipboard management, and other productivity features.

## Problem

Safe Exam Browser blocks essential features:
- Copy/Paste (Ctrl+C, Ctrl+V)
- Screenshots (PrintScreen)
- External applications

This makes working on coding tasks unnecessarily difficult.

## Solution

SEB Bot runs as a background Windows process and uses **Windows UIAutomation** (which SEB cannot block) to:
- Read your code directly from the editor
- Detect special tags (`@@ASK:`, `@@SOLVE:`, etc.)
- Send requests to an AI provider (Gemini, Groq, or Mistral)
- Return answers in a floating window
- Handle clipboard operations directly from the OS level

## Features

| Tag | Purpose | Example |
|-----|---------|---------|
| `@@ASK: question@@` | Get a short explanation | `@@ASK: How do I reverse a list?@@` |
| `@@SOLVE: task@@` | Generate complete code | `@@SOLVE: Write a function that calculates factorial@@` |
| `@@FIX: instruction@@` | Fix your code | `@@FIX: Make this more efficient@@` |
| `@@COPY: text@@` | Copy specific text | `@@COPY: my-password-123@@` |
| `@@COPYABOVE@@` | Copy everything above the tag | — |
| `@@COPYALL@@` | Copy entire field content | — |
| `@@SCREENSHOT@@` | Take a screenshot | — |
| `@@ASKALL: question@@` | Ask about code above | `@@ASKALL: Why isn't this working?@@` |
| `@@SOLVEALL@@` | Solve entire exercise | — |

## Technologies Used

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | **Python 3.8+** | Core implementation |
| UI reading | **Windows UIAutomation** (`uiautomation`) | Reads editor text at the OS accessibility level — invisible to SEB |
| AI providers | **Google Gemini**, **Groq**, **Mistral AI** | Pluggable LLM backends, auto-selected by API key format |
| Response UI | **tkinter** | Always-on-top floating response window |
| Clipboard | **pyperclip** | OS-level clipboard access (bypasses SEB's copy/paste block) |
| Keyboard simulation | **keyboard** / **pyautogui** | Types AI responses directly into the editor |
| Screenshots | **Pillow** + **pyautogui** | OS-level screen capture |
| HTTP (Mistral) | **requests** | Direct REST calls to the Mistral API |
| Config | **JSON** | Human-editable settings file, validated at startup |

## Installation

### Prerequisites
- Python 3.8+
- Windows (uses UIAutomation API)
- An API key from one of:
  - [Google Gemini](https://aistudio.google.com/apikey) — free tier available
  - [Groq](https://console.groq.com/keys) — free tier available
  - [Mistral AI](https://console.mistral.ai/api-keys)

### Setup

1. **Clone or download** this repository
2. **Run installation** (one time):
   ```bash
   scripts\install.bat
   ```
3. **Configure API key**:
   - Copy `settings.example.json` to `settings.json`
   - Add your API key to `settings.json` — the provider is auto-detected from the key format
4. **Start the bot** (before opening SEB):
   ```bash
   scripts\start.bat
   ```

## Usage

1. Open Safe Exam Browser
2. In your code editor, type a tag: `@@ASK: Your question here@@`
3. Wait 1-2 seconds for the bot to detect the tag
4. A window appears with the AI's response
5. Use the "Copy" or "Type in editor" buttons

## Configuration

Edit `settings.json`:
```json
{
  "api_key": "your-key-here",
  "provider": "",
  "model": "gemini-2.0-flash-lite",
  "response_mode": "auto",
  "poll_interval": 1.0,
  "type_speed": 0.015,
  "language": "he"
}
```

- **provider**: `""` (auto-detect from key format), `"gemini"`, `"groq"`, or `"mistral"`
- **response_mode**: `"auto"` (pop-up window) or `"type"` (direct typing)
- **type_speed**: Delay between characters when typing (in seconds)
- **language**: `"he"` (Hebrew) or `"en"` (English)

Settings are validated at startup — invalid values (e.g. an unknown `response_mode`) raise a clear error instead of failing silently.

## How It Works

```
1. You type @@TAG: content@@
      ↓
2. Main loop reads focused window (0.3s intervals)
      ↓
3. Detector regex finds tags + hash-based deduplication
      ↓
4. Debounce waits 1.5s for user to finish typing
      ↓
5. AI request sent to the configured provider
      ↓
6. Response appears in floating window
      ↓
7. You can copy or type directly into editor
```

**Key Technical Points:**
- Uses **Windows UIAutomation** (accessibility API) — SEB cannot block it
- **No screenshots/OCR** for reading — direct text extraction from controls
- **No clipboard spoofing** — operates at OS level
- **Debouncing** — prevents sending incomplete tags to AI
- **Hash-based deduplication** — avoids duplicate requests
- **Provider-agnostic AI layer** — swap Gemini/Groq/Mistral without touching the rest of the code

## Architecture

```
main.py             — Main loop: debouncing, tag detection, dispatch
config.py           — Settings loading + validation
constants.py        — All tunable values (timeouts, limits, sizes)
reader.py           — Text reading via UIAutomation
detector.py         — Tag detection & hash-based deduplication
ai_provider.py       — AI provider abstraction (Gemini / Groq / Mistral)
tag_handlers.py      — One handler function per tag type
ui_window.py         — Floating response window (tkinter)
keyboard_input.py    — Automated typing into the editor
clipboard_utils.py   — Shared clipboard read/write logic

settings.json         — Local config with API key (gitignored)
settings.example.json — Template to copy

scripts/
├── install.bat      — One-time dependency installation
└── start.bat        — Run before each exam session

docs/
├── HOW_IT_WORKS.html   — Detailed technical walkthrough
├── TAGS_GUIDE.txt      — Tag reference
└── PROJECT_SUMMARY.txt — Project overview
```

Each module has a single responsibility: `reader.py` only reads text, `detector.py` only recognizes tags, `ai_provider.py` only talks to LLMs, `tag_handlers.py` only decides what each tag does, and `main.py` just wires them together in a loop. No file imports something that (directly or indirectly) imports it back.

## Security & Privacy

⚠️ **Important:**
- `settings.json` is **NOT** pushed to GitHub (protected by `.gitignore`)
- Never share your API key
- Never commit `settings.json` to version control
- API calls go to your chosen provider (check their respective privacy policies)

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Missing API key" | `settings.json` not configured | Get a free key from Gemini or Groq |
| Missing dependency error at startup | A required package isn't installed | Run `scripts\install.bat` again |
| Tag not detected | Missing closing `@@` | Always use `@@TAG: content@@` format |
| No response | Waited less than 1.5 seconds | Wait for debounce timeout |
| 429 Too Many Requests | Exceeded rate limit | Bot retries automatically (15s wait, up to 3 times) |
| Window blocked | SEB in full kiosk mode | Change `response_mode` to `"type"` |

## Development

To contribute or modify:
1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Modify the relevant module (see Architecture above)
4. Test with a running SEB session
5. Submit a pull request

To add a new tag: write a handler function in `tag_handlers.py` and register it in the `HANDLERS` dict — no changes needed elsewhere.

To add a new AI provider: add a class in `ai_provider.py` implementing `AIProvider.generate()`, and register it in `get_provider()`.

## License

MIT License — See [LICENSE](LICENSE) file

## Disclaimer

This tool is designed for **educational purposes** with restricted browser environments. Users are responsible for ensuring compliance with their institution's policies and SEB usage agreements.

---

**Made with ❤️ for students tired of browser restrictions.**

Questions? Open an issue on GitHub.
