#!/bin/bash
# Nightly SQLite backup — runs via cron at 2:00 AM
# Deploy to: /opt/scripts/nightly_backup.sh on Host C LXC 102
# Cron: 0 2 * * * root /opt/scripts/nightly_backup.sh

set -euo pipefail

BACKUP_DIR="/mnt/nfs/backups/ai-engine/$(date +%Y-%m-%d)"
LITELLM_DB="/opt/litellm/data/litellm.db"
AGENT_DB="/opt/agent-service/data/agents.db"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

# Backup LiteLLM SQLite (online backup — safe while DB is in use)
if [ -f "$LITELLM_DB" ]; then
    sqlite3 "$LITELLM_DB" ".backup '$BACKUP_DIR/litellm.db'"
    echo "$(date -Iseconds) Backed up litellm.db → $BACKUP_DIR/"
fi

# Backup agent service SQLite
if [ -f "$AGENT_DB" ]; then
    sqlite3 "$AGENT_DB" ".backup '$BACKUP_DIR/agents.db'"
    echo "$(date -Iseconds) Backed up agents.db → $BACKUP_DIR/"
fi

# Backup n8n data (if mounted)
N8N_DIR="/opt/n8n/data"
if [ -d "$N8N_DIR" ]; then
    tar czf "$BACKUP_DIR/n8n-data.tar.gz" -C "$N8N_DIR" . 2>/dev/null || true
    echo "$(date -Iseconds) Backed up n8n data → $BACKUP_DIR/"
fi

# Prune old backups
find /mnt/nfs/backups/ai-engine/ -maxdepth 1 -mtime +${RETENTION_DAYS} -exec rm -rf {} +
echo "$(date -Iseconds) Pruned backups older than ${RETENTION_DAYS} days"
