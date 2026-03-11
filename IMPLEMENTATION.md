# AI Productivity Engine — Implementation Plan

**From Current State to Finished Project**

**Tool:** Claude Code (primary) | VS Code / Cursor (live editing, debugging)

**Date:** March 2026

---

## Current State Summary

**What exists (code written, not deployed):**
- `gateway/config.yaml` — LiteLLM config, 9 aliases, fallback chains
- `gateway/docker-compose.yaml` — Docker deployment for Host C LXC 102
- `gateway/hooks/pre_call.py` — 5-stage routing pipeline (685 lines)
- `gateway/hooks/post_call.py` — validation, escalation, SQLite logging (706 lines)
- `gateway/validators/batch_triage.py` — JSON schema validator
- `gateway/system-prompts.yaml` — all 9 alias system prompts
- `gateway/classification-prompt.txt` — qwen3.5:4b router prompt
- `gateway/n8n-email-triage.json` — n8n workflow export (email → classify → route)
- `gateway/tests/milestone2_validate.sh` — 18-test validation suite

**What does NOT exist yet:**
- Nothing deployed to any homelab host
- No Open WebUI / Cloudflare tunnel config
- No feedback loop (thumbs up/down)
- No backup/cron infrastructure
- No job search pipeline
- No document processing pipeline
- No notification filtering
- No agent framework (Tier 1 n8n or Tier 2 FastAPI)
- No Grafana dashboard
- No entity presence validator (summarize alias)
- No context loader folders
- No Alfred → gateway integration workflows

---

## Sprint Structure

| Sprint | Duration | Deliverable |
|--------|----------|-------------|
| **S1** | 2-3 days | Gateway deployed + live on Host C |
| **S2** | 2-3 days | Validation sprint — all 15 plan tests pass |
| **S3** | 1-2 days | Backup, git, recovery test |
| **S4** | 2-3 days | Open WebUI, Cloudflare tunnel, feedback loop |
| **S5** | 3-4 days | Email triage live + tested |
| **S6** | 3-4 days | Job search pipeline |
| **S7** | 3-4 days | Document processing + entity validator |
| **S8** | 2-3 days | Context loader + Tier 1 agents (n8n) |
| **S9** | 2-3 days | Notification filtering |
| **S10** | 2-3 days | PBC document sorting |
| **S11** | 3-4 days | Tier 2 agent framework (FastAPI) |
| **S12** | 2-3 days | Grafana dashboard + monitoring alerts |
| **S13** | 2-3 days | Music library automation |
| **S14** | 2-3 days | Alfred gateway workflows + polish |

---

## S1: Deploy Gateway (2-3 days)

**Goal:** Gateway running on Host C LXC 102, answering requests.

**Tool:** Claude Code (SSH commands) + VS Code (if debugging config issues)

### Prerequisites — verify before starting
```
# Claude Code — read homelab docs first
git -C ~/Documents/GitHub/homelab pull
# Then read 00_index.md and relevant files
```

### Step 1.1 — Prepare Host C LXC 102

```bash
# SSH to Host C bare metal
ssh root@192.168.1.22

# Verify LXC 102 exists and has Docker
pct exec 102 -- docker --version
pct exec 102 -- curl --version

# If LXC 102 doesn't exist, create from template
# (Check homelab docs for standard LXC creation)
```

### Step 1.2 — Deploy gateway files

```bash
# From Mac — copy gateway/ to Host C LXC 102
scp -r /Volumes/NVMe2tbCrucial500/Code/alfred/gateway/* root@192.168.1.52:/opt/litellm/

# SSH into LXC 102 and verify structure
ssh root@192.168.1.52
ls -la /opt/litellm/
# Expected: config.yaml, docker-compose.yaml, system-prompts.yaml,
#           classification-prompt.txt, hooks/, validators/, data/
```

### Step 1.3 — Set environment variables

```bash
# On LXC 102
cat >> /etc/environment << 'EOF'
LITELLM_MASTER_KEY=<generate-a-uuid>
ANTHROPIC_API_KEY=<from-mac-zshrc>
OPENAI_API_KEY=<from-mac-zshrc>
GEMINI_API_KEY=<from-mac-zshrc>
EOF

# Also create .env for docker-compose
cat > /opt/litellm/.env << 'EOF'
LITELLM_MASTER_KEY=<same-uuid>
ANTHROPIC_API_KEY=<same>
OPENAI_API_KEY=<same>
GEMINI_API_KEY=<same>
EOF
```

### Step 1.4 — Verify Ollama backends

```bash
# Host B LXC 501 — router model
ssh root@192.168.1.166
pct exec 501 -- curl -s http://localhost:11434/api/ps | jq .
# Must show qwen3.5:4b loaded

# Host A LXC 101 — heavy inference
ssh root@192.168.1.188
pct exec 101 -- curl -s http://localhost:11434/api/ps | jq .
# Must show qwen3.5:27b loaded

# Host C LXC 100 — batch processing
ssh root@192.168.1.22
pct exec 100 -- curl -s http://localhost:11434/api/ps | jq .
# Must show qwen3.5:9b loaded
```

If models aren't pulled:
```bash
# Example: on Host B LXC 501
pct exec 501 -- ollama pull qwen3.5:4b
# Verify OLLAMA_KEEP_ALIVE=60m is set in the Ollama systemd unit
```

### Step 1.5 — Start the gateway

```bash
ssh root@192.168.1.52
cd /opt/litellm
docker compose up -d
docker logs -f litellm-gateway  # watch for startup errors
```

### Step 1.6 — Smoke test

```bash
# From Mac
curl -s http://192.168.1.52:4000/health | jq .

# Basic chat request
curl -s http://192.168.1.52:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <LITELLM_MASTER_KEY>" \
  -d '{"model":"chat","messages":[{"role":"user","content":"Hello"}],"stream":false}' | jq .
```

### Step 1.7 — Fix issues

Common problems to watch for:
- **Hook import errors:** Check `docker logs litellm-gateway` for Python import failures. The `PYTHONPATH=/app/config` in docker-compose should make `hooks.pre_call` importable. If not, adjust the Python path.
- **Ollama unreachable:** Verify LXC network — `ping 192.168.1.41` from LXC 102.
- **API key errors:** Verify env vars are passed through to the container.
- **YAML parse errors:** Validate `config.yaml` and `system-prompts.yaml` with `python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"`.

**Exit criteria:** `curl http://192.168.1.52:4000/health` returns 200. At least one alias returns a valid response.

---

## S2: Validation Sprint (2-3 days)

**Goal:** All 15 AI-PLAN tests pass. No exceptions.

**Tool:** Claude Code (run tests, debug, iterate)

### Step 2.1 — Run automated test suite

```bash
# From Mac
export LITELLM_MASTER_KEY=<your-key>
cd /Volumes/NVMe2tbCrucial500/Code/alfred/gateway/tests
chmod +x milestone2_validate.sh
./milestone2_validate.sh
```

### Step 2.2 — Manual infrastructure tests

These can't be automated — they require toggling hardware:

| # | Test | How To Execute |
|---|------|---------------|
| 1 | Offline backend | SSH to burst machine, `systemctl stop ollama`. Send request. Verify zero added latency. |
| 2 | Backend comes online | `systemctl start ollama`. Wait 60s. Send request. Verify it routes there. |
| 3 | Fallback chain | Stop Ollama on Host A (`pct exec 101 -- systemctl stop ollama`), then Host C (`pct exec 100 -- systemctl stop ollama`). Send `private` request. Must get response from deepest fallback. |
| 4 | Streaming | `curl -N` with `"stream": true` through each alias. Verify chunks arrive incrementally. |
| 5 | Router model down | `pct exec 501 -- systemctl stop ollama`. Send `auto` request. Must fall back to claude-sonnet-4-6 within 3s. |
| 6 | Malformed JSON | Temporarily corrupt classification-prompt.txt. Send `auto` request. Must fall back gracefully. Restore prompt. |
| 12 | VRAM gate | Run GPU stress on Host A. Check `curl http://192.168.1.220:11435` returns 503. Send request — must route to 5060 Ti. |
| 13 | Pipeline health ntfy | Stop router. Send 6+ `auto` requests. Check ntfy (192.168.1.38:8090) fires after 5th consecutive failure. |

### Step 2.3 — Write VRAM gate service (if not existing)

**File:** `gateway/vram-gate/vram_gate.py`

```python
"""
VRAM gate — HTTP 200 if GPU VRAM < 90%, 503 otherwise.
Deploy to Host A LXC 101, port 11435.
"""
import subprocess
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

THRESHOLD = 0.90  # 90%

class VRAMHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5
            )
            used, total = [int(x.strip()) for x in result.stdout.strip().split(",")]
            ratio = used / total
            if ratio < THRESHOLD:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"vram_pct": round(ratio, 3), "status": "ok"}).encode())
            else:
                self.send_response(503)
                self.end_headers()
                self.wfile.write(json.dumps({"vram_pct": round(ratio, 3), "status": "overloaded"}).encode())
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def log_message(self, format, *args):
        pass  # silence logs

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 11435), VRAMHandler)
    print("VRAM gate listening on :11435")
    server.serve_forever()
```

Deploy:
```bash
scp gateway/vram-gate/vram_gate.py root@192.168.1.188:/opt/vram-gate/
# Create systemd unit on Host A LXC 101
ssh root@192.168.1.188
pct exec 101 -- bash -c 'cat > /etc/systemd/system/vram-gate.service << EOF
[Unit]
Description=VRAM Gate Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /opt/vram-gate/vram_gate.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now vram-gate'
```

### Step 2.4 — Fix and re-test

Iterate: fix issues found in tests, re-run `milestone2_validate.sh`. Common fixes:
- Adjust timeout values in pre_call.py
- Fix metadata key paths in post_call.py (LiteLLM's internal structure can vary by version)
- Tune classification prompt if routing accuracy is poor
- Adjust confidence threshold if too many requests fall to `chat`

**Exit criteria:** All 15 tests pass. Performance targets met (classification p95 < 1s, routed < 4s, hint < 2s).

---

## S3: Backup, Git, Recovery (1-2 days)

**Goal:** Config in git, backups running, recovery tested.

**Tool:** Claude Code (SSH for cron setup)

### Step 3.1 — Initialize /opt as git repo on Host C

```bash
ssh root@192.168.1.52
cd /opt
git init
cat > .gitignore << 'EOF'
*.db
*.db-journal
*.pyc
__pycache__/
.env
*.log
EOF

git add -A
git commit -m "Initial AI engine config"
git remote add origin <homelab-repo-url>
git push -u origin main
```

### Step 3.2 — Config snapshot cron

```bash
ssh root@192.168.1.52
cat > /etc/cron.d/ai-config-snapshot << 'CRON'
0 */6 * * * root cd /opt && git add -A && git diff --cached --quiet || git commit -m "auto: config snapshot $(date +\%Y-\%m-\%d_\%H:\%M)" && git push 2>/dev/null
CRON
```

### Step 3.3 — Nightly SQLite backup

**File:** `gateway/scripts/nightly_backup.sh`

```bash
#!/bin/bash
BACKUP_DIR="/mnt/nfs/backups/ai-engine/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"
sqlite3 /opt/litellm/data/litellm.db ".backup '$BACKUP_DIR/litellm.db'"
# Future: add agent-service and n8n backups here
find /mnt/nfs/backups/ai-engine/ -maxdepth 1 -mtime +30 -exec rm -rf {} +
```

Deploy:
```bash
scp gateway/scripts/nightly_backup.sh root@192.168.1.52:/opt/scripts/
ssh root@192.168.1.52 'chmod +x /opt/scripts/nightly_backup.sh'
ssh root@192.168.1.52 'echo "0 2 * * * root /opt/scripts/nightly_backup.sh" > /etc/cron.d/ai-nightly-backup'
```

### Step 3.4 — Recovery test

```bash
# DESTRUCTIVE — do this intentionally
# 1. Snapshot LXC 102 first: pct snapshot 102 pre-recovery-test
# 2. Destroy and rebuild
pct stop 102
pct destroy 102
# 3. Recreate from template, clone repo, docker compose up
# 4. Restore SQLite from NFS backup
# 5. Time it — must be < 40 minutes
```

**Exit criteria:** Git repo active. Crons running. Recovery < 40 min.

---

## S4: Open WebUI + Cloudflare + Feedback (2-3 days)

**Goal:** Web UI connected to gateway, external access, user feedback loop.

**Tool:** Claude Code (SSH) + VS Code (if editing Open WebUI config)

### Step 4.1 — Configure Open WebUI → gateway

```bash
ssh root@192.168.1.188  # Host A LXC 101 where Open WebUI lives
# Edit Open WebUI config to point at gateway
# Open WebUI env: OPENAI_API_BASE_URL=http://192.168.1.52:4000/v1
# Restart Open WebUI container
```

### Step 4.2 — Cloudflare tunnel

```bash
ssh root@192.168.1.52
# Add to existing cloudflared config (check homelab docs for tunnel setup)
# Route: ai-gateway.neubneub.com → http://localhost:4000
# The tunnel should already exist — just add the new route
```

### Step 4.3 — Classification feedback system

**File:** `gateway/hooks/feedback.py`

This adds a `feedback` table and an endpoint for Open WebUI thumbs up/down:

```python
"""
Feedback hook — links user satisfaction to router classification.
Adds POST /v1/feedback endpoint.
"""
import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
import os

logger = logging.getLogger("litellm.feedback")

CONFIG_DIR = Path(os.environ.get("LITELLM_CONFIG_DIR", "/app/config"))
DB_PATH = CONFIG_DIR / "data" / "litellm.db"

FEEDBACK_DDL = """
CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    request_id  TEXT NOT NULL,
    rating      INTEGER NOT NULL,  -- 1 = thumbs up, -1 = thumbs down
    alias       TEXT,
    model       TEXT,
    comment     TEXT
);
CREATE INDEX IF NOT EXISTS idx_feedback_request_id ON feedback(request_id);
CREATE INDEX IF NOT EXISTS idx_feedback_alias ON feedback(alias);
"""

def init_feedback_table():
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.executescript(FEEDBACK_DDL)
    except Exception as e:
        logger.error("Failed to init feedback table: %s", e)

def record_feedback(request_id, rating, alias=None, model=None, comment=None):
    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            conn.execute(
                """INSERT INTO feedback (timestamp, request_id, rating, alias, model, comment)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (datetime.now(timezone.utc).isoformat(), request_id, rating, alias, model, comment)
            )
    except Exception as e:
        logger.error("Feedback write failed: %s", e)
```

**Integration approach:** Either (a) add a custom FastAPI endpoint alongside LiteLLM, or (b) use Open WebUI's webhook/callback on rating to POST to a small sidecar service that writes to SQLite.

**Exit criteria:** Open WebUI routes through gateway. External access works via Cloudflare. Feedback writes to SQLite.

---

## S5: Email Triage Live (3-4 days)

**Goal:** Emails auto-classified and routed. < 2 min/day manual triage.

**Tool:** Claude Code (n8n workflow iteration) + VS Code/Cursor (n8n workflow editor in browser)

### Step 5.1 — Import n8n workflow

```bash
# n8n API — import the pre-built workflow
curl -s -X POST http://192.168.1.52:5678/api/v1/workflows \
  -H "Content-Type: application/json" \
  -H "X-N8N-API-KEY: <n8n-api-key>" \
  -d @/Volumes/NVMe2tbCrucial500/Code/alfred/gateway/n8n-email-triage.json
```

### Step 5.2 — Configure Fastmail JMAP credentials in n8n

In the n8n UI (http://192.168.1.52:5678):
1. Create credential: "Fastmail JMAP" — HTTP Header Auth with Fastmail API token
2. Set workflow variables: `accountId`, `inboxId`, `jobSearchFolderId`, `actionRequiredFolderId`
3. Test JMAP connection: verify the workflow's first node can fetch emails

### Step 5.3 — Tune classification prompt

**File:** Update the system prompt in the n8n workflow's HTTP Request node.

The classification prompt needs domain-specific tuning for recruiter emails:
- Tax provision role synonyms: "income tax," "ASC 740," "tax accounting," "tax compliance," "tax provision," "deferred tax"
- Recruiter patterns: subject line signals, sender domain patterns
- Priority signals: direct recruiter vs. mass blast

### Step 5.4 — Test with real email backlog

```bash
# Manually trigger the workflow with a backfill:
# Change the JMAP query to fetch last 4 weeks of email
# Run in dry-run mode (log actions but don't move emails)
# Review classification accuracy
# Fix false positives/negatives by tuning the prompt
```

### Step 5.5 — Enable live polling

Activate the workflow's 5-minute schedule trigger. Monitor for 48 hours.

**Exit criteria:** Workflow classifying real emails. < 2 min/day manual review after 1 week.

---

## S6: Job Search Pipeline (3-4 days)

**Goal:** Job postings scored and routed to Things 3 or application pipeline.

**Tool:** Claude Code (n8n workflows, scoring logic)

### Step 6.1 — Create job scoring n8n workflow

**File:** `gateway/n8n-job-search.json`

Build in n8n UI, then export. Pipeline:

```
Source trigger (email forward / RSS / webhook)
  → Extract job posting text
  → POST to gateway (model: "batch-triage")
    System prompt includes the 7-factor scoring rubric:
      - ASC 740 focus (25%)
      - Team size/structure (20%)
      - M&A exposure (15%)
      - Tech stack (15%)
      - Location (10%)
      - Seniority (10%)
      - Company stability (5%)
    Output schema: {"score": int, "factors": {...}, "summary": string}
  → Score router:
    - > 80 → trigger Job Application Pipeline (S8)
    - 60-80 → create Things 3 task (things:///add?title=...)
    - < 60 → log and skip
```

### Step 6.2 — Job scoring prompt

**File:** `gateway/prompts/job-scoring.txt`

```
You are a job matching engine for a Senior Tax Manager seeking ASC 740 / income
tax provision roles. Score the following job posting on a 0-100 scale.

Scoring factors:
- ASC 740 / tax provision focus (25%): Explicit mention of income tax provision,
  deferred tax, ASC 740, tax accounting. Score 0 if none, 25 if primary focus.
- Team size / structure (20%): Established team, manager role, team of 5+.
  Score 0 if solo contributor, 20 if managing a team.
- M&A / transaction exposure (15%): Deal-related tax, due diligence, transaction.
  Score 0 if none, 15 if significant.
- Tech stack / automation (15%): Modern tools, automation focus, data analytics.
  Score 0 if none, 15 if strong tech emphasis.
- Location (10%): Remote = 10, hybrid in target metros = 7, onsite = 3.
- Seniority match (10%): Manager/Senior Manager = 10, Director = 7,
  Staff/Senior = 5, VP/Partner = 3.
- Company stability (5%): Public/established = 5, mid-size = 3, startup = 1.

Return ONLY this JSON:
{"score": <0-100>, "factors": {"asc740": <0-25>, "team": <0-20>, "ma": <0-15>,
 "tech": <0-15>, "location": <0-10>, "seniority": <0-10>, "stability": <0-5>},
 "summary": "<1-2 sentence summary>", "confidence": <0.0-1.0>}
```

### Step 6.3 — Data source integrations

Build separate n8n triggers for each source:

1. **LinkedIn email alerts:** Parse forwarded emails (already in inbox → email triage flags them → webhook to job pipeline)
2. **Company career pages:** n8n HTTP Request nodes with schedules:
   ```
   Cron (daily 8am)
     → Fetch career page RSS/JSON for each target company
     → Extract new postings (compare against SQLite seen_jobs table)
     → Feed to scoring pipeline
   ```
3. **Indeed/Google Jobs (future):** Placeholder nodes, activate when API access available

### Step 6.4 — Things 3 integration for 60-80 scores

```bash
# n8n Code node — create Things 3 task via URL scheme
# Uses the things:///json URL scheme (already proven in Alfred things workflow)
const task = {
  type: "to-do",
  attributes: {
    title: `Review: ${jobTitle} at ${company} (Score: ${score})`,
    notes: `${summary}\n\nScore breakdown: ${JSON.stringify(factors)}\n\nLink: ${url}`,
    "list-id": "Career",  // Things 3 area
    tags: ["job-search", `score-${Math.floor(score/10)*10}`],
    deadline: new Date(Date.now() + 7*24*60*60*1000).toISOString().split('T')[0]
  }
};
```

**Exit criteria:** Pipeline scoring real postings. Things 3 tasks appearing for 60-80 scores.

---

## S7: Document Processing + Entity Validator (3-4 days)

**Goal:** Documents preprocessed before frontier analysis. Entity validator live.

**Tool:** Claude Code (validators, prompts) + n8n UI (workflow)

### Step 7.1 — Entity presence validator

**File:** `gateway/validators/entity_presence.py`

```python
"""
Entity presence validator for 'summarize' alias.
Ensures summaries retain key entities (dollar amounts, dates, proper nouns).
Threshold: 60% entity overlap between original and summary.
"""
import re
from typing import Set, Tuple

def extract_entities(text: str) -> Set[str]:
    entities = set()
    # Dollar amounts
    entities.update(re.findall(r'\$[\d,.]+', text))
    # Dates (various formats)
    entities.update(re.findall(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', text))
    entities.update(re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}\b', text))
    # Proper nouns (capitalized multi-word sequences)
    entities.update(re.findall(r'\b[A-Z][a-z]+ (?:[A-Z][a-z]+ ?)+', text))
    # Percentages
    entities.update(re.findall(r'\d+\.?\d*%', text))
    return entities

def validate_summary(output: str, original: str = "", threshold: float = 0.6) -> Tuple[bool, str]:
    """Validate summary retains key entities from original.

    NOTE: This validator requires the original text, which must be passed
    via request metadata. If original is empty, validation passes (graceful).
    """
    if not original:
        return True, ""

    original_entities = extract_entities(original)
    if not original_entities:
        return True, ""

    summary_entities = extract_entities(output)
    overlap = len(original_entities & summary_entities) / len(original_entities)

    if overlap >= threshold:
        return True, ""
    else:
        missing = original_entities - summary_entities
        return False, f"Entity overlap {overlap:.0%} < {threshold:.0%}. Missing: {list(missing)[:5]}"
```

### Step 7.2 — Register entity validator

**Edit:** `gateway/validators/__init__.py`

```python
from validators.batch_triage import validate_triage
from validators.entity_presence import validate_summary

VALIDATORS = {
    "batch-triage": validate_triage,
    "summarize": validate_summary,
}
```

**Edit:** `gateway/hooks/post_call.py` — update `_get_validators()` to load from registry.

### Step 7.3 — Document processing n8n workflow

**File:** `gateway/n8n-document-processing.json`

Build in n8n UI:

```
Paperless-ngx webhook (new document)
  → GET document text via Paperless API
  → POST to gateway (model: "batch-triage")
    System prompt: Classify document type + extract metadata
    Output: {"type": "tax-return|financial-statement|engagement-letter|...",
             "metadata": {...}, "confidence": float}
  → If type requires frontier analysis:
    → POST to gateway (model: "summarize")
      Condense to < 5k tokens
    → Validate summary (entity presence)
    → If summary > 30k tokens still: route to long-context (Gemini Pro)
    → POST to gateway (model: "analyze")
      Condensed context + analysis question
    → Store result + notify via ntfy
  → Tag document in Paperless-ngx via API
```

### Step 7.4 — Paperless-ngx API integration

```bash
# Test Paperless API access from n8n
curl -s http://192.168.1.221:8000/api/documents/ \
  -H "Authorization: Token <paperless-api-token>" | jq '.count'
```

**Exit criteria:** Documents auto-classified and tagged. Summaries pass entity validation. Frontier token usage reduced 70-90%.

---

## S8: Context Loader + Tier 1 Agents (2-3 days)

**Goal:** Context folders populated. Four n8n agent workflows operational.

**Tool:** Claude Code (content creation) + n8n UI (workflows)

### Step 8.1 — Create context loader folders

```bash
ssh root@192.168.1.166  # Host B (NFS host)
mkdir -p /mnt/nfs/ai-context/{career,tax-reference,homelab,templates}
```

### Step 8.2 — Populate context folders

**Claude Code task:** Generate initial content for each folder.

#### career/
```
career/
├── resume-base.md          # Master resume, all bullets
├── resume-tax-manager.md   # Tax manager variant
├── star-stories.md         # STAR format stories (10-15)
├── engagement-summaries.md # Key engagement descriptions
├── cover-letter-base.md    # Template cover letter
└── target-companies.md     # Priority company list + notes
```

#### tax-reference/
```
tax-reference/
├── asc740-overview.md      # ASC 740 guidance summary
├── m1-m3-items.md          # Common M-1/M-3 book-tax differences
├── pbc-checklist.md        # Standard PBC request list
├── deferred-tax-patterns.md # Common deferred tax scenarios
└── provision-workflow.md   # Tax provision process steps
```

#### homelab/
```
homelab/
├── architecture.md         # Node inventory, IPs, services
├── gpu-allocation.md       # GPU VRAM budgets per node
├── troubleshooting.md      # Common issues + fixes
└── network-map.md          # VLAN, DNS, Cloudflare tunnels
```

#### templates/
```
templates/
├── engagement-letter.md    # Engagement letter template
├── pbc-request-list.md     # Standard PBC items
├── workpaper-format.md     # Standard workpaper structure
└── status-update.md        # Client status update template
```

### Step 8.3 — Tier 1 Agent: Job Application Pipeline

**n8n workflow triggered by S6 job scoring (score > 80)**

```
Webhook trigger (from job scoring pipeline, score > 80)
  → context_load: GET /mnt/nfs/ai-context/career/resume-base.md
  → context_load: GET /mnt/nfs/ai-context/career/star-stories.md
  → POST to gateway (model: "code")
    Prompt: "Analyze this job posting against my resume.
             Identify matching qualifications, gaps, and key phrases.
             Suggest resume bullet modifications."
    Context: [resume + job posting]
  → POST to gateway (model: "code")
    Prompt: "Draft a cover letter for this role using my STAR stories."
    Context: [star-stories + job analysis]
  → Create Things 3 project:
    things:///json?data=[{
      "type": "project",
      "attributes": {
        "title": "Apply: {title} at {company}",
        "area-id": "Career",
        "items": [
          {"type":"to-do","attributes":{"title":"Review tailored resume"}},
          {"type":"to-do","attributes":{"title":"Review cover letter draft"}},
          {"type":"to-do","attributes":{"title":"Submit application"}},
          {"type":"to-do","attributes":{"title":"Follow up (1 week)"}}
        ]
      }
    }]
  → Fastmail draft: Create email draft with cover letter + resume notes
  → ntfy: "New high-match job: {title} at {company} (Score: {score})"
```

### Step 8.4 — Tier 1 Agent: Email Response Drafter

**n8n workflow triggered by email triage "actionable" classification**

```
Webhook trigger (from email triage, category = "actionable")
  → Fastmail JMAP: Fetch full thread
  → context_load: career/ (if recruiter) or templates/ (if client)
  → POST to gateway (model: "chat")
    Prompt: "Draft a response to this email thread.
             Context: {career/template context}.
             Tone: professional, concise. Include specific next steps."
  → Fastmail JMAP: Save as draft (do NOT send)
  → Things 3: Create task "Review + send response to {sender}"
  → ntfy: "Draft ready: RE: {subject}"
```

### Step 8.5 — Tier 1 Agent: Document Analysis Pipeline

**n8n workflow — chains S7 document processing with context loader**

```
Webhook (from document processing pipeline, post-classification)
  → context_load: Load relevant context by document type
    - tax-return → tax-reference/asc740-overview.md + m1-m3-items.md
    - engagement-letter → templates/engagement-letter.md
    - financial-statement → tax-reference/provision-workflow.md
  → POST to gateway (model: "analyze")
    Prompt: "Analyze this {doc_type}. {condensed_summary}.
             Context: {loaded_context}.
             Provide: key findings, risks, action items."
  → ntfy: "Analysis complete: {doc_title}"
  → Paperless-ngx: Tag with analysis results
```

### Step 8.6 — Tier 1 Agent: Weekly Digest

**n8n cron workflow — Sunday 8 PM**

```
Cron trigger: Sunday 20:00
  → SQLite query: aggregate week's requests, costs, escalation rates
  → SQLite query: email triage stats (count per category)
  → SQLite query: job search stats (new postings, scores, applications)
  → Paperless-ngx API: documents processed this week
  → POST to gateway (model: "summarize")
    Prompt: "Create a weekly digest from these metrics:
             {request_stats}, {email_stats}, {job_stats}, {doc_stats}.
             Format: executive summary, then section bullets."
  → ntfy: Push full digest
```

**Exit criteria:** All 4 Tier 1 agents functional. Context folders populated and used.

---

## S9: Notification Filtering (2-3 days)

**Goal:** Smart notification scoring. Score 4-5 → ntfy. Score 1-3 → log only.

**Tool:** Claude Code (n8n workflow + scoring logic)

### Step 9.1 — Notification scoring n8n workflow

**File:** `gateway/n8n-notification-filter.json`

```
Webhook trigger (receives alerts from Alertmanager, n8n events, etc.)
  → Extract: source, type, message, severity
  → Deterministic scoring (no LLM needed):
    Score 5 (Critical):
      - Service down > 5 min
      - LXC/container crashed
      - Gateway unreachable
    Score 4 (High):
      - Disk > 85%
      - GPU temp > 85C
      - Workflow failure
      - Job match > 80
    Score 3 (Medium):
      - Escalation rate > 25%
      - API cost > $10/day
      - High-priority email
    Score 2 (Low):
      - Transient CPU spikes
      - Watchtower updates
      - Scheduled restarts
    Score 1 (Noise):
      - Successful routine runs
      - Brief latency spikes
  → Time-of-day weight:
    22:00-07:00 → only push score 5
    07:00-22:00 → push score 4-5
  → Score >= threshold → ntfy push
  → All → SQLite log (notifications table)
```

### Step 9.2 — Alertmanager webhook integration

```yaml
# Add to Alertmanager config on Host C CT 101
receivers:
  - name: 'ai-filter'
    webhook_configs:
      - url: 'http://192.168.1.52:5678/webhook/notification-filter'
        send_resolved: true
```

**Exit criteria:** Noise reduced by 50%+. Only actionable alerts push to phone.

---

## S10: PBC Document Sorting (2-3 days)

**Goal:** Documents auto-classified against PBC checklist. Gap analysis report.

**Tool:** Claude Code (n8n workflow) + n8n UI

### Step 10.1 — PBC classification n8n workflow

```
Webhook (from document processing pipeline)
  → context_load: templates/pbc-request-list.md
  → POST to gateway (model: "batch-triage")
    Prompt: "Classify this document against the PBC checklist.
             PBC items: {pbc_list}.
             Document summary: {summary}.
             Return: {pbc_item_id, confidence, matched_content}"
  → Route to correct Paperless-ngx folder by PBC category
  → Update PBC tracking table in SQLite
```

### Step 10.2 — Gap analysis report

```
Cron trigger (weekly or on-demand via Alfred)
  → SQLite: Query PBC tracking — find items with no matching document
  → POST to gateway (model: "chat")
    Prompt: "Generate a PBC gap analysis. Missing items: {list}.
             Received items: {list}. Format as a client-ready report."
  → Create Things 3 tasks for each missing item
  → ntfy: "PBC gap report ready — {n} items outstanding"
```

**Exit criteria:** Documents auto-sorted into PBC categories. Gap report accurate.

---

## S11: Tier 2 Agent Framework (3-4 days)

**Goal:** FastAPI agent service with tool registry. 4 Tier 2 agents.

**Tool:** Claude Code (Python development) + VS Code/Cursor (debugging)

### Step 11.1 — Agent service scaffold

**Directory:** `gateway/agent-service/`

```
agent-service/
├── Dockerfile
├── requirements.txt
├── main.py              # FastAPI app, POST /v1/agent/run
├── agent_loop.py        # Core agent loop (observe → think → act)
├── tools/
│   ├── __init__.py
│   ├── registry.py      # Tool registry loader
│   ├── gateway_chat.py  # Send prompt to LiteLLM gateway
│   ├── context_load.py  # Load markdown from NFS
│   ├── paperless.py     # Paperless-ngx search/download/tag
│   ├── fastmail.py      # JMAP search/draft/label
│   ├── things.py        # Things 3 URL scheme
│   ├── ntfy.py          # Push notification
│   ├── n8n_webhook.py   # Trigger n8n workflow
│   ├── web_search.py    # SearXNG or gateway
│   └── shell_exec.py    # Whitelisted commands only
├── agents/
│   ├── __init__.py
│   ├── research.py      # Research agent
│   ├── tax_prep.py      # Tax prep agent
│   ├── interview_prep.py # Interview prep agent
│   └── homelab_troubleshooter.py # Homelab agent
├── config/
│   ├── tools.yaml       # Tool definitions + JSON schemas
│   └── agents.yaml      # Agent personas + tool allowlists + limits
└── data/
    └── agents.db        # Agent run history (SQLite)
```

### Step 11.2 — Core agent loop

**File:** `gateway/agent-service/agent_loop.py`

```python
"""
Core agent loop — observe → think → act.
All LLM calls route through the gateway.
"""
import asyncio
import time
import httpx
from dataclasses import dataclass, field
from typing import Any

GATEWAY_URL = "http://192.168.1.52:4000/v1/chat/completions"
MAX_ITERATIONS_DEFAULT = 10
MAX_ITERATIONS_HARD = 25
COST_CEILING_PER_RUN = 2.00  # dollars
DAILY_COST_BREAKER = 15.00
CONTEXT_SUMMARIZE_THRESHOLD = 0.80  # % of window

@dataclass
class AgentRun:
    agent_id: str
    task: str
    model: str = "agent"
    tools: list = field(default_factory=list)
    max_iterations: int = MAX_ITERATIONS_DEFAULT
    messages: list = field(default_factory=list)
    iteration: int = 0
    total_cost: float = 0.0
    status: str = "running"
    result: Any = None

async def run_agent(run: AgentRun, tool_registry: dict) -> AgentRun:
    """Execute agent loop until task complete, max iterations, or cost ceiling."""

    # Build initial messages
    agent_config = _load_agent_config(run.agent_id)
    run.messages = [
        {"role": "system", "content": agent_config["system_prompt"]},
        {"role": "user", "content": run.task},
    ]

    while run.iteration < min(run.max_iterations, MAX_ITERATIONS_HARD):
        run.iteration += 1

        # Cost check
        if run.total_cost >= COST_CEILING_PER_RUN:
            run.status = "cost_ceiling"
            break

        # Context window management
        if _context_usage(run.messages) > CONTEXT_SUMMARIZE_THRESHOLD:
            run.messages = await _summarize_history(run.messages)

        # Call gateway
        response = await _gateway_call(run.model, run.messages)
        run.total_cost += response.get("cost", 0)

        assistant_msg = response["choices"][0]["message"]
        run.messages.append(assistant_msg)

        # Check for tool calls
        tool_calls = assistant_msg.get("tool_calls", [])
        if not tool_calls:
            # Agent is done — no more tool calls
            run.status = "complete"
            run.result = assistant_msg.get("content", "")
            break

        # Execute tool calls
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            tool_args = tc["function"]["arguments"]

            if tool_name not in run.tools:
                tool_result = f"Error: tool '{tool_name}' not in allowlist"
            elif tool_name not in tool_registry:
                tool_result = f"Error: tool '{tool_name}' not registered"
            else:
                tool_result = await tool_registry[tool_name].execute(tool_args)

            run.messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(tool_result),
            })

    if run.status == "running":
        run.status = "max_iterations"

    return run
```

### Step 11.3 — Tool implementations

Each tool is a small module with an `execute(args)` async method:

**`tools/gateway_chat.py`:**
```python
async def execute(args: dict) -> str:
    """Send a prompt to the gateway. Args: {model, prompt, system?}"""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(GATEWAY_URL, json={
            "model": args.get("model", "chat"),
            "messages": [
                *([{"role": "system", "content": args["system"]}] if "system" in args else []),
                {"role": "user", "content": args["prompt"]},
            ],
            "stream": False,
        }, headers={"Authorization": f"Bearer {GATEWAY_KEY}"})
        return resp.json()["choices"][0]["message"]["content"]
```

**`tools/shell_exec.py`:**
```python
WHITELIST = [
    "curl -s", "docker ps", "docker logs --tail", "df -h", "free -m",
    "nvidia-smi", "systemctl status", "ping -c", "cat /proc/",
]

async def execute(args: dict) -> str:
    """Execute whitelisted shell command. Args: {command}"""
    cmd = args["command"]
    if not any(cmd.startswith(prefix) for prefix in WHITELIST):
        return f"Error: command not whitelisted: {cmd}"
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    return stdout.decode() + (f"\nSTDERR: {stderr.decode()}" if stderr else "")
```

### Step 11.4 — Agent definitions

**File:** `gateway/agent-service/config/agents.yaml`

```yaml
research:
  display_name: "Research Agent"
  model: agent
  max_iterations: 15
  tools:
    - gateway_chat
    - web_search
    - context_load
    - ntfy
  system_prompt: |
    You are a research agent. Given a topic, systematically search for
    information, synthesize findings, and produce a structured report.

    Process:
    1. Decompose the topic into 3-5 research questions
    2. Search for each question (web_search)
    3. Load relevant context if available (context_load)
    4. For complex sub-topics, use gateway_chat with model="analyze"
    5. Synthesize into a report: Executive Summary, Key Findings,
       Sources, Open Questions
    6. Send notification when complete (ntfy)

    Be thorough but efficient. Avoid redundant searches. Stop when you
    have sufficient coverage — don't chase diminishing returns.

tax_prep:
  display_name: "Tax Prep Agent"
  model: agent
  max_iterations: 20
  tools:
    - gateway_chat
    - context_load
    - paperless_search
    - paperless_download
    - things_create
    - ntfy
  system_prompt: |
    You are a tax preparation agent. Given a client name or engagement,
    prepare for the engagement by:

    1. Load PBC template (context_load: templates/pbc-request-list.md)
    2. Search Paperless-ngx for existing client documents (paperless_search)
    3. Download and review available documents (paperless_download)
    4. Compare against PBC checklist — identify gaps
    5. Use gateway_chat with model="analyze" for technical questions
    6. Generate follow-up request list for missing items
    7. Create Things 3 project with outstanding tasks (things_create)
    8. Send notification with summary (ntfy)

    Reference ASC 740, IRC sections, and specific standards when relevant.
    Be precise about which documents are present vs. missing.

interview_prep:
  display_name: "Interview Prep Agent"
  model: agent
  max_iterations: 15
  tools:
    - gateway_chat
    - context_load
    - web_search
    - things_create
    - ntfy
  system_prompt: |
    You are an interview preparation agent. Given a company name:

    1. Load career context (context_load: career/)
    2. Research the company (web_search): recent news, culture, products,
       tax department structure, notable transactions
    3. Map STAR stories to likely interview questions
    4. Generate 10 behavioral questions with suggested answers
    5. Generate 5 technical questions (ASC 740 focus)
    6. Create a Things 3 project with prep checklist (things_create)
    7. Send notification when ready (ntfy)

    Tailor everything to tax provision / ASC 740 roles.

homelab_troubleshooter:
  display_name: "Homelab Troubleshooter"
  model: agent
  max_iterations: 10
  tools:
    - gateway_chat
    - context_load
    - shell_exec
    - ntfy
  system_prompt: |
    You are a homelab troubleshooting agent. Given an alert or issue:

    1. Load homelab documentation (context_load: homelab/)
    2. Parse the alert — identify affected service, node, severity
    3. Run diagnostics (shell_exec): check service status, logs, resources
    4. Correlate findings with known issues from documentation
    5. Recommend specific fix with exact commands
    6. Send notification with diagnosis + recommended action (ntfy)

    Use shell_exec judiciously — only whitelisted commands. Never take
    destructive actions. Recommend, don't execute fixes.
```

### Step 11.5 — FastAPI main.py

**File:** `gateway/agent-service/main.py`

```python
"""
Tier 2 Agent Service — POST /v1/agent/run
Host C LXC 102, port 8100
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

from agent_loop import AgentRun, run_agent
from tools.registry import load_tools

app = FastAPI(title="AI Agent Service")
tool_registry = load_tools()

class AgentRequest(BaseModel):
    agent: str          # research, tax_prep, interview_prep, homelab_troubleshooter
    task: str           # natural language task description
    max_iterations: int = 10

class AgentResponse(BaseModel):
    status: str
    result: str
    iterations: int
    cost: float

@app.post("/v1/agent/run")
async def run(req: AgentRequest) -> AgentResponse:
    agent_run = AgentRun(
        agent_id=req.agent,
        task=req.task,
        max_iterations=req.max_iterations,
    )
    result = await run_agent(agent_run, tool_registry)
    return AgentResponse(
        status=result.status,
        result=result.result or "",
        iterations=result.iteration,
        cost=result.total_cost,
    )
```

### Step 11.6 — Docker + deploy

**File:** `gateway/agent-service/Dockerfile`

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
```

Add to `gateway/docker-compose.yaml`:
```yaml
  agent-service:
    build: ./agent-service
    container_name: agent-service
    restart: unless-stopped
    ports:
      - "8100:8100"
    volumes:
      - /mnt/nfs/ai-context:/context:ro
      - /opt/agent-service/data:/app/data
    environment:
      - GATEWAY_URL=http://litellm-gateway:4000
      - GATEWAY_KEY=${LITELLM_MASTER_KEY}
```

### Step 11.7 — Alfred integration

**New Alfred workflow:** `workflows/ai-agent/`

Keywords:
- `research {topic}` → POST to agent service
- `taxprep {client}` → POST to agent service
- `interview {company}` → POST to agent service

```bash
#!/bin/bash
# workflows/ai-agent/run_agent.sh
AGENT_TYPE="$1"
TASK="$2"
AGENT_URL="http://192.168.1.52:8100/v1/agent/run"

# Fire and forget — agent sends ntfy when done
curl -s -X POST "$AGENT_URL" \
  -H "Content-Type: application/json" \
  -d "{\"agent\": \"$AGENT_TYPE\", \"task\": \"$TASK\"}" &

echo "Agent '$AGENT_TYPE' started. You'll get a notification when it's done."
```

**Exit criteria:** All 4 Tier 2 agents callable via Alfred. Agent runs logged. Cost ceilings enforced.

---

## S12: Grafana Dashboard + Monitoring (2-3 days)

**Goal:** Observability into gateway operations, costs, routing accuracy.

**Tool:** Claude Code (Grafana provisioning, Prometheus config)

### Step 12.1 — Prometheus SQLite exporter

**File:** `gateway/monitoring/prometheus_exporter.py`

```python
"""
Prometheus exporter — reads SQLite, exposes metrics on :9101.
Scrape interval: 60s.
"""
import sqlite3
import time
from prometheus_client import start_http_server, Gauge, Counter

DB_PATH = "/opt/litellm/data/litellm.db"

# Gauges
daily_cost = Gauge("ai_daily_cost_dollars", "Total API cost today")
local_ratio = Gauge("ai_local_inference_ratio", "Ratio of local vs cloud requests")
escalation_rate = Gauge("ai_escalation_rate", "Escalation rate per alias", ["alias"])
classification_latency_p95 = Gauge("ai_classification_latency_p95_ms", "Classification p95 latency")

# Counters
requests_total = Counter("ai_requests_total", "Total requests", ["alias", "model"])

def collect():
    conn = sqlite3.connect(DB_PATH)
    # ... query SQLite, update metrics
    conn.close()

if __name__ == "__main__":
    start_http_server(9101)
    while True:
        collect()
        time.sleep(60)
```

### Step 12.2 — Prometheus scrape config

```yaml
# Add to Prometheus config on Host C CT 101
scrape_configs:
  - job_name: 'ai-engine'
    static_configs:
      - targets: ['192.168.1.52:9101']
    scrape_interval: 60s
```

### Step 12.3 — Alertmanager rules

```yaml
# New alert rules
groups:
  - name: ai-engine
    rules:
      - alert: GatewayDown
        expr: up{job="ai-engine"} == 0
        for: 2m
        labels: { severity: critical }

      - alert: RouterModelCold
        expr: ai_router_model_loaded == 0
        for: 1m
        labels: { severity: critical }

      - alert: RouterLatencyDegraded
        expr: ai_classification_latency_p95_ms > 1500
        for: 5m
        labels: { severity: warning }

      - alert: EscalationRateHigh
        expr: ai_escalation_rate > 0.25
        for: 1h
        labels: { severity: warning }

      - alert: APICostSpike
        expr: ai_daily_cost_dollars > 10
        labels: { severity: warning }
```

### Step 12.4 — Grafana dashboard JSON

**File:** `gateway/monitoring/grafana-dashboard.json`

Panels:
1. Daily API Spend (time series)
2. Cost Per Alias (bar chart)
3. Local vs. Cloud Split (pie chart, target 60-70% local)
4. Escalation Rate by Alias (time series)
5. Router Confidence Distribution (histogram)
6. Model Latency p50/p95 (time series)
7. Token Usage by Model (stacked bar)

Import via Grafana API or UI.

**Exit criteria:** Dashboard showing live data. All 6 alert rules active.

---

## S13: Music Library Automation (2-3 days)

**Goal:** Overnight batch jobs for FLAC metadata, genre classification, playlists.

**Tool:** Claude Code (n8n workflows)

### Step 13.1 — Music batch processing n8n workflow

```
Cron trigger (daily 2:00 AM)
  → Scan music library for untagged/poorly-tagged FLAC files
  → For each file:
    → Extract existing metadata (ffprobe)
    → POST to gateway (model: "batch-triage")
      Prompt: "Classify genre/mood: {filename, existing tags, audio features}"
      Output: {"genre": str, "mood": str, "confidence": float}
    → Update FLAC metadata via mutagen
  → For new albums:
    → POST to gateway (model: "summarize")
      Prompt: "Generate playlist description for: {album, artist, genre}"
    → Update Navidrome via API
  → Log results to SQLite
  → Integration with music-rec engine (192.168.1.38:8877)
```

All local inference — zero API cost.

**Exit criteria:** Nightly cron running. Metadata improving over time.

---

## S14: Alfred Gateway Workflows + Polish (2-3 days)

**Goal:** Alfred directly queries gateway for multi-model AI, summarize, rewrite.

**Tool:** Claude Code (Alfred workflow scripts)

### Step 14.1 — Multi-model AI workflow

**New workflow:** `workflows/ai-gateway/`

Keywords:
- `ai {query}` — auto-route through gateway
- `code {query}` — direct to code alias
- `analyze {query}` — direct to analyze alias
- `ask {query}` — direct to chat alias (cheap, fast)

```bash
#!/bin/bash
# workflows/ai-gateway/gateway_query.sh
ALIAS="${1:-auto}"
QUERY="$2"
GATEWAY="http://192.168.1.52:4000/v1/chat/completions"
API_KEY=$(grep "LITELLM_MASTER_KEY" ~/.zshrc | tail -1 | cut -d'"' -f2)

RESPONSE=$(curl -s "$GATEWAY" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d "{\"model\": \"$ALIAS\", \"messages\": [{\"role\": \"user\", \"content\": \"$QUERY\"}], \"stream\": false}")

echo "$RESPONSE" | jq -r '.choices[0].message.content // "Error: no response"'
```

### Step 14.2 — Summarize clipboard workflow

- `sum` → read clipboard → POST to gateway (model: "summarize") → copy result to clipboard

### Step 14.3 — Rewrite clipboard workflow

- `rewrite {style}` → read clipboard → POST to gateway (model: "chat") with rewrite prompt → copy result

### Step 14.4 — Run install.sh

```bash
cd /Volumes/NVMe2tbCrucial500/Code/alfred
./install.sh
```

**Exit criteria:** All Alfred → gateway workflows functional. install.sh updated.

---

## Development Tooling Guide

### When to use Claude Code
- **SSH deployment** (S1, S3): Running commands on homelab hosts
- **File creation** (all sprints): Writing Python, YAML, shell scripts
- **Test execution** (S2): Running validation suite, debugging failures
- **Iterative development** (S11): Agent framework code + rapid testing
- **Git operations** (S3): Commits, pushes, repo management

### When to use VS Code / Cursor
- **n8n workflow editing** (S5, S6, S8, S9, S10, S13): n8n's visual editor in the browser is the primary tool; VS Code for editing exported JSON when needed
- **Python debugging** (S11): Step-through debugging the agent loop with breakpoints
- **Grafana dashboard design** (S12): Visual panel arrangement in Grafana UI
- **Large file editing** (S7, S8): Entity validator development with LSP support

### When to use the n8n UI directly
- All workflow building (S5, S6, S8, S9, S10, S13)
- Credential management
- Workflow testing and execution monitoring
- The exported JSON files in the repo are for version control — editing happens in the UI

---

## Dependency Graph

```
S1 (Deploy) ─────→ S2 (Validate) ─────→ S3 (Backup) ─→ S4 (WebUI/CF)
                                                │
                                                ▼
                          S5 (Email) ──→ S6 (Jobs) ──→ S8 (Agents Tier 1)
                              │                            │
                              ▼                            ▼
                          S9 (Notif) ←── S7 (Docs) ──→ S10 (PBC)
                                                           │
                                                           ▼
                                    S11 (Agent Framework) ─→ S14 (Alfred)
                                                           │
                                    S12 (Grafana) ←────────┘
                                                           │
                                    S13 (Music) ←──────────┘
```

**Critical path:** S1 → S2 → S3 → S5 → S8 → S11 → S14

**Parallelizable after S3:**
- S4 (WebUI) can run alongside S5
- S7 (Docs) can run alongside S6
- S12 (Grafana) can start anytime after S2
- S13 (Music) is fully independent after S1

---

## Estimated Timeline

| Week | Sprints | Milestone |
|------|---------|-----------|
| 1 | S1 + S2 | Gateway deployed + validated |
| 2 | S3 + S4 + S5 | Phase 1 complete. Email triage live. |
| 3 | S6 + S7 | Job pipeline + document processing |
| 4 | S8 + S9 | Tier 1 agents + notification filtering |
| 5 | S10 + S11 | PBC + Tier 2 agent framework |
| 6 | S12 + S13 + S14 | Monitoring + music + Alfred polish |

**Total: ~6 weeks to feature-complete.**

---

## Definition of Done (Full Project)

- [ ] Gateway routing all requests through single endpoint
- [ ] All 15 Milestone 2 tests pass
- [ ] 60-70% local inference ratio (Grafana confirmed)
- [ ] Monthly API cost < $100
- [ ] Email triage < 2 min/day manual effort
- [ ] Job pipeline scoring real postings, Things 3 tasks created
- [ ] Documents auto-preprocessed, entity validation live
- [ ] 4 Tier 1 agents (n8n) operational
- [ ] 4 Tier 2 agents (FastAPI) operational and callable from Alfred
- [ ] Notification noise reduced 50%+
- [ ] PBC gap analysis functional
- [ ] Grafana dashboard with all 7 panels + 6 alert rules
- [ ] Music batch processing running nightly
- [ ] All config in git, backups running, recovery tested < 40 min
- [ ] Alfred workflows: ai-gateway, ai-agent, summarize, rewrite
