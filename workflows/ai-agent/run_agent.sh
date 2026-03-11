#!/bin/bash
# run_agent.sh — Fire-and-forget agent trigger via homelab agent service
# Usage: run_agent.sh AGENT_TYPE TASK
# install.sh handles chmod +x
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

AGENT_URL="http://192.168.1.52:8100/v1/agent/run"

agent_type="$1"
task="$2"

if [ -z "$agent_type" ] || [ -z "$task" ]; then
    echo "Error: Missing agent type or task"
    exit 0
fi

# Get API key (optional — agent service may use same LiteLLM key or be open on LAN)
api_key="${LITELLM_MASTER_KEY}"
if [ -z "$api_key" ]; then
    api_key=$(grep -m1 'export LITELLM_MASTER_KEY=' ~/.zshrc 2>/dev/null | sed 's/^export LITELLM_MASTER_KEY=//' | tr -d '"' | tr -d "'")
fi

# Build JSON payload
json_payload=$(python3 -c "
import json, sys
payload = {
    'agent_type': sys.argv[1],
    'task': sys.argv[2]
}
print(json.dumps(payload))
" "$agent_type" "$task" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$json_payload" ]; then
    echo "Error: Failed to build request payload"
    exit 0
fi

# Fire-and-forget — background curl so Alfred returns immediately
# Notification will come from the agent service when done
if [ -n "$api_key" ]; then
    curl -s --max-time 10 --connect-timeout 3 \
        "$AGENT_URL" \
        -H "Authorization: Bearer $api_key" \
        -H "Content-Type: application/json" \
        -d "$json_payload" \
        >/dev/null 2>&1 &
else
    curl -s --max-time 10 --connect-timeout 3 \
        "$AGENT_URL" \
        -H "Content-Type: application/json" \
        -d "$json_payload" \
        >/dev/null 2>&1 &
fi

echo "Agent '$agent_type' started: $task"
