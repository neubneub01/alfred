# Alfred Power Setup

Complete Alfred 5 workflow suite — a full Raycast replacement for macOS productivity.

## Workflows

| Workflow | Keyword | Description |
|----------|---------|-------------|
| **Homelab SSH** | `ssh` | Quick SSH to homelab nodes (neubneub, neub, neub3) |
| **Dev Tools** | `uuid`, `base64e`, `base64d`, `epoch`, `hash`, `json`, `urlencode`, `urldecode`, `lorem`, `hex` | Developer utilities |
| **System Commands** | `flushdns`, `emptytrash`, `darkmode`, `showfiles`, `lock`, `sleep`, `wifi`, etc. | Quick system actions |
| **Process Killer** | `kill` | Find and kill running processes |
| **Project Launcher** | `code` | Open code projects in VS Code |
| **IP Info** | `ip` | Show local/public IP, gateway, DNS, Wi-Fi |
| **AI Quick Ask** | `ai` | Ask Claude AI quick questions |
| **Quick Search** | `g`, `gh`, `so`, `npm`, `yt`, `reddit`, `mdn`, `wiki`, `maps`, etc. | Multi-engine web search |

## Installation

```bash
git clone https://github.com/Neubneub/alfred.git
cd alfred
./install.sh
```

Then restart Alfred to load the workflows.

## Setup

### AI Quick Ask
1. Open Alfred Preferences → Workflows → AI Quick Ask
2. Click the `[x]` icon (workflow variables)
3. Set `ANTHROPIC_API_KEY` to your Claude API key

### Alfred Recommended Settings
- **Hotkey**: `Cmd+Space` (replace Spotlight) or `Option+Space`
- **Clipboard History**: Enable in Alfred Preferences → Features → Clipboard History
- **Snippets**: Enable in Alfred Preferences → Features → Snippets
- **File Search**: Already enabled by default
- **Calculator**: Already enabled by default

## Project Directories Scanned
The Project Launcher scans:
- `/Volumes/NVMe2tbCrucial500/Code/`
- `~/Documents/GitHub/`
