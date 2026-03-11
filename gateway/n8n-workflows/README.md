# n8n Workflows — AI Productivity Engine

Importable n8n workflow JSON files for the homelab AI gateway.

**n8n instance:** http://192.168.1.52:5678 (Host C LXC 102)
**n8n external:** https://n8n.neubneub.com (via Cloudflare tunnel)
**LiteLLM gateway:** http://litellm-gateway:4000 (Docker network) / http://192.168.1.52:4000 (LAN)
**ntfy server:** http://192.168.1.38:8090

## Deployed Workflows

All workflows imported and activated on n8n (Host C LXC 102).

| ID | File | Status | Description |
|----|------|--------|-------------|
| 100 | `email-triage.json` | Active | Fetch unread emails via Fastmail IMAP, classify with LLM (batch-triage), route by priority: P5 urgent ntfy, P4 important ntfy, P3 log, P1-2 archive |
| 101 | `job-search.json` | Active | Score job postings against 7-factor rubric (ASC 740, team, M&A, tech, location, seniority, stability). Score >80 triggers application pipeline, 60-80 creates Things 3 task |
| 102 | `notification-filter.json` | Active | Webhook receiver for Alertmanager/n8n events. Deterministic scoring (1-5), time-of-day gating, only score 4-5 push to ntfy |
| 103 | `pbc-document-sorting.json` | Active | Two pipelines: document classification against PBC checklist + weekly gap analysis report |
| 104 | `music-library-automation.json` | Active | Two pipelines: daily FLAC metadata tagging + weekly album description generation |

## How to Import (if re-deploying)

```bash
# SSH to Host C, exec into n8n container
ssh root@192.168.1.22
pct exec 102 -- bash

# Copy workflow files into container and import
docker cp workflow.json n8n:/tmp/
docker exec n8n n8n import:workflow --input=/tmp/workflow.json

# Activate
docker exec n8n n8n update:workflow --id=<ID> --active=true

# Restart n8n for activations to take effect
docker restart n8n
```

Note: Workflow JSON files must have string `id` fields (e.g., `"id": "100"`). n8n will reject them otherwise with "NOT NULL constraint" errors.

## Credentials Configured

| Credential | Type | Used By | Status |
|------------|------|---------|--------|
| LiteLLM Gateway Token | httpHeaderAuth (`Authorization: Bearer sk-litellm-...`) | All workflows with LLM calls | Configured |
| Fastmail IMAP | IMAP (`michael@neuberger.work`, `imap.fastmail.com:993`) | email-triage (#100) | Configured |
| Paperless Token | httpHeaderAuth (`Authorization: Token 8b22ca...`) | pbc-document-sorting (#103) | Configured |

Credentials imported via `n8n import:credentials` CLI. To re-import:
```bash
docker exec -i n8n n8n import:credentials --input=/dev/stdin <<< '<JSON>'
```

## Architecture

```
Schedule/Webhook Trigger
  |
  v
Data Source (IMAP / Paperless / Webhook)
  |
  v
Code Node — Extract & normalize metadata
  |
  v
HTTP Request — POST to LiteLLM gateway (batch-triage model)
  |
  v
Code Node — Parse LLM JSON response
  |
  v
Switch Node — Route by priority/category/score
  |
  +---> ntfy notification (urgent/important)
  +---> IMAP action (archive, flag, move)
  +---> Things 3 task creation
  +---> Fastmail draft creation
  +---> Log only (noOp)
```
