# SEB AI Agent

An AI assistant that runs silently in the background and helps students communicate with an AI model while working inside **Safe Exam Browser (SEB)** — which normally blocks copy/paste, screenshots, and external tools.

## How It Works

The agent reads text from the active window using the **Windows UIAutomation API** (OS-level, not blocked by SEB). Students write special tags inside their code editor, and the agent detects them, calls the AI, and displays the response in a floating popup window.

Student types @@ASK: why does my loop run forever?@@
↓
Agent reads via UIAutomation (no screenshot, no OCR)
↓
Gemini AI responds
↓
Floating popup appears with the answer


## Features

- Reads text directly from the browser editor — no screenshots, no OCR
- Detects tags only when complete (debounce), avoiding API calls mid-typing
- Floating always-on-top response window with "Type into editor" button
- OS-level screenshot capture (bypasses SEB's screenshot block)
- Clipboard operations that bypass SEB's copy restriction
- Free AI via Google Gemini 2.0 Flash Lite
- Auto-retry on rate limit errors (429)

## Supported Tags

| Tag | Description |
|-----|-------------|
| `@@ASK: question@@` | Short explanation / hint (no full code) |
| `@@ASKALL: question@@` | Question about the code written above the tag |
| `@@SOLVE: task@@` | Generate complete code |
| `@@SOLVEALL@@` | Solve the full exercise from everything in the editor |
| `@@FIX: instruction@@` | Fix the code written above the tag |
| `@@COPY: text@@` | Copy specific text to clipboard |
| `@@COPYABOVE@@` | Copy all text above the tag to clipboard |
| `@@COPYALL@@` | Copy entire field content to clipboard |
| `@@SCREENSHOT@@` | Take an OS-level screenshot (saved as PNG) |

## Requirements

- Windows 10/11
- Python 3.10+
- Google Gemini API key (free) — get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

## Setup

1. Clone the repository
2. Run `install.bat` to install dependencies
3. Open `settings.json` and add your Gemini API key:
```json
{
  "api_key": "YOUR_GEMINI_API_KEY",
  "model": "gemini-2.0-flash-lite"
}
Run start.bat before opening SEB
Usage
Write any tag inside your code editor (tested with Ultracode / Monaco editor), wait 2 seconds, and the response appears in a floating window.

Example:
int findMax(int arr[], int n) {
    int max = 0;
    for(int i = 0; i < n; i++)
        if(arr[i] > max) max = arr[i];
    return max;
}

@@ASKALL: why doesn't this work when all numbers are negative?@@
Note: Do not open the TAGS_GUIDE.txt file while the agent is running — it contains @@ patterns that may confuse the detector.

Architecture
main.py          — Main loop, debounce, tag dispatch
reader.py        — UIAutomation text extraction (fast, no OCR)
detector.py      — Tag parsing, hash-based deduplication
claude_client.py — Gemini API calls, retry logic, token efficiency
popup_window.py  — Floating tkinter response window
typer.py         — Keyboard simulation for typing into editor
config.py        — Settings loader
Platform
Developed and tested on:

Safe Exam Browser (SEB)
Ultracode — Monaco-based online judge
Windows 11
