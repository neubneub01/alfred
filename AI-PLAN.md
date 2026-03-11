**NEUBNEUB HOMELAB**

AI Productivity Engine

Implementation Project Plan

Prepared for: Michael Neuberger

Date: March 2026

Version: 3.2 (Execution Plan)

**CONFIDENTIAL**

---

# **1. Project Objectives**

Transform the homelab into an AI productivity coprocessor that:

1. Routes every AI request through a single intelligent gateway
2. Maximizes local inference utilization (60-70% of requests handled locally)
3. Uses frontier models only when intelligence is required
4. Automates job search, email triage, and document analysis
5. Enables agentic workflows across the environment

**Success means:**

| Metric | Target |
| :---- | :---- |
| Local inference ratio | 60-70% |
| Monthly API cost | < $100 |
| Routed request latency | < 4s |
| Hint-routed request latency | < 2s |
| Classification latency | < 1s |
| Automation hours saved | 10-15/week |

---

# **2. Architecture Overview**

## **Core Design Principle**

Local models are the hands. Frontier models are the brain. The gateway is the dispatcher.

**Local models excel at:** reading, sorting, classifying, formatting, filtering, preprocessing, metadata extraction, notification triage, and structured data output.

**Frontier models excel at:** reasoning, synthesis, long-form analysis, creative writing, complex code generation, nuanced decision-making, and domain expertise.

All clients send requests to one URL:

```
POST http://192.168.1.52:4000/v1/chat/completions
```

The gateway determines: model selection, routing, fallback chain, validation, and logging.

## **Request Flow**

```
Client
 ↓
LiteLLM Gateway (192.168.1.52:4000)
 ↓
Pre-Call Hook
 ├─ Deterministic image check (vision)
 ├─ Alias resolution (hint bypass)
 ├─ Router classification (alias + privacy + confidence)
 ├─ System prompt injection
 └─ Cache control
 ↓
Model Group (primary → fallback chain)
 ↓
Model Response
 ↓
Post-Call Hook
 ├─ Validator (non-streaming only)
 │   ├─ Pass → Return to client
 │   └─ Fail → Escalate once (next model in chain)
 ├─ Escalation logging
 └─ Request logging + cost tracking
```

## **Router Design**

The router classifies incoming prompts with a 3-field output:

```json
{
  "alias": "summarize",
  "privacy": false,
  "confidence": 0.82
}
```

**Why only three fields:** Earlier iterations had 5 axes (task type, complexity, privacy, token estimate, recommended model). Too many decisions for a 4B model. The simplified contract: pick the alias, flag privacy, report confidence. Everything else is handled downstream by model groups and the validation layer.

**Routing behavior:**

| Model Value | Behavior |
| :---- | :---- |
| `"auto"` | Image check → classification → route by alias |
| Alias hint (`"code"`, `"chat"`, etc.) | Skip classification, map to model group |
| Explicit model (`"claude-sonnet-4-6"`) | Pass through, no routing |

**Confidence threshold:** If confidence < 0.55, ignore the alias and default to `chat` (GPT-5 mini) — cheap enough that a misroute costs nothing.

**Two fallback behaviors, two reasons:** Low confidence is treated as **ambiguity** — the router saw the prompt but couldn't decide, so the system chooses the cheapest safe general-purpose alias (`chat` / GPT-5 mini). Router failure (timeout, malformed JSON) is treated as **infrastructure degradation** — the system falls back to a known-reliable default model (`claude-sonnet-4-6`). Ambiguity should be cheap. Failure should be safe.

## **Model Groups (Aliases)**

| Alias | Maps To (Primary) | Cost (In/Out per 1M) | When To Use |
| :---- | :---- | :---- | :---- |
| `code` | Claude Sonnet 4.6 | $3 / $15 | Coding, debugging, code review |
| `analyze` | Claude Opus 4.6 | $5 / $25 | Tax/finance reasoning, complex analysis |
| `agent` | Claude Sonnet 4.6 | $3 / $15 | Multi-step tool-use workflows |
| `long-context` | Gemini 3.1 Pro | $2 / $12 | Documents > 30k tokens |
| `chat` | GPT-5 mini | $0.25 / $2 | Simple conversation, rewriting |
| `summarize` | qwen3.5:9b (5060 Ti) | $0 (local) | Meeting notes, document summaries |
| `batch-triage` | qwen3.5:9b (5060 Ti) | $0 (local) | Classification at scale — email, jobs, alerts |
| `vision` | Gemini 3 Flash | $0.10 / $0.40 | Image/screenshot analysis, OCR |
| `private` | qwen3.5:27b (4090) | $0 (local) | Sensitive data — never leaves LAN |

Each alias carries its full fallback chain. If the primary fails, LiteLLM dispatches to Fallback 1 → Fallback 2 automatically.

## **Routing Rules**

| Task Type | Primary | Fallback 1 | Fallback 2 |
| :---- | :---- | :---- | :---- |
| Coding / debugging | Claude Sonnet 4.6 | GPT-5 | qwen3.5:27b (4090) |
| Deep analysis / reasoning | Claude Opus 4.6 | Gemini 3.1 Pro | qwen3.5:27b (4090) |
| Agent / tool-use loops | Claude Sonnet 4.6 | GPT-5 | qwen3.5:27b (4090) |
| Simple chat / rewriting | GPT-5 mini | Gemini Flash | qwen3.5:9b (5060 Ti) |
| Private / sensitive data | qwen3.5:27b (4090) | qwen3.5:9b (5060 Ti) | N/A — never leaves local |
| Vision / multimodal | Gemini 3 Flash | GPT-5 mini | qwen3.5:9b (5060 Ti) |
| Long context (50k+) | Gemini 3.1 Pro | Claude Sonnet 4.6 | N/A |
| Batch / classification | qwen3.5:9b (5060 Ti) | qwen3.5:27b (4090) | GPT-5 mini |
| Summarization | qwen3.5:9b (5060 Ti) | qwen3.5:27b (4090) | Claude Sonnet 4.6 |

**Privacy policy:** No DeepSeek models in any chain. All private/sensitive data routes stay local.

## **Validation Layer**

Routing picks the cheapest adequate model. Validation verifies the output was adequate. Validators are deterministic — no LLM evaluation, < 50ms, zero cost.

**Principle: Route → Execute → Validate → Escalate if needed.**

| Alias | Validator | Ships With |
| :---- | :---- | :---- |
| `batch-triage` | JSON schema validation (`jsonschema.validate`) | Phase 1 (Gateway) |
| `summarize` | Entity presence (overlap ≥ 60%) | Phase 2 (Document Processing) |
| `code` | Syntax validation (`py_compile`, `node --check`) | Phase 4 (if needed) |
| `analyze` | Optional reasoning structure check | Phase 4 (if needed) |
| `chat` / `vision` | None — interactive streaming bypasses validation | N/A |
| `private` | None — escalation to cloud impossible | N/A |

**Streaming exemption:** Interactive streaming aliases (`chat`, `vision`, most Open WebUI usage) are not protected by post-response validation. Reliability protections apply to unattended non-streaming workflows. Interactive users can see and correct bad output. Batch workflows can't.

### **Escalation Policy**

* **Escalate once only.** Never retry the same model — retries rarely fix capability failures.
* **Escalation chains (canonical):**

| Alias | Chain | Give-Up Behavior |
| :---- | :---- | :---- |
| `batch-triage` | qwen3.5:9b → qwen3.5:27b → GPT-5 mini → fail | Return error to n8n; log raw input for manual review |
| `summarize` | qwen3.5:9b → qwen3.5:27b → fail | Return best attempt + send ntfy alert |
| `code` | (future) Primary → fallback → fail | Return best attempt + flag in logs |

* **Never silently drop data.** Every give-up returns an error or returns the best attempt with an alert.
* **Escalation latency budget:** 10 seconds max for validate-escalate cycle.

## **System Prompts Per Alias**

Each alias injects a system prompt via the pre-call hook. They live in `/opt/litellm/system-prompts.yaml`. The hook checks if the request already has a system message — if yes, don't override (n8n workflows send their own).

**`code`:**
```
You assist with software development. Prefer Python 3.12+ and TypeScript. When writing code, include type hints, handle errors explicitly, and keep functions focused. For infrastructure work, assume a Proxmox/Docker/Linux environment. Be direct — skip preamble, show code first, explain after.
```

**`analyze`:**
```
You are a senior tax and financial analyst. Apply rigorous technical accuracy — cite specific IRC sections, ASC standards, or regulatory guidance when relevant. Structure analysis as: key findings first, supporting detail second, caveats and limitations last. When working with financial data, verify mathematical consistency. Flag assumptions explicitly. Never sacrifice precision for readability.
```

**`agent`:**
```
You are an autonomous agent executing a multi-step workflow. Be efficient with tool calls — plan before acting, batch related operations, and avoid redundant calls. After each tool result, briefly assess whether you have enough information to proceed or need additional data. When the goal is met, stop immediately. Do not summarize unless asked.
```

**`long-context`:**
```
You are processing a large document or codebase. Focus your analysis on the specific question asked — do not attempt to summarize the entire input unless explicitly requested. Reference specific sections, page numbers, or line ranges in your response. Prioritize precision over comprehensiveness.
```

**`chat`:**
```
Be concise and helpful. Match the tone of the request — casual for casual, professional for professional. Keep responses short unless asked for detail.
```

**`summarize`:**
```
Extract the key points from the provided content. Output a structured summary: 1-2 sentence overview, then bullet points for main findings, action items, or decisions. Omit filler, pleasantries, and restated context. Maximum 300 words unless instructed otherwise.
```

**`batch-triage`:**
```
You are a classification engine. Analyze the input and return ONLY valid JSON matching this schema: {"category": string, "priority": 1-5, "confidence": float, "reason": string}. Do not include any text outside the JSON object. Do not explain your reasoning in prose.
```

**`vision`:**
```
You are analyzing an image or screenshot. Describe what you see precisely and answer the user's question about it. For screenshots of UIs, identify elements, text, layout, and state. For documents or photos, extract all visible text and relevant details. For charts or diagrams, describe the data, axes, labels, and trends. Be specific — reference positions (top-left, center, etc.) and quote visible text exactly. Do not speculate about content outside the image boundaries.
```

**`private`:**
```
You are a senior tax and financial analyst. Apply rigorous technical accuracy — cite specific IRC sections, ASC standards, or regulatory guidance when relevant. Structure analysis as: key findings first, supporting detail second, caveats and limitations last. When working with financial data, verify mathematical consistency. Flag assumptions explicitly. Never sacrifice precision for readability. Additionally: all data in this conversation is confidential. Do not suggest uploading to external services, sharing via cloud tools, or referencing third-party platforms. All work products stay local.
```

## **Prompt Caching**

| Provider | Mechanism | Savings |
| :---- | :---- | :---- |
| Anthropic (Claude) | `cache_control: {"type": "ephemeral"}` on system prompt | 90% off system prompt tokens |
| OpenAI (GPT-5) | Automatic for repeated prefixes | 50% off cached input |
| Google (Gemini) | Context caching API | Varies |
| Ollama (local) | KV cache via `OLLAMA_KEEP_ALIVE=60m` | N/A (free) |

---

# **3. Infrastructure Topology**

## **Hardware Allocation**

| Node | IP | Hardware | GPU | Primary Role |
| :---- | :---- | :---- | :---- | :---- |
| Host A (neubneub) | 192.168.1.188 | i9-13900K, 128 GB RAM | RTX 4090 (24 GB) | Heavy local inference — qwen3.5:27b |
| Host B (neub) | 192.168.1.166 | Ryzen 9 9950X, 96 GB RAM | RTX 3070 (8 GB) | Router — qwen3.5:4b + embeddings |
| Host C (neub3) | 192.168.1.22 | Ryzen 9 7900, 64 GB RAM | RTX 5060 Ti (16 GB) | Gateway + batch — qwen3.5:9b |
| Windows PC | 192.168.1.70 | Ryzen 7 9800X3D, 96 GB RAM | RTX 5080 (16 GB) | Toggle-on burst: qwen3.5:27b |
| MacBook M4 Pro | Tailscale | Apple M4 Pro, 48 GB unified | — | Toggle-on burst: qwen3.5:9b |

**Total GPU VRAM (always-on):** 48 GB

## **GPU Budget**

### RTX 3070 (8 GB) — Host B LXC 501 — Router

| Allocation | VRAM | Status |
| :---- | :---- | :---- |
| Qwen3.5 4B (Q4_K_M) | ~2.5 GB | Always loaded |
| nomic-embed-text (768-dim) | ~0.6 GB | Always loaded |
| CUDA / Ollama overhead | ~1 GB | Always loaded |
| Available headroom | ~3.9 GB | KV cache buffer |

### RTX 4090 (24 GB) — Host A LXC 101 — Primary Compute

| Allocation | VRAM | Status |
| :---- | :---- | :---- |
| Qwen3.5 27B (Q4_K_M) | ~16 GB | Primary model, 60m keep-alive |
| CUDA / Ollama overhead | ~1 GB | Always loaded |
| Available for on-demand | ~7 GB | Can run smaller models alongside |
| Tdarr NVENC | Dedicated silicon | Shared (separate silicon) |

VRAM gate service on port 11435: returns 503 when GPU > 90%, triggering failover.

### RTX 5060 Ti (16 GB) — Host C LXC 100 — Secondary Compute

| Allocation | VRAM | Status |
| :---- | :---- | :---- |
| Qwen3.5 9B (Q4_K_M) | ~5.5 GB | Primary model |
| CUDA / Ollama overhead | ~1 GB | Always loaded |
| Available headroom | ~9.5 GB | Concurrent models or Speaches |

### Burst Capacity (Toggle-On/Off)

The Windows PC and MacBook are not always-on. Ollama defaults to off. A toggle starts the service; LiteLLM's health check picks it up automatically (lowest-priority fallback). When off, LiteLLM skips the dead backend silently.

**Verification required:** Test that LiteLLM gracefully skips unhealthy backends with zero error propagation and no added latency. If it probes per-request adding seconds, implement a health-check sidecar (cron every 30s) instead.

## **Network Architecture**

| Endpoint | URL | Protocol |
| :---- | :---- | :---- |
| Gateway (LAN) | http://192.168.1.52:4000/v1/chat/completions | OpenAI-compatible API |
| Gateway (Cloudflare) | https://ai-gateway.neubneub.com/v1/chat/completions | Identity-gated |
| Open WebUI | https://ai.neubneub.com | Web chat interface |

## **Service Endpoints**

| Service | Internal URL | Host |
| :---- | :---- | :---- |
| AI Gateway | 192.168.1.52:4000 | Host C LXC 102 |
| Ollama (4090) | 192.168.1.220:11434 | Host A LXC 101 |
| Ollama (4090 VRAM gate) | 192.168.1.220:11435 | Host A LXC 101 |
| Ollama (3070) | 192.168.1.41:11434 | Host B LXC 501 |
| Ollama (5060 Ti) | 192.168.1.50:11434 | Host C LXC 100 |
| Open WebUI | 192.168.1.220:3000 | Host A LXC 101 |
| n8n | 192.168.1.52:5678 | Host C LXC 102 |
| Qdrant | 192.168.1.38:6333 | Host B LXC 201 |
| Grafana | 192.168.1.51:3000 | Host C CT 101 |
| Prometheus | 192.168.1.51:9090 | Host C CT 101 |
| Alertmanager | 192.168.1.51:9093 | Host C CT 101 |
| ntfy | 192.168.1.38:8090 | Host B LXC 201 |
| Paperless-ngx | 192.168.1.221:8000 | Host A CT 102 |
| Speaches (Whisper) | 192.168.1.22:8000 | Host C bare metal |
| Agent Service | 192.168.1.52:8100 | Host C LXC 102 |
| llama.cpp RPC worker | 192.168.1.220:50052 | Host A LXC 101 |

---

# **4. Implementation Phases**

| Phase | Duration | Outcome |
| :---- | :---- | :---- |
| Phase 1 | Week 1-2 | Gateway operational, validated, backed up |
| Phase 2 | Week 3-4 | Email, job search, document processing live |
| Phase 3 | Week 5-6 | Notifications, PBC, Tier 1 agents complete |
| Phase 4 | Week 7+ | Optimization, music, Tier 2 evaluation |

---

## **PHASE 1: Foundation**

**Duration:** 1-2 weeks

**Goal:** Deploy the AI gateway, validate it under stress, establish version control and backup.

---

### **Milestone 1: Gateway Infrastructure**

**Deliverables:** LiteLLM proxy, routing logic, classification system, validation, logging layer.

#### Task 1.1 — Deploy LiteLLM Proxy

**Host:** Host C LXC 102 (192.168.1.52)

```bash
docker run -d \
  -p 4000:4000 \
  -v /opt/litellm:/app/config \
  litellm/litellm
```

#### Task 1.2 — Configure Model Groups

**Create:** `/opt/litellm/config.yaml`

Define all 9 aliases, fallback chains, provider API keys, local Ollama endpoints, and per-alias token budget limits:
* Default: `max_input_tokens: 100000`, `max_output_tokens: 8192`
* `long-context`: `max_input_tokens: 500000`
* `agent`: `max_output_tokens: 16384`

Token limits prevent runaway prompts from agent loops and context-loader injections.

#### Task 1.3 — Configure Router Model

**Host:** Host B LXC 501 (192.168.1.41:11434)

```bash
ollama pull qwen3.5:4b
```

Set `OLLAMA_KEEP_ALIVE=60m` and `OLLAMA_KV_CACHE_TYPE=q4_0`.

Verify permanently loaded:

```bash
ollama ps  # must show qwen3.5:4b
```

Router must **never** unload.

#### Task 1.4 — Write Classification Prompt

**Create:** `/opt/litellm/classification-prompt.txt`

Output schema: `{"alias": string, "privacy": bool, "confidence": float}` — 9 alias classes + binary privacy flag + confidence score. If confidence < 0.55, the hook ignores the alias and defaults to `chat`.

#### Task 1.5 — Implement Pre-Call Hook

**Create:** `/opt/litellm/hooks/pre_call.py`

Five stages executed in sequence, with `PipelineHealth` tracking:

1. **Deterministic image check** — scan message array for `image_url` or base64 `data:image/`. If found, route to `vision`. Pure string matching, zero cost.
2. **Alias resolution** — if model is a hint alias, map to primary model.
3. **Classification** — if model is `auto`, call Qwen3.5 4B. Apply confidence threshold.
4. **System prompt injection** — inject alias default from YAML if no system message present.
5. **Cache control** — add `cache_control: {"type": "ephemeral"}` for Anthropic requests.

Every stage reports success/failure to the health object with severity (LOW/MEDIUM/HIGH) and human-readable impact statement.

**Pipeline Health Tracking:**

```python
@dataclass
class StageResult:
    stage: str
    failed: bool = False
    severity: Severity = Severity.LOW
    error: str = ""
    impact: str = ""

@dataclass
class PipelineHealth:
    results: list[StageResult] = field(default_factory=list)
    request_id: str = ""

    def record_failure(self, stage: str, severity: Severity, error: str, impact: str):
        self.results.append(StageResult(
            stage=stage, failed=True, severity=severity,
            error=str(error), impact=impact
        ))

    def record_success(self, stage: str):
        self.results.append(StageResult(stage=stage))
```

**Classification with confidence:**

```python
CONFIDENCE_THRESHOLD = 0.55

async def _classify_request(data: dict, health: PipelineHealth) -> dict:
    try:
        result = await _call_router_model(data)
        alias = result["alias"]
        confidence = result.get("confidence", 0.0)
        if result.get("privacy"):
            alias = "private"
        elif confidence < CONFIDENCE_THRESHOLD:
            alias = "chat"
        data["model"] = ALIAS_MAP[alias]["primary"]
        data["_alias"] = alias
        data["_confidence"] = confidence
        data["_routed_by"] = "classifier"
        health.record_success("classification")
        return data
    except asyncio.TimeoutError:
        data["model"] = DEFAULT_MODEL  # claude-sonnet-4-6
        health.record_failure(
            stage="classification",
            severity=Severity.MEDIUM,
            error="Router model timed out (>3s)",
            impact=f"Falling back to {DEFAULT_MODEL}"
        )
        return data
```

**Final safety net in main hook:** If model is still `"auto"` after all stages → HIGH severity, hardcode default.

**Health reporting escalation rules:**
1. Any HIGH severity → notify immediately
2. Same stage fails 5+ times consecutively → persistent issue alert
3. 3+ stages fail on one request → systemic degradation alert
4. 5-minute cooldown per stage to prevent notification storms
5. Counter resets on success — only persistent failures escalate

#### Task 1.6 — Implement Post-Call Hook

**Create:** `/opt/litellm/hooks/post_call.py`

Responsibilities:
* **Validation dispatch** — run alias-specific validator on non-streaming responses
* **Escalation** — on validation failure, re-dispatch to next model in fallback chain (once only)
* **Request logging** — every request: timestamp, request ID, client, original model, resolved model, alias, confidence, tokens, latency, cost, validation status
* **Escalation logging** — dedicated table: original model, escalation target, validator trigger, tokens for both attempts, total latency

The escalation log is the primary tuning signal. "qwen9B summarize → escalates 35% of the time" tells you to route summarize to 27B directly.

#### Task 1.7 — Implement Batch-Triage Validator

**This ships with the gateway — Phase 1, not deferred.**

Every email triage, job scoring, and notification filtering workflow depends on structured JSON. Malformed JSON = silent data loss.

```python
TRIAGE_SCHEMA = {
    "type": "object",
    "required": ["category", "priority", "confidence", "reason"],
    "properties": {
        "category": {"type": "string"},
        "priority": {"type": "integer", "minimum": 1, "maximum": 5},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reason": {"type": "string"}
    },
    "additionalProperties": False
}

def validate_triage(output: str) -> bool:
    try:
        data = json.loads(output)
        jsonschema.validate(data, TRIAGE_SCHEMA)
        return True
    except (json.JSONDecodeError, jsonschema.ValidationError):
        return False
```

On failure: escalate per alias fallback chain (see Escalation Policy in section 2).

#### Task 1.8 — Write System Prompts

**Create:** `/opt/litellm/system-prompts.yaml`

All 9 alias prompts (see section 2). Pre-call hook loads on startup, injects per-alias.

#### Task 1.9 — Configure SQLite Logging

**Create:** `/opt/litellm/data/litellm.db`

Tables: `requests`, `classifications`, `escalations`, `feedback`

#### Task 1.10 — Configure Open WebUI

Point to gateway: `http://192.168.1.52:4000`

#### Task 1.11 — Configure Cloudflare Tunnel

Route `ai-gateway.neubneub.com` → `192.168.1.52:4000`

#### Task 1.12 — Add Classification Feedback

Open WebUI thumbs up/down logs back to classification record in SQLite, linking user satisfaction to the model the router picked.

---

### **Milestone 2: Validation Sprint**

**Duration:** 2-3 days, dedicated

**Purpose:** Break the gateway intentionally. Prove every failure mode is handled.

#### Validation Tests

| # | Test | Pass Criteria |
| :---- | :---- | :---- |
| 1 | Health check — offline backend | Toggle Ollama off on burst machine. Zero added latency, zero error propagation. |
| 2 | Health check — backend comes online | Toggle back on. Joins pool within 60s, no restart. |
| 3 | Fallback chain activation | Kill Host A Ollama, then Host C. Client gets response from deepest fallback. |
| 4 | Streaming through proxy | Stream from each backend type. No drops, no buffering artifacts. |
| 5 | Pre-call hook error handling | Stop router model. Hook falls back to `claude-sonnet-4-6` within 3s. |
| 6 | Pre-call hook — malformed JSON | Corrupt classification prompt. Hook catches parse error, falls back, logs raw output. |
| 7 | Classification latency under load | 10 concurrent `auto` requests. p95 < 1.5s (target 300-800ms). |
| 8 | Low-confidence routing | Ambiguous prompt. Router returns confidence < 0.55. Hook routes to `chat`. |
| 9 | Deterministic image routing | Multimodal `image_url` payload. Rewrites to `vision` without calling classifier. |
| 10 | Alias routing | All 9 aliases map to correct model. System prompt injected/skipped correctly. |
| 11 | Cost logging | 20 mixed requests. Every row has timestamp, model, tokens, cost. No gaps. |
| 12 | VRAM gate | Saturate 4090. Port 11435 returns 503. Falls back to 5060 Ti. |
| 13 | Pipeline health escalation | Stop router. 6+ requests. ntfy fires after 5th failure. Cooldown prevents repeat. |
| 14 | Batch-triage validation | Valid JSON passes. Malformed triggers escalation to 27B. Both logged. |
| 15 | Validation escalation chain | Force 9B and 27B to both return invalid JSON. Chain walks: 9B → 27B → GPT-5 mini. |

#### Performance Targets

| Metric | Target |
| :---- | :---- |
| Classification latency (p95) | < 1s |
| Routed request (end-to-end) | < 4s |
| Hint-routed request | < 2s |
| Validation-escalation cycle | < 10s |

#### Exit Criteria

All 15 tests pass. No exceptions, no "good enough."

---

### **Milestone 3: Version Control + Backup**

#### Git Configuration

Initialize `/opt/` as Git-tracked directory, push to homelab repo.

**Tracked files:**

| File | Path | Contents |
| :---- | :---- | :---- |
| LiteLLM config | `/opt/litellm/config.yaml` | Model groups, fallback chains, alias definitions |
| System prompts | `/opt/litellm/system-prompts.yaml` | All 9 alias system prompts |
| Classification prompt | `/opt/litellm/classification-prompt.txt` | Qwen3.5 4B router prompt |
| Pre-call hook | `/opt/litellm/hooks/pre_call.py` | Classification, image detection, prompt injection, caching |
| Post-call hook | `/opt/litellm/hooks/post_call.py` | Logging, validation, escalation |
| Validators | `/opt/litellm/validators/` | Batch-triage schema, entity validator, future validators |
| Tool registry | `/opt/agent-service/tools.yaml` | Tool definitions, JSON schemas, `shell_exec` whitelist |
| Agent definitions | `/opt/agent-service/agents.yaml` | Persona prompts, tool allowlists, limits |
| Agent service | `/opt/agent-service/` | FastAPI app, Dockerfile, requirements.txt |
| Docker Compose | `/opt/docker-compose.yaml` | Container definitions |
| n8n workflows | `/opt/n8n/workflows/` | JSON exports of all AI workflows |

**Rule: if it's not in git, it doesn't exist in production.**

#### Config Snapshot Cron (every 6 hours)

```bash
cd /opt || exit 1
git add -A
if ! git diff --cached --quiet; then
  git commit -m "auto: config snapshot $(date +%Y-%m-%d_%H:%M)"
  git push
fi
```

#### Nightly SQLite Backup (2:00 AM)

```bash
#!/bin/bash
BACKUP_DIR="/mnt/nfs/backups/ai-engine/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"
sqlite3 /opt/litellm/data/litellm.db ".backup '$BACKUP_DIR/litellm.db'"
sqlite3 /opt/agent-service/data/agents.db ".backup '$BACKUP_DIR/agents.db'"
sqlite3 /home/node/.n8n/database.sqlite ".backup '$BACKUP_DIR/n8n.db'"
find /mnt/nfs/backups/ai-engine/ -maxdepth 1 -mtime +30 -exec rm -rf {} +
```

**Storage:** Host B NFS (`/mnt/nfs/`) on ZFS `tank` with daily snapshots. 30-day retention on rolling backups, ZFS snapshots handle the long tail.

**n8n workflow export:** n8n stores workflows in its internal database. Build an n8n meta-workflow that exports all workflow JSONs via API (`GET /api/v1/workflows/{id}`) to `/opt/n8n/workflows/` on a daily schedule.

#### Recovery Test

**Before moving to Phase 2:** Destroy LXC 102. Rebuild from backups.

| Step | Action | Time |
| :---- | :---- | :---- |
| 1 | Create new LXC from Proxmox template | 5 min |
| 2 | Install Docker, clone homelab repo | 5 min |
| 3 | Copy `/opt/` config from repo, set API key env vars | 5 min |
| 4 | `docker compose up -d` — LiteLLM + agent service | 2 min |
| 5 | Install n8n, restore database from NFS backup | 10 min |
| 6 | Restore SQLite databases from NFS backup | 2 min |
| 7 | Verify: gateway routing, n8n workflows, agent health | 10 min |
| **Total** | **Full recovery from zero** | **< 40 min** |

**What survives without Host C:** Ollama on Host A and B continues. Open WebUI can point directly at Ollama for basic local inference. System degrades to "local models only, manual routing."

**What is NOT recoverable without backups:** Classification tuning feedback, agent run history, n8n execution logs. Losing them means restarting the tuning period.

#### Exit Criteria

Git repo initialized with all config. Nightly backup running. Recovery test passes under 40 minutes.

---

### **Phase 1 Exit Criteria**

Gateway operational. All 15 validation tests pass. Config in git. Backups running. Recovery tested. Only then does Phase 2 begin.

---

## **PHASE 2: High-Impact Productivity**

**Duration:** 2 weeks

**Goal:** Automate job search, email triage, and document processing.

---

### **Milestone 4: Email Triage System**

| Field | Value |
| :---- | :---- |
| Workflow Engine | n8n (192.168.1.52:5678) |
| Inference | qwen3.5:9b (192.168.1.50:11434) — async batch |
| Integration | Fastmail JMAP → n8n → Ollama → Fastmail labels |

#### Workflow

```
Fastmail (JMAP)
     ↓
n8n trigger (new email)
     ↓
qwen3.5:9b classification
     ↓
Fastmail labels/folders
```

#### Classification Output

```json
{"category": "string", "priority": 1-5, "confidence": 0.0-1.0, "reason": "string"}
```

Uses `batch-triage` alias → validated by JSON schema validator (already deployed in Phase 1).

#### Categories

| Category | Action | Priority |
| :---- | :---- | :---- |
| Recruiter (matching) | Flag + Job Search folder | Immediate |
| Interview scheduling | Flag + extract times + calendar hold | Immediate |
| Recruiter (non-matching) | Tag low-priority, archive | Low |
| Newsletters | Auto-archive | None |
| Transactional | Auto-label | None |
| Personal | Leave in inbox | Normal |
| Actionable | Flag + Action Required folder | High |
| Spam | Auto-archive | None |

#### Tasks

1. Configure Fastmail JMAP API in n8n. Expect to use HTTP Request nodes hitting JMAP directly for reliable folder moves and labeling.
2. Build n8n workflow: new email trigger → extract subject/sender/preview → classify via gateway (`batch-triage`) → label/move
3. Write classification prompt with synonym lists and example patterns for tax provision roles ("income tax," "ASC 740," "tax accounting," "tax compliance")
4. **Cold-start risk:** Recruiter language is inconsistent. Build prompt with synonym lists, not keyword matching. Expect meaningful false-negative rate initially.
5. Test with 4 weeks of real email. Manually review all "actionable" flags and all "auto-archived" for the first month.

#### Exit Criteria

Inbox requires < 2 minutes/day manual triage.

---

### **Milestone 5: Job Search Automation**

#### Data Sources

Phase 1 sources:
* LinkedIn email alerts (forwarded to Fastmail, parsed by n8n)
* Target company career pages (scraped or RSS)

**Source fragility warning:** LinkedIn alerts change format periodically. Indeed public search is rate-limited. Prioritize in order of reliability: (1) company career pages, (2) Indeed Partner API (if available), (3) Google Jobs API, (4) LinkedIn email alerts as a workaround (not scraping).

#### Pipeline

```
job source
     ↓
n8n extraction
     ↓
qwen3.5:9b scoring (batch-triage)
     ↓
ranked list
     ↓
Things 3 task (>60) / Application Pipeline (>80)
```

#### Scoring Model

| Factor | Weight | Signal |
| :---- | :---- | :---- |
| ASC 740 / tax provision focus | 25% | Explicit mention of income tax provision, deferred tax, ASC 740 |
| Team size / structure | 20% | Established team, manager role, team of 5+ |
| M&A / transaction exposure | 15% | Deal-related tax, due diligence, transaction |
| Tech stack / automation | 15% | Modern tools, automation focus, data analytics |
| Location | 10% | Remote/hybrid in target metros |
| Seniority match | 10% | Manager/Senior Manager level |
| Company stability | 5% | Public, established, non-startup |

#### Automation

* Score > 80: Trigger Job Application Pipeline agent
* Score 60-80: Create Things 3 task for manual review
* Score < 60: Log, skip

#### Exit Criteria

Job pipeline running with real postings. Application materials auto-drafted for high-match jobs.

---

### **Milestone 6: Document Processing**

| Field | Value |
| :---- | :---- |
| Inference | qwen3.5:27b (4090) or qwen3.5:9b (5060 Ti) for extraction |
| Ingestion | Paperless-ngx (192.168.1.221:8000) for OCR |
| Integration | Upload → OCR → preprocess → condensed context → frontier model |

#### Pipeline

```
document upload
     ↓
Paperless-ngx OCR
     ↓
local model classification + summarization
     ↓
frontier model analysis (with condensed context)
```

#### Document Types

| Type | Preprocessing | Frontier Task |
| :---- | :---- | :---- |
| Tax returns (1120, 1065, 1040) | Extract schedules, income, entity info | ASC 740 analysis |
| Financial statements | Extract P&L, BS, ratios | Trend analysis |
| Engagement letters / SOWs | Extract scope, timeline, fees | Review, redline |
| Legal agreements | Extract parties, terms, dates | Risk analysis |
| GL exports / trial balances | Normalize, identify key accounts | M-1/M-3 mapping |

**Chunking mandate:** Summarization must reduce input to < 5k tokens before hitting frontier. If still > 30k after summarization, route to Gemini Pro (1M context).

#### Entity Presence Validator

**Ships with Milestone 6 — protects downstream frontier analysis.**

```python
def extract_entities(text: str) -> Set[str]:
    entities = set()
    entities.update(re.findall(r'\$[\d,.]+', text))
    entities.update(re.findall(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b', text))
    entities.update(re.findall(r'\b[A-Z][a-z]+ (?:[A-Z][a-z]+ ?)+', text))
    return entities

def validate_summary(summary: str, original: str, threshold: float = 0.6) -> bool:
    original_entities = extract_entities(original)
    if not original_entities:
        return True
    summary_entities = extract_entities(summary)
    overlap = len(original_entities & summary_entities) / len(original_entities)
    return overlap >= threshold
```

On failure: escalate to qwen3.5:27b. If 27B also fails, return best attempt + ntfy alert.

#### Tasks

1. Configure Paperless-ngx API access for n8n
2. Build classification prompt: identify type, extract metadata
3. Build summarization prompt: condense to < 5k tokens structured content
4. Build n8n workflow: Paperless webhook → extract text → classify → preprocess → store
5. Deploy entity presence validator
6. Test with real tax workpapers, engagement letters, financial statements

#### Exit Criteria

Documents preprocessed before frontier analysis. Frontier token usage reduced 70-90% vs raw input. Entity validator catching dropped figures/names.

---

### **Phase 2 Additional Tasks**

* **Context Loader:** Populate `career/` and `tax-reference/` folders on NFS (`/mnt/nfs/ai-context/`)
* **Tier 1 Agent: Job Application Pipeline** (triggered by Milestone 5 scores > 80)
* **Tier 1 Agent: Email Response Drafter** (triggered by Milestone 4 "actionable" classification)
* **Burst capacity test:** Verify LiteLLM health check behavior with Windows PC / MacBook

---

## **PHASE 3: Workflow Expansion**

**Duration:** 2 weeks

**Goal:** Reduce noise, enhance operations, complete Tier 1 agent coverage.

---

### **Milestone 7: Smart Notification Filtering**

#### Input Sources

* Prometheus / Alertmanager
* n8n workflow events
* Blackbox Exporter
* Docker / Proxmox events

#### Scoring

| Source | Signal (notify 4-5) | Noise (log 1-3) |
| :---- | :---- | :---- |
| Prometheus | Service down > 5 min, disk > 85%, GPU temp > 85C | Transient CPU spikes, brief latency |
| n8n | Workflow failure, job match found, high-priority email | Successful routine runs |
| Blackbox | Tunnel endpoint down, HTTP 5xx | Occasional slow response |
| Docker/Proxmox | Critical container crashed, LXC stopped | Watchtower update, scheduled restart |

Score 4-5 → push to ntfy. Score 1-3 → log to SQLite only. Time-of-day weighting.

---

### **Milestone 8: PBC Document Sorting**

#### Pipeline

```
document upload
     ↓
classification against PBC template
     ↓
PBC category assignment
     ↓
folder routing
     ↓
gap analysis report
```

Output: Missing PBC items report + Things 3 tasks for outstanding items.

---

### **Phase 3 Additional Tasks**

* **Context Loader:** Populate `templates/` and `homelab/` folders
* **Tier 1 Agent: Document Analysis Pipeline** (chains Milestone 6 + context loader + Paperless-ngx)
* **Tier 1 Agent: Weekly Digest** (cron Sunday 8 PM)
* **Router optimization:** Tune classification prompt based on collected data, review feedback logs

---

## **PHASE 4: Optimization & Agents**

**Duration:** Ongoing

**Goal:** Batch processing, validation expansion, agent framework, local-first cascades.

---

### **Milestone 9: Music Library Automation**

Batch jobs (all local, zero API cost):
* Metadata correction for untagged FLAC files
* Genre classification via local model
* Playlist description generation for Navidrome
* Integration with music-rec engine (192.168.1.38:8877)

Schedule as overnight n8n cron.

---

### **Milestone 10: Agent Framework**

#### Two Tiers

| Tier | Runtime | Loop Control | When To Use |
| :---- | :---- | :---- | :---- |
| **Tier 1** | n8n workflows | Hardcoded branches | Steps known in advance |
| **Tier 2** | Python FastAPI | Model decides | Dynamic reasoning required |

#### Tool Registry

| Tool | Endpoint | What It Does |
| :---- | :---- | :---- |
| `gateway_chat` | 192.168.1.52:4000 | Send prompt to gateway |
| `context_load` | Local filesystem | Load markdown from context folder |
| `paperless_search` | 192.168.1.221:8000 | Search Paperless-ngx |
| `paperless_download` | 192.168.1.221:8000 | Download document text |
| `paperless_tag` | 192.168.1.221:8000 | Update tags/metadata |
| `fastmail_search` | JMAP via n8n | Search emails |
| `fastmail_draft` | JMAP via n8n | Create draft email |
| `fastmail_label` | JMAP via n8n | Apply labels/move |
| `things_create` | URL scheme | Create Things 3 task/project |
| `things_search` | AppleScript bridge | Search Things 3 |
| `ntfy_send` | 192.168.1.38:8090 | Push notification |
| `n8n_webhook` | 192.168.1.52:5678 | Trigger n8n workflow |
| `web_search` | Via gateway or SearXNG | Web search |
| `shell_exec` | Whitelisted commands only | Diagnostic commands |

#### Context Loader (Replaces RAG)

| Folder | Path | Contents |
| :---- | :---- | :---- |
| `career` | `/mnt/nfs/ai-context/career/` | Resume variants, STAR stories, engagement summaries |
| `tax-reference` | `/mnt/nfs/ai-context/tax-reference/` | ASC 740 guidance, M-1/M-3 items, PBC checklists |
| `homelab` | `/mnt/nfs/ai-context/homelab/` | Architecture, node inventory, troubleshooting |
| `templates` | `/mnt/nfs/ai-context/templates/` | Engagement letters, PBC lists, workpaper formats |

Why this works: collections are small, curated, rarely change, fit in a single context window. Editing means updating a markdown file — no re-embedding, no chunk boundaries, no retrieval tuning.

#### Tier 1 Agents (n8n — No New Infrastructure)

**Job Application Pipeline:** Module 5 scores > 80 → context_load(career) → analyze job → draft cover letter → tailor resume bullets → create Things 3 project → draft email → notify

**Document Analysis Pipeline:** Paperless webhook → download → classify → tag → load context → deep analysis via Claude → notify

**Email Response Drafter:** "Actionable" email → retrieve thread → load career context → draft response → save draft → create Things task → notify

**Weekly Digest:** Cron Sunday 8 PM → aggregate n8n logs, LiteLLM metrics, Fastmail stats, Paperless-ngx counts → summarize → notify

#### Tier 2 Agent Service (Deferred — Phase 4+)

**Build signal:** Tier 1 n8n workflows hit these walls: (1) 10+ conditional paths, (2) next steps unpredictable at design time, (3) meta-workflows orchestrating other workflows. Until then, Tier 1 covers the need.

**Service:**
* Python 3.12 + FastAPI on Host C LXC 102, port 8100
* Single endpoint: `POST /v1/agent/run`
* All LLM calls route through the gateway

**Safety Constraints:**
* Max iterations: default 10, hard cap 25
* Tool allowlists per agent
* `shell_exec` command whitelist (not sandbox): `curl -s`, `docker ps`, `docker logs --tail`, `df -h`, `free -m`, `nvidia-smi`, `systemctl status`, `ping -c`, `cat /proc/`
* Per-run cost ceiling: $2
* Aggregate daily cost breaker: $15
* Context budget: summarize history at 80% window capacity

**Agents:**
* **Research** — Alfred `research {topic}` → systematic search → synthesize → notify
* **Tax Prep** — `taxprep {client}` → load PBC template → find docs → gap analysis → draft follow-up
* **Interview Prep** — `interview {company}` → load career context → research company → map STAR stories → generate questions → create prep project
* **Homelab Troubleshooter** — Alertmanager → parse alert → load homelab docs → diagnostics → correlate → recommend fix

**Alfred Integration:**
* `research {topic}` → Research agent
* `taxprep {client}` → Tax Prep agent
* `interview {company}` → Interview Prep agent
* `analyze {query}` → Document Analysis Pipeline (Tier 1)

---

### **Phase 4 Additional Tasks**

* **Validation expansion:** Review escalation logs. Add `code` syntax validator if escalation rate is high. Only add validators that earn their keep.
* **Local-first cascade evaluation:** For aliases where qwen3.5:27b escalation rate < 15%, switch primary from cloud to local with cloud as validation-failure escalation. Pattern: `code → qwen27B → [validate] → pass? return : escalate → Claude Sonnet`. **Only after validators are stable.** Potential 30-50% additional API savings.
* **Job search expansion:** Google Jobs API, Indeed Partner API, additional career pages
* **Deploy Grafana cost dashboard**

---

# **5. Monitoring & Observability**

## **Existing Stack**

* **Prometheus:** 47 scrape targets, 15-60s intervals
* **Alertmanager:** 14 alert rules, 4 groups
* **Blackbox Exporter:** 20 LAN + 13 Cloudflare endpoints
* **Grafana:** Endpoint Health, Node Exporter Full, NVIDIA GPU Metrics
* **Alert delivery:** Alertmanager → ntfy (192.168.1.38:8090/homelab-alerts)

## **New AI Engine Alerts**

| Alert | Trigger | Severity |
| :---- | :---- | :---- |
| Gateway Down | LiteLLM health endpoint unreachable > 2 min | Critical |
| Router Model Cold | qwen3.5:4b not loaded (Ollama `api/ps`) | Critical |
| Router Latency Degraded | Classification p95 > 1.5s | Warning |
| Escalation Rate High | Any alias > 25% over 1-hour window | Warning |
| API Cost Spike | Daily spend > $10 | Warning |
| Pipeline Health | 5+ consecutive same-stage failures or 3+ stages on single request | Warning |

## **Router Cold-Start Watchdog**

The router model must never unload. Cold load adds 3-5s to every classified request. Watchdog checks: (1) Ollama `api/ps` confirms model loaded, (2) classification p95 < 1.5s. Cold router is Critical, not Warning.

## **Escalation Rate Monitoring**

Prometheus metric `ai_escalation_rate{alias}` from escalation log. > 25% indicates: model capability mismatch, validator too strict, or router misclassification.

## **Cost & Usage Dashboard (Grafana)**

| Panel | Data Source | Purpose |
| :---- | :---- | :---- |
| Daily API Spend | SQLite cost log | Catch billing spikes |
| Cost Per Alias | SQLite cost log | Identify expensive aliases |
| Local vs. Cloud Split | SQLite request log | Track 60-70% local target |
| Escalation Rate by Alias | SQLite escalation log | Validator/routing trend |
| Router Confidence Distribution | SQLite classification log | Prompt ambiguity signal |
| Model Latency (p50/p95) | SQLite request log | Catch degradation |
| Token Usage by Model | SQLite request log | Spot runaway prompts |

**Implementation:** SQLite → Prometheus via Python exporter sidecar (60s scrape), or Grafana SQLite plugin.

---

# **6. Cost Model**

| Category | Estimated Monthly | Notes |
| :---- | :---- | :---- |
| Anthropic (Claude) | $20-$60 | Coding, analysis, reasoning |
| OpenAI (GPT-5) | $3-$10 | Chat alias + fallback |
| Google (Gemini) | $2-$12 | Vision (Flash), long context (Pro) |
| Local (electricity) | $8-$15 | 3 GPUs, mostly idle |
| Fastmail | $5 | Already paid |
| Prompt caching savings | -$3-$8 | 90% off Anthropic, 50% off OpenAI |
| **Total** | **$35-$92/month** | |

**Savings vs cloud-only:** 50-65%. Four mechanisms:

1. `chat`, `summarize`, `batch-triage`, `vision` aliases → 40-50% of volume to free/near-free inference
2. Deterministic vision routing → Gemini Flash ($0.10/$0.40) instead of frontier tokens
3. Prompt caching → 90% off Anthropic system prompts, 50% off OpenAI
4. Classifier routes remaining `auto` requests to cheapest adequate model

Validation adds minimal cost (deterministic checks) while preventing the costliest failure: misrouted batch jobs producing garbage that triggers expensive rework.

---

# **7. Risk Management**

| Risk | Probability | Impact | Mitigation |
| :---- | :---- | :---- | :---- |
| Router model unloads | Low | High — 3-5s per classified request | `OLLAMA_KEEP_ALIVE=60m` + cold-start watchdog alert |
| Classification errors | Medium | Medium — wrong model selected | Confidence threshold (< 0.55 → `chat`), alias hints bypass router, validation catches downstream |
| Model produces invalid output | Medium | High for batch workflows | Deterministic validators + escalation chains |
| API cost spike | Low | Medium | $15/day agent breaker, $10/day alert, per-alias token limits |
| Gateway failure (LXC 102) | Low | High — all routing stops | < 40 min rebuild from backups, system degrades to local-only |
| Fastmail JMAP instability | Medium | Low — email triage pauses | n8n retry logic, manual fallback |
| Job search source changes | High | Medium — scoring pipeline breaks | Prioritize reliable sources, monitor for format changes |
| Context loader files stale | Medium | Low — outdated context | Review schedule, version control context folders |

---

# **8. Final Success Metrics**

| Metric | Target | Measurement |
| :---- | :---- | :---- |
| Local inference ratio | 60-70% | Grafana local vs. cloud panel |
| Classification latency | < 1s (p95) | SQLite classification log |
| Request latency | < 4s (classified), < 2s (hint) | SQLite request log |
| API spend | < $100/month | Grafana daily spend panel |
| Escalation rate | < 15% per alias after tuning | SQLite escalation log |
| Router accuracy (raw) | > 85% after month 1 | Classification log vs. feedback |
| Effective routing reliability | Higher than raw accuracy | Alias bypass + confidence fallback + validation |
| Email triage time | < 2 min/day manual | User observation |
| Recovery time | < 40 minutes | Tested in Phase 1 |

---

# **Appendix: Model Inventory**

### RTX 4090 — Host A LXC 101 (192.168.1.220)

| Model | Size (Q4) | Purpose | Loading |
| :---- | :---- | :---- | :---- |
| qwen3.5:27b | ~16 GB | Primary heavy inference (multimodal) | Default, 60m keep-alive |
| llama3.1:8b | ~4.9 GB | Light tasks alongside 27B | On demand |

### RTX 3070 — Host B LXC 501 (192.168.1.41)

| Model | Size | Purpose | Loading |
| :---- | :---- | :---- | :---- |
| qwen3.5:4b | ~2.5 GB | Router / classifier (multimodal) | Always loaded |
| nomic-embed-text | ~0.6 GB | Music-rec engine embeddings | Always loaded |

### RTX 5060 Ti — Host C LXC 100 (192.168.1.50)

| Model | Size (Q4) | Purpose | Loading |
| :---- | :---- | :---- | :---- |
| qwen3.5:9b | ~5.5 GB | Batch processing + fallback (multimodal) | Default |
| llama3.2:3b | ~2 GB | Ultra-fast automation | On demand |

### Ollama Configuration

| Node | GPU | KV Cache | Keep-Alive | VRAM Gate |
| :---- | :---- | :---- | :---- | :---- |
| Host A LXC 101 | RTX 4090 | q4_0 | 60m | :11435 (90% threshold) |
| Host B LXC 501 | RTX 3070 | q4_0 | 60m | None |
| Host C LXC 100 | RTX 5060 Ti | Default | Default | None |

### API Keys Required

* Anthropic: `ANTHROPIC_API_KEY` (in ~/.zshrc, verified)
* OpenAI: `OPENAI_API_KEY` (in ~/.zshrc)
* Google: `GEMINI_API_KEY` (in ~/.zshrc)
* Fastmail: JMAP API token

### Distributed Inference (Optional)

llama.cpp RPC can pool RTX 4090 + RTX 5060 Ti for ~40 GB combined VRAM, enabling 70B Q4_K_M models. RPC worker on Host A LXC 101, port 50052. Not part of default operating mode but available for deep reasoning.
