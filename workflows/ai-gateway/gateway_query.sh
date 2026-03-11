#!/bin/bash
# gateway_query.sh — Send a query through the LiteLLM gateway with model alias routing
# Usage: gateway_query.sh ALIAS QUERY
# install.sh handles chmod +x
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

GATEWAY_URL="http://192.168.1.52:4000/v1/chat/completions"

alias="$1"
query="$2"

# If only one arg, treat it as query with auto alias
if [ -z "$query" ]; then
    query="$alias"
    alias="chat"
fi

if [ -z "$query" ]; then
    echo "Please provide a query"
    exit 0
fi

# Get API key — try workflow variable first, then grep from ~/.zshrc
api_key="${LITELLM_MASTER_KEY}"
if [ -z "$api_key" ]; then
    api_key=$(grep -m1 'export LITELLM_MASTER_KEY=' ~/.zshrc 2>/dev/null | sed 's/^export LITELLM_MASTER_KEY=//' | tr -d '"' | tr -d "'")
fi

# Build auth header — if no key, try without auth (gateway may be open on LAN)
auth_header=""
if [ -n "$api_key" ]; then
    auth_header="-H \"Authorization: Bearer $api_key\""
fi

# Build the JSON payload safely with python3
json_payload=$(python3 -c "
import json, sys
payload = {
    'model': sys.argv[1],
    'messages': [
        {'role': 'user', 'content': sys.argv[2]}
    ],
    'max_tokens': 4096
}
print(json.dumps(payload))
" "$alias" "$query" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$json_payload" ]; then
    echo "Error: Failed to build request payload"
    exit 0
fi

# Call the gateway
if [ -n "$api_key" ]; then
    response=$(curl -s --max-time 60 --connect-timeout 5 \
        "$GATEWAY_URL" \
        -H "Authorization: Bearer $api_key" \
        -H "Content-Type: application/json" \
        -d "$json_payload" 2>/dev/null)
else
    response=$(curl -s --max-time 60 --connect-timeout 5 \
        "$GATEWAY_URL" \
        -H "Content-Type: application/json" \
        -d "$json_payload" 2>/dev/null)
fi

curl_exit=$?

if [ $curl_exit -eq 7 ]; then
    echo "Error: Gateway unreachable at 192.168.1.52:4000 — is LiteLLM running?"
    exit 0
elif [ $curl_exit -eq 28 ]; then
    echo "Error: Gateway request timed out (60s limit)"
    exit 0
elif [ $curl_exit -ne 0 ] || [ -z "$response" ]; then
    echo "Error: Failed to reach gateway (curl exit $curl_exit)"
    exit 0
fi

# Extract the response — OpenAI-compatible format from LiteLLM
result=$(python3 -c "
import json, sys

try:
    data = json.loads(sys.stdin.read())
except (json.JSONDecodeError, ValueError):
    print('Error: Invalid JSON response from gateway')
    sys.exit(0)

# Check for API errors
if 'error' in data:
    msg = data['error'].get('message', str(data['error']))
    print(f'Gateway Error: {msg}')
    sys.exit(0)

# OpenAI-compatible: choices[0].message.content
if 'choices' in data and len(data['choices']) > 0:
    content = data['choices'][0].get('message', {}).get('content', '')
    if content:
        print(content)
    else:
        print('Error: Empty response from model')
else:
    print('Error: Unexpected response format')
" <<< "$response")

if [ -z "$result" ]; then
    echo "Error: Empty response from gateway"
    exit 0
fi

echo "$result"
