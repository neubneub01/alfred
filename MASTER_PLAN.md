# Alfred Power Setup — Master Plan

## Vision
Replace Raycast entirely. Alfred becomes the single command center for the entire Mac — launching, searching, automating, AI, dev tools, homelab, and daily productivity.

---

## Phase 1: Foundation (DONE)
Core workflows installed and working.

- [x] **Homelab SSH** — `ssh` → connect to homelab nodes
- [x] **Dev Tools** — `uuid`, `base64e/d`, `epoch`, `hash`, `json`, `urlencode/d`, `lorem`, `hex`
- [x] **System Commands** — `flushdns`, `emptytrash`, `darkmode`, `showfiles`, `lock`, `sleep`, `wifi`, etc.
- [x] **Process Killer** — `kill` → find and kill processes
- [x] **Project Launcher** — `code` → open projects in VS Code
- [x] **IP Info** — `ip` → local/public IP, gateway, DNS, SSID
- [x] **AI Quick Ask** — `ai` → ask Claude questions, Large Type response
- [x] **Quick Search** — `g`, `gh`, `so`, `npm`, `yt`, `reddit`, `wiki`, `maps`, etc.

### Phase 1 Fixes Needed
- [ ] Sync source repo → Alfred directory after edits (install.sh now copies, not symlinks)
- [ ] Test all workflows end-to-end after restart

---

## Phase 2: Raycast Feature Parity
Everything Raycast did, Alfred does better.

### 2A — Built-in Alfred Features to Configure
- [ ] **Clipboard History** — Enable, set 3-month retention, configure hotkey (Cmd+Shift+V)
- [ ] **Snippets** — Import/create text expansion snippets (email, address, date formats, code blocks)
- [ ] **File Search** — Tune search scope (include NVMe volume, exclude node_modules/.git)
- [ ] **Calculator** — Already built-in, verify working
- [ ] **Contacts** — Enable contact search
- [ ] **Music/Media** — Enable mini player controls
- [ ] **1Password / Keychain** — Integrate password lookup if applicable
- [ ] **Hotkey** — Set Cmd+Space as primary (disable Spotlight)
- [ ] **Appearance** — Dark theme, match system

### 2B — New Workflows to Build
- [ ] **Clipboard Formatter** — `upper`, `lower`, `title`, `camel`, `snake`, `kebab` → transform clipboard text
- [ ] **Window Manager** — `win left`, `win right`, `win full`, `win center` → window tiling (or integrate Rectangle)
- [ ] **Emoji Picker** — `emoji {search}` → search and copy emoji
- [ ] **Color Picker** — `color` → screen color picker, copy hex/rgb
- [ ] **Timer/Stopwatch** — `timer 5m`, `stopwatch` → quick timers with notification
- [ ] **Quick Notes** — `note {text}` → append to a scratchpad file, `notes` → open it
- [ ] **Bookmark Search** — `bm {query}` → search Chrome/Safari bookmarks
- [ ] **Recent Files** — `recent` → show recently opened files
- [ ] **Define Word** — `define {word}` → dictionary lookup
- [ ] **Translate** — `tr {text}` → quick translate via API
- [ ] **Calendar** — `cal` → show today's events, `cal add` → quick event creation
- [ ] **Reminders** — `remind {text} in 30m` → create a macOS reminder

### 2C — Homelab & DevOps Workflows
- [ ] **Docker Manager** — `docker ps`, `docker stop {name}`, `docker logs {name}` → manage containers on homelab
- [ ] **Proxmox Quick** — `pve` → show VM/LXC status, start/stop VMs
- [ ] **SSH Tunnel** — `tunnel {service}` → set up SSH tunnels to homelab services
- [ ] **Tailscale** — `ts` → show Tailscale status, connect/disconnect
- [ ] **Port Scanner** — `ports {host}` → quick port check on a host
- [ ] **Wake-on-LAN** — `wake {host}` → send WOL packet to homelab nodes

### 2D — Enhanced AI Workflows
- [ ] **AI Chat** — `ai` upgrade: multi-turn conversation in a floating window or sequential Large Type
- [ ] **AI Summarize** — `sum` → summarize clipboard contents
- [ ] **AI Rewrite** — `rewrite formal/casual/shorter` → rewrite clipboard text
- [ ] **AI Code** — `aicode {description}` → generate code snippet, copy to clipboard
- [ ] **AI Explain** — `explain` → explain clipboard code/text
- [ ] **Multi-Model** — `gpt {query}` → OpenAI, `gem {query}` → Gemini (you have keys for all 3)

---

## Phase 3: Power User & Automation
Go beyond what Raycast could do.

### 3A — Workflow Automation
- [ ] **n8n Triggers** — `n8n {workflow}` → trigger n8n workflows on homelab
- [ ] **Cron Status** — `cron` → show scheduled tasks status
- [ ] **GitHub Actions** — `actions {repo}` → show workflow run status
- [ ] **Deploy** — `deploy {project}` → trigger deployment pipelines

### 3B — Personal Productivity
- [ ] **OpenClaw Integration** — `claw {command}` → interface with OpenClaw
- [ ] **Fitness Log** — `fit {exercise} {weight} {reps}` → log to fitness-neub
- [ ] **Golf Stats** — `golf` → quick access to data-golf tools
- [ ] **Career Hub** — `career` → open career-hub dashboard, search jobs

### 3C — System Intelligence
- [ ] **System Monitor** — `sys` → CPU, RAM, disk, battery at a glance
- [ ] **Disk Usage** — `disk` → show disk usage for all volumes
- [ ] **Network Speed** — `speed` → quick speed test
- [ ] **Brew Manager** — `brew outdated`, `brew update`, `brew cleanup` → Homebrew management
- [ ] **App Cleaner** — `uninstall {app}` → cleanly remove apps and their files

### 3D — Alfred Theme & UX
- [ ] Custom Alfred theme matching system aesthetic
- [ ] Workflow icons (SF Symbols or custom)
- [ ] Fallback searches configuration
- [ ] Universal Actions setup (select text → transform/search/ai)

---

## Phase 4: Distribution & Maintenance
- [ ] GitHub repo with all workflows version-controlled
- [ ] `install.sh` handles fresh install and updates (copies to Alfred dir)
- [ ] `update.sh` — pull latest from GitHub + reinstall
- [ ] Workflow documentation in README
- [ ] Backup Alfred preferences to repo

---

## Architecture Notes

### File Structure
```
alfred/
├── MASTER_PLAN.md          ← This file
├── README.md               ← Usage docs
├── install.sh              ← Copies workflows into Alfred
├── workflows/
│   ├── ai-ask/             ← Claude AI integration
│   ├── dev-tools/          ← Developer utilities
│   ├── homelab-ssh/        ← Homelab SSH connections
│   ├── ip-info/            ← Network information
│   ├── process-killer/     ← Kill processes
│   ├── project-launcher/   ← Open projects in VS Code
│   ├── quick-search/       ← Multi-engine web search
│   └── system-commands/    ← System management
```

### Key Decisions
- **Copies, not symlinks** — Alfred doesn't reliably follow symlinks to external volumes
- **Shell scripts** — All workflows use bash for portability, python3 for JSON/encoding
- **API keys from ~/.zshrc** — Alfred doesn't source shell profiles; scripts grep the key directly
- **install.sh re-runs** — Overwrites existing, restarts Alfred automatically

### API Keys Available
- Anthropic (Claude): ~/.zshrc
- OpenAI (GPT): ~/.zshrc
- Google (Gemini): ~/.zshrc

### Project Directories
- /Volumes/NVMe2tbCrucial500/Code/ — Main code directory
- ~/Documents/GitHub/ — GitHub projects
- Homelab: 192.168.1.188, 192.168.1.166, 192.168.1.22
