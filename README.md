<p align="center">
  <h1 align="center">⌨️ CodeMaker</h1>
  <p align="center">
    <strong>System-level input interceptor & AI code spoofing tool</strong>
  </p>
  <p align="center">
    A background service that monitors your keyboard for a trigger sequence,<br>
    screenshots the screen, sends it to an AI model, then <em>ghost-types</em> the<br>
    generated code — one character per keystroke — by intercepting your real input.
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS-green" alt="Linux | macOS">
    <img src="https://img.shields.io/badge/wayland-all%20compositors-purple" alt="Wayland">
    <img src="https://img.shields.io/badge/providers-7%20APIs%20+%20local-orange" alt="Multi-Provider">
    <img src="https://img.shields.io/badge/license-MIT-yellow" alt="MIT License">
  </p>
</p>

---

## Table of Contents

- [How It Works](#how-it-works)
- [Supported AI Providers](#supported-ai-providers)
- [Installation](#installation)
  - [macOS](#-macos)
  - [Arch Linux](#-arch-linux)
  - [Debian / Ubuntu](#-debian--ubuntu)
  - [Fedora / RHEL](#-fedora--rhel)
- [Finding Your Keyboard Device (Linux)](#finding-your-keyboard-device-linux)
- [Configuration](#configuration)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Autostart / Run on Boot](#autostart--run-on-boot)
- [Running Tests](#running-tests)

---

## How It Works

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   OBSERVER   │─────►│   CAPTURE    │─────►│  PROCESSING  │─────►│   PLAYBACK   │
│              │      │              │      │              │      │              │
│  Monitors    │      │  Screenshot  │      │  AI provider │      │  Ghost-types │
│  trigger     │      │  taken       │      │  returns     │      │  code from   │
│  sequence    │      │  silently    │      │  code        │      │  buffer      │
└──────────────┘      └──────────────┘      └──────────────┘      └──────┬───────┘
       ▲                                                                  │
       └─────────────────── buffer exhausted ─────────────────────────────┘
```

1. **OBSERVER** — The service silently monitors your keyboard for the trigger sequence (default: `t a a r u n`)
2. **CAPTURE** — On trigger, it silently screenshots your screen
3. **PROCESSING** — The screenshot is sent to the configured AI provider (with automatic fallback to the next provider on failure)
4. **PLAYBACK** — Every key you press now outputs the next character from the AI-generated code. Indentation is stripped so your editor's auto-indent handles formatting. Backspace moves backward through the code buffer.

### Backspace Behavior

| Scenario | What Happens |
|----------|-------------|
| Normal typing | Next character from AI code is injected |
| Backspace (buffer has content) | Moves cursor back in code buffer, deletes injected char |
| Backspace (at position 0) | Blocked — stays at start |
| Any key after backspacing to 0 | Resumes typing from the beginning of the buffer |

---

## Supported AI Providers

CodeMaker supports **up to 5 API providers + 1 local model**, tried in configurable priority order. If one fails (rate limit, error), it automatically falls back to the next.

| Provider | Free Tier | Vision | Get API Key |
|----------|-----------|--------|-------------|
| **Google Gemini** | 1,500 req/day (Flash) | ✅ | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| **Groq** | 14,400 req/day | ✅ | [console.groq.com](https://console.groq.com) |
| **OpenRouter** | $1 free credit | ✅ | [openrouter.ai](https://openrouter.ai) |
| **Mistral** | Free tier | ✅ | [console.mistral.ai](https://console.mistral.ai) |
| **Together AI** | $1 free credit | ✅ | [together.ai](https://www.together.ai) |
| **GitHub Models** | Free with GitHub | ✅ | [github.com/marketplace/models](https://github.com/marketplace/models) |
| **Any OpenAI-compatible** | varies | ✅ | Custom `BASE_URL` |
| **Ollama (local)** | ∞ unlimited | ✅ | [ollama.com](https://ollama.com) — auto-downloads models |

### Recommended Setup

Set Gemini as primary (smartest), OpenRouter as free fallback, Groq as last-resort, and optionally a local two-stage pipeline for offline use:

```env
PROVIDER_PRIORITY=2,3,1,local

# Provider 1: Groq (fast but less capable)
PROVIDER_1_TYPE=groq
PROVIDER_1_KEY=your_groq_key
PROVIDER_1_MODEL=meta-llama/llama-4-scout-17b-16e-instruct

# Provider 2: Gemini (best code quality — tried first)
PROVIDER_2_TYPE=gemini
PROVIDER_2_KEY=your_gemini_key
PROVIDER_2_MODEL=gemini-2.5-flash

# Provider 3: OpenRouter (free vision fallback)
PROVIDER_3_TYPE=openrouter
PROVIDER_3_KEY=your_openrouter_key
PROVIDER_3_MODEL=openrouter/free

# Local: two-stage pipeline (vision extracts question, code model solves it)
LOCAL_VISION_MODEL=minicpm-v
LOCAL_CODE_MODEL=qwen2.5-coder:7b
```

---

## Installation

### Prerequisites (All Platforms)

- **Python 3.11** or newer
- At least one AI provider API key (see [Supported AI Providers](#supported-ai-providers))

---

### 🍎 macOS

<details open>
<summary><strong>Click to expand</strong></summary>

#### 1. Install Python (if not already installed)

```bash
# Using Homebrew (recommended)
brew install python@3.11

# Or download from https://www.python.org/downloads/
```

#### 2. Clone and set up the project

```bash
git clone <your-repo-url> CodeMaker
cd CodeMaker

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 3. Grant permissions

CodeMaker needs these macOS permissions to function:

**Accessibility** (for keyboard interception):
1. Open **System Settings → Privacy & Security → Accessibility**
2. Click the **+** button and add your terminal app (Terminal.app, iTerm2, etc.)
3. Ensure the toggle is **enabled**

**Screen Recording** (for screenshots):
1. Open **System Settings → Privacy & Security → Screen Recording**
2. Add your terminal app and enable it

**Full Disk Access** (required for autostart / if project is in `~/Desktop` or `~/Documents`):
1. Open **System Settings → Privacy & Security → Full Disk Access**
2. Click **+**, press **Cmd+Shift+G**, type `/bin/bash`, and add it
3. Also add your terminal app if not already listed

> ⚠️ You may need to **restart your terminal** after granting permissions.

#### 4. Configure

```bash
cp .env.example .env
nano .env
```

Set at minimum:
- `PROVIDER_1_KEY` — your Gemini API key (or whichever provider you're using)

> No `KEYBOARD_DEVICE` needed on macOS — Quartz handles keyboard interception automatically.

#### 5. Run

```bash
python -m codemaker
```

> **No `sudo` required** on macOS — keyboard access is granted through Accessibility permissions, not root.

#### 6. Optional: Install Ollama for local models

```bash
brew install ollama
ollama serve  # Start the Ollama server
```

</details>

---

### 🐧 Arch Linux

<details>
<summary><strong>Click to expand</strong></summary>

#### 1. Install system dependencies

```bash
sudo pacman -S python python-pip git

# Screenshot tool (install at least one)
sudo pacman -S grim          # Hyprland / Sway / wlroots
sudo pacman -S spectacle     # KDE Plasma
sudo pacman -S gnome-screenshot  # GNOME

sudo modprobe uinput

# Optional: for local AI model support
sudo pacman -S ollama
```

#### 2. Set up input permissions

```bash
sudo usermod -aG input $USER
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | \
  sudo tee /etc/udev/rules.d/99-uinput.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
# ⚠️ LOG OUT AND BACK IN for group changes to take effect
```

#### 3. Clone and set up the project

```bash
git clone <your-repo-url> CodeMaker
cd CodeMaker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 4. Find your keyboard device

```bash
sudo .venv/bin/python diagnose_keyboard.py
```

Press a few keys and set the suggested path in `.env`:

```env
KEYBOARD_DEVICE=/dev/input/event10
```

#### 5. Configure

```bash
cp .env.example .env
nano .env
# Set PROVIDER_1_KEY and KEYBOARD_DEVICE
```

#### 6. Run

```bash
sudo .venv/bin/python -m codemaker
```

</details>

---

### 🐧 Debian / Ubuntu

<details>
<summary><strong>Click to expand</strong></summary>

#### 1. Install system dependencies

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git
sudo apt install python3-dev gcc  # Build deps for python-evdev

# Screenshot tool
sudo apt install grim              # wlroots compositors
sudo apt install kde-spectacle     # KDE Plasma
sudo apt install gnome-screenshot  # GNOME

sudo modprobe uinput

# Optional: for local AI model support
curl -fsSL https://ollama.com/install.sh | sh
```

#### 2. Set up input permissions

```bash
sudo usermod -aG input $USER
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | \
  sudo tee /etc/udev/rules.d/99-uinput.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
# ⚠️ LOG OUT AND BACK IN
```

#### 3. Clone and set up

```bash
git clone <your-repo-url> CodeMaker
cd CodeMaker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 4. Find keyboard device, configure, and run

```bash
sudo .venv/bin/python3 diagnose_keyboard.py
cp .env.example .env
nano .env   # Set PROVIDER_1_KEY and KEYBOARD_DEVICE
sudo .venv/bin/python3 -m codemaker
```

</details>

---

### 🐧 Fedora / RHEL

<details>
<summary><strong>Click to expand</strong></summary>

#### 1. Install system dependencies

```bash
sudo dnf install python3 python3-pip python3-devel gcc git
sudo dnf install grim          # wlroots compositors
sudo dnf install spectacle     # KDE Plasma
sudo dnf install gnome-screenshot  # GNOME
sudo modprobe uinput

# Optional: for local AI model support
curl -fsSL https://ollama.com/install.sh | sh
```

#### 2. Set up input permissions

```bash
sudo usermod -aG input $USER
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | \
  sudo tee /etc/udev/rules.d/99-uinput.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
# ⚠️ LOG OUT AND BACK IN
```

#### 3. Clone, configure, and run

```bash
git clone <your-repo-url> CodeMaker
cd CodeMaker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
sudo .venv/bin/python3 diagnose_keyboard.py
cp .env.example .env
nano .env   # Set PROVIDER_1_KEY and KEYBOARD_DEVICE
sudo .venv/bin/python3 -m codemaker
```

</details>

---

## Finding Your Keyboard Device (Linux)

Many laptops split keyboard input across multiple `/dev/input/event*` devices. Use the included diagnostic tool:

```bash
sudo .venv/bin/python diagnose_keyboard.py
```

> **macOS:** This step is not needed — Quartz CGEventTap handles all keyboard input automatically.

**Output:**

```
══════════════════════════════════════════════════════════════════
  CodeMaker Keyboard Diagnostic
  Press keys on your keyboard. Watch which device receives them.
══════════════════════════════════════════════════════════════════

  Monitoring: /dev/input/event10      ITE Tech. Inc. ITE Device(8176)
──────────────────────────────────────────────────────────────────
  ⌨️  /dev/input/event10      │ ITE Tech. Inc. ITE Device(8176)      │ KEY_A
──────────────────────────────────────────────────────────────────
  ✅ Set this in your .env:
     KEYBOARD_DEVICE=/dev/input/event10
```

---

## Configuration

All settings live in the `.env` file. Copy `.env.example` to `.env` and edit:

### Core Settings

| Variable | Default | Description |
|:---------|:--------|:------------|
| `SYSTEM_PROMPT` | `Solve this in c and have no comments at all.` | Instruction sent to the AI with the screenshot |
| `TRIGGER_SEQUENCE` | `t,a,a,r,u,n` | Comma-separated key names that activate capture |
| `SCREENSHOT_TOOL` | `auto` | `grim`, `gnome-screenshot`, `spectacle`, `screencapture`, `pillow`, or `auto` |
| `KILL_COMBO` | `ctrl+shift+escape` | Emergency kill combo to exit instantly |
| `RESET_COMBO` | `ctrl+shift+r` | Jump back to observer mode (cancels playback) |
| `KEYBOARD_DEVICE` | *(auto-detect)* | Linux only: explicit device path like `/dev/input/event10` |

### AI Provider Settings

| Variable | Description |
|:---------|:------------|
| `PROVIDER_PRIORITY` | Comma-separated priority order: `1,2,3,4,5,local` |
| `PROVIDER_N_TYPE` | Provider type: `gemini`, `groq`, `openrouter`, `mistral`, `together`, `github`, `openai` |
| `PROVIDER_N_KEY` | API key for the provider |
| `PROVIDER_N_MODEL` | Model name/ID |
| `PROVIDER_N_BASE_URL` | Custom base URL (for `openai` type or overrides) |
| `LOCAL_MODEL` | Single Ollama model for vision+code (simple mode) |
| `LOCAL_VISION_MODEL` | Vision model for question extraction (pipeline mode) |
| `LOCAL_CODE_MODEL` | Code model for solution generation (pipeline mode) |
| `LOCAL_VISION_PROMPT` | Custom prompt for the vision extraction step |
| `OLLAMA_URL` | Ollama server URL (default: `http://localhost:11434`) |

### Available Key Names

Letters: `a`–`z` · Digits: `0`–`9` · Modifiers: `shift`, `ctrl`, `alt`, `meta`
Special: `tab`, `backspace`, `enter`, `space`, `escape`, `delete`, `capslock`
Navigation: `up`, `down`, `left`, `right`, `home`, `end`, `pageup`, `pagedown`
Function keys: `f1`–`f12`

---

## Usage

### Starting the Service

```bash
# macOS (no sudo needed)
python -m codemaker

# Linux
sudo .venv/bin/python -m codemaker
```

You'll see a startup banner showing the active provider chain:

```
╔══════════════════════════════════════════╗
║         CodeMaker v0.1.0 Active          ║
║                                          ║
║  Trigger: t,a,a,r,u,n                    ║
║  Kill:    ctrl+escape+shift              ║
║                                          ║
║  Waiting for trigger sequence...          ║
╚══════════════════════════════════════════╝
  Providers: provider_1(gemini:gemini-2.0-fla) → provider_2(groq:llama-4-scout-1)
```

### Workflow

1. Open any text editor, IDE, or code input field
2. Type the trigger sequence: **t a a r u n**
3. Wait 2–5 seconds for the screenshot to be captured and processed
4. Start typing anything — every key you press outputs the next character of the AI-generated code
5. Use **Backspace** to move backward in the code buffer
6. When the entire code buffer has been typed out, normal keyboard operation resumes automatically

> **Note:** Indentation is automatically stripped from the AI output so your editor's auto-indent handles formatting correctly.

### Emergency Exit

Press **Ctrl+Shift+Escape** (or your configured `KILL_COMBO`) at any time to instantly kill the service and restore normal keyboard operation.

---

## Troubleshooting

### macOS

<details>
<summary><strong>CGEventTap failed: "Failed to create event tap"</strong></summary>

Your terminal app doesn't have Accessibility permissions.

1. Open **System Settings → Privacy & Security → Accessibility**
2. Add your terminal (Terminal.app, iTerm2, Alacritty, etc.)
3. Make sure the toggle is **on**
4. **Restart your terminal** after granting permission

</details>

<details>
<summary><strong>Screenshots are blank or show only wallpaper</strong></summary>

Screen Recording permission is not granted.

1. Open **System Settings → Privacy & Security → Screen Recording**
2. Add your terminal app
3. Restart the terminal

</details>

<details>
<summary><strong>Screenshot fails: "No such file or directory: screencapture"</strong></summary>

This happens when running via launchd autostart. macOS's `screencapture` lives at `/usr/sbin/screencapture`, but launchd provides a minimal `PATH` that excludes `/usr/sbin`.

**Fix:** This is handled automatically in the latest version. If you see this error, update your code and re-run `./setup_autostart_macos.sh`.

</details>

<details>
<summary><strong>Autostart fails: "Operation not permitted" / sandbox errors</strong></summary>

macOS blocks launchd processes from accessing `~/Desktop`, `~/Documents`, and `~/Downloads` (sandbox-protected locations).

1. Grant **Full Disk Access** to `/bin/bash`:
   - **System Settings → Privacy & Security → Full Disk Access**
   - Click **+**, press **Cmd+Shift+G**, type `/bin/bash`, add it
2. Re-run `./setup_autostart_macos.sh` to regenerate the plist
3. Check logs at `~/Library/Logs/CodeMaker/codemaker.log`

Alternatively, move the project to a non-protected location like `~/Projects/CodeMaker`.

</details>

<details>
<summary><strong>Autostart crashes repeatedly (Gatekeeper blocks unsigned Python)</strong></summary>

macOS Gatekeeper blocks unsigned executables (like `.venv/bin/python`) from being launched directly by launchd.

**Fix:** The `setup_autostart_macos.sh` script works around this by using `/bin/bash` (Apple-signed) as the launcher. Make sure you're using the latest version of the script.

</details>

<details>
<summary><strong>Keys are not being intercepted</strong></summary>

1. Verify Accessibility permission is granted and enabled
2. Try closing and reopening your terminal
3. Check if another app has an active CGEventTap that might conflict

</details>

### Linux

<details>
<summary><strong>Permission denied: /dev/input/event*</strong></summary>

```bash
groups  # Check if 'input' is listed
sudo usermod -aG input $USER
# LOG OUT and back in, or reboot
```

Quick fix: `sudo .venv/bin/python -m codemaker`

</details>

<details>
<summary><strong>Permission denied: /dev/uinput</strong></summary>

```bash
echo 'KERNEL=="uinput", GROUP="input", MODE="0660"' | \
  sudo tee /etc/udev/rules.d/99-uinput.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

</details>

<details>
<summary><strong>Wrong keyboard detected / no keys received</strong></summary>

Run `sudo .venv/bin/python diagnose_keyboard.py`, press keys, and set the correct device in `.env`:

```env
KEYBOARD_DEVICE=/dev/input/event10
```

</details>

<details>
<summary><strong>Device busy (EBUSY)</strong></summary>

Another program (keyd, kmonad, etc.) has an exclusive grab. Stop it or use its virtual output device:

```env
KEYBOARD_DEVICE=/dev/input/event26   # keyd virtual keyboard
```

</details>

<details>
<summary><strong>Screenshot fails: "All screenshot methods failed"</strong></summary>

Install a screenshot tool for your compositor:
```bash
sudo pacman -S grim      # Arch + wlroots
sudo apt install grim     # Debian + wlroots
```

Or force: `SCREENSHOT_TOOL=grim`

</details>

<details>
<summary><strong>evdev build fails: "Python.h not found"</strong></summary>

```bash
sudo apt install python3-dev    # Debian/Ubuntu
sudo dnf install python3-devel  # Fedora
```

</details>

### API Issues

<details>
<summary><strong>429 RESOURCE_EXHAUSTED — quota exceeded</strong></summary>

1. **Wait** for daily reset
2. **Add more providers** as fallbacks
3. **Use a local model** via Ollama

</details>

<details>
<summary><strong>Model not found (404)</strong></summary>

Check the exact model ID:
```env
# ❌ Wrong
PROVIDER_2_MODEL=llama-4-scout-17b-16e-instruct
# ✅ Correct
PROVIDER_2_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
```

</details>

---

## Architecture

```
CodeMaker/
├── .env.example              # Configuration template (all providers)
├── .env                      # Your config (gitignored)
├── requirements.txt          # Python dependencies
├── diagnose_keyboard.py      # Keyboard device finder tool (Linux)
├── setup_autostart.sh        # Linux systemd autostart setup
├── setup_autostart_macos.sh  # macOS launchd autostart setup
├── README.md                 # This file
├── codemaker/
│   ├── __init__.py           # Package metadata
│   ├── __main__.py           # python -m codemaker entry
│   ├── main.py               # Orchestrator — wires everything
│   ├── config.py             # .env → Config dataclass + provider parsing
│   ├── state.py              # OBSERVER/CAPTURE/PLAYBACK state machine
│   ├── trigger.py            # Sliding-window trigger detector
│   ├── playback.py           # Code buffer + backspace logic
│   ├── capture.py            # Universal screenshot (auto env recovery)
│   ├── providers.py          # Multi-provider AI backend + fallback chain
│   ├── gemini.py             # Legacy Gemini-only module (deprecated)
│   ├── utils.py              # Logging, code fence & indentation stripping
│   └── platform/
│       ├── __init__.py
│       ├── base.py           # Abstract PlatformHook interface
│       ├── linux.py          # evdev grab + uinput (all compositors)
│       └── macos.py          # Quartz CGEventTap + CGEventPost
└── tests/
    ├── test_trigger.py       # Trigger detector tests
    ├── test_playback.py      # Playback buffer tests
    ├── test_state.py         # State machine tests
    └── test_utils.py         # Utility function tests
```

### Platform Support Matrix

| Feature | Linux (Wayland) | Linux (X11) | macOS |
|:--------|:---------------|:------------|:------|
| Keyboard interception | evdev grab | evdev grab | Quartz CGEventTap |
| Key injection | uinput virtual keyboard | uinput virtual keyboard | CGEventPost |
| Screenshot | grim / spectacle / gnome-screenshot | Pillow ImageGrab | screencapture / Pillow |
| Required privileges | `input` group or root | `input` group or root | Accessibility permission |

---

## Running Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

Expected output:

```
========================= 34 passed in 0.03s =========================
```

---

## Autostart / Run on Boot

### 🍎 macOS (launchd)

<details open>
<summary><strong>Click to expand</strong></summary>

#### Automated Setup (recommended)

```bash
./setup_autostart_macos.sh
```

This script:
- Creates a launcher wrapper at `~/Library/Application Support/CodeMaker/launcher.sh`
- Creates a LaunchAgent plist at `~/Library/LaunchAgents/com.codemaker.agent.plist`
- Uses `/bin/bash` (Apple-signed) to bypass Gatekeeper restrictions on unsigned Python binaries
- Places the launcher in `~/Library/Application Support/` to avoid macOS sandbox restrictions on `~/Desktop`
- Logs are written to `~/Library/Logs/CodeMaker/codemaker.log`

#### Required permissions for autostart

| Permission | Why | How |
|:-----------|:----|:----|
| **Accessibility** | Keyboard interception | System Settings → Privacy & Security → Accessibility → add terminal |
| **Screen Recording** | Screenshots | System Settings → Privacy & Security → Screen Recording → add terminal |
| **Full Disk Access** | Access project files in `~/Desktop` | System Settings → Privacy & Security → Full Disk Access → add `/bin/bash` (Cmd+Shift+G → `/bin/bash`) |

#### Manage

```bash
# View live logs
tail -f ~/Library/Logs/CodeMaker/codemaker.log

# Stop
launchctl unload ~/Library/LaunchAgents/com.codemaker.agent.plist

# Start
launchctl load ~/Library/LaunchAgents/com.codemaker.agent.plist

# Remove completely
launchctl unload ~/Library/LaunchAgents/com.codemaker.agent.plist
rm ~/Library/LaunchAgents/com.codemaker.agent.plist
rm ~/Library/Application\ Support/CodeMaker/launcher.sh
```

</details>

### 🐧 Linux (systemd — all distros)

<details>
<summary><strong>Click to expand</strong></summary>

#### Automated Setup

```bash
sudo ./setup_autostart.sh
```

#### Manage

```bash
sudo systemctl status codemaker
sudo systemctl stop codemaker
sudo systemctl restart codemaker
sudo systemctl disable codemaker
```

</details>

---

## License

MIT
