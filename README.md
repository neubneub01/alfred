# Alfred Power Setup

Complete Alfred 5 workflow suite + AI Productivity Engine — a full Raycast replacement for macOS productivity backed by a homelab AI gateway.

## Alfred Workflows (Phase 1)

| Workflow | Keyword | Description |
|----------|---------|-------------|
| **Homelab SSH** | `ssh` | Quick SSH to homelab nodes (neubneub, neub, neub3) |
| **Dev Tools** | `uuid`, `base64e`, `base64d`, `epoch`, `hash`, `json`, `urlencode`, `urldecode`, `lorem`, `hex` | Developer utilities |
| **System Commands** | `flushdns`, `emptytrash`, `darkmode`, `showfiles`, `lock`, `sleep`, `wifi`, etc. | Quick system actions |
| **Process Killer** | `kill` | Find and kill running processes |
| **Project Launcher** | `code` | Open code projects in VS Code |
| **IP Info** | `ip` | Show local/public IP, gateway, DNS, Wi-Fi |
| **AI Quick Ask** | `ai`, `aikey` | Ask Claude AI quick questions |
| **Quick Search** | `g`, `gh`, `so`, `npm`, `yt`, `reddit`, `mdn`, `wiki`, `maps`, etc. | Multi-engine web search |
| **Things 3** | `do`, `things`, `find`, `plan`, `brainstorm`, `routine` | Full Things 3 integration |

## AI Productivity Engine (Gateway)

A self-hosted AI gateway running on the homelab that routes requests to the optimal model — local Ollama instances for classification/triage, frontier models (Claude, GPT, Gemini) for complex work.

### Architecture

```
Client Request
  → LiteLLM Gateway (192.168.1.52:4000)
    → Pre-call hook (classification + routing)
      → Local: Ollama qwen3.5:9b/27b (Host B/C GPUs)
      → Cloud: Claude Sonnet, GPT-5 Mini, Gemini
    → Post-call hook (validation + logging)
  → Response
```

### Stack (Host C LXC 102 — 192.168.1.52)

| Service | Port | Status |
|---------|------|--------|
| LiteLLM Gateway | 4000 | Running, healthy |
| Agent Service | 8100 | Running, healthy (9 tools, 4 agents) |
| n8n | 5678 | Running, 5 workflows active |

### External Access

- **Cloudflare Tunnel:** `ai-gateway.neubneub.com` → LiteLLM (port 4000)
- **Service Token Auth:** Bypasses Cloudflare Access OTP for API calls
- **n8n UI:** `n8n.neubneub.com`

### Model Aliases

| Alias | Model | Use Case |
|-------|-------|----------|
| code | claude-sonnet-4-6 | Code generation, technical work |
| analyze | claude-opus-4-6 | Deep analysis, complex reasoning |
| agent | claude-sonnet-4-6 | Agentic workflows, tool use |
| long-context | claude-sonnet-4-6 | Large document processing |
| chat | gpt-5-mini | Casual conversation, quick Q&A |
| summarize | ollama/qwen3.5:9b | Text summarization |
| batch-triage | ollama/qwen3.5:9b | Email/notification classification |
| vision | gpt-5-mini | Image analysis |
| private | ollama/qwen3.5:27b | Sensitive/private data processing |

### n8n Workflows

| ID | Workflow | Description |
|----|----------|-------------|
| 100 | Email Triage | IMAP fetch → LLM classification → priority routing → ntfy alerts |
| 101 | Job Search Pipeline | Score postings against 7-factor rubric → route high matches |
| 102 | Notification Filter | Webhook scoring with time-of-day gating → ntfy push |
| 103 | PBC Document Sorting | Document classification + weekly gap analysis |
| 104 | Music Library Automation | Nightly FLAC metadata + weekly album descriptions |

### NFS Context Library (21 files)

Mounted at `/mnt/ai-context/` in the agent-service container:

```
context/
├── career/          — Resume, STAR stories, cover letters, target companies
├── homelab/         — Architecture, GPU allocation, network map, troubleshooting
├── tax-reference/   — ASC 740, M-1/M-3, PBC checklist, deferred tax, provision workflow
└── templates/       — Engagement letter, PBC request, workpaper, status update
```

### Credentials Configured

| Credential | Type | Used By |
|------------|------|---------|
| LiteLLM Gateway Token | HTTP Header Auth | All n8n workflows |
| Fastmail IMAP | IMAP (michael@neuberger.work) | Email triage |
| Paperless Token | HTTP Header Auth | Document workflows |

## Installation

### Alfred Workflows
```bash
git clone https://github.com/Neubneub/alfred.git
cd alfred
./install.sh
```

### Gateway (already deployed to Host C LXC 102)
```bash
# Files in gateway/ — deployed via scp to /opt/litellm/
# Docker Compose manages litellm + agent-service
# n8n runs alongside with imported workflows
```

## Project Directories Scanned
- `/Volumes/NVMe2tbCrucial500/Code/`
- `~/Documents/GitHub/`

## Key Decisions
- **Copies, not symlinks** — Alfred doesn't reliably follow symlinks to external volumes
- **API keys from ~/.zshrc** — Alfred doesn't source shell profiles; scripts grep directly
- **install.sh re-runs** — Overwrites existing, restarts Alfred automatically
- **Gateway uses pre/post hooks** — LiteLLM custom_callbacks for routing, validation, logging
