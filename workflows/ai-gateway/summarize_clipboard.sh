#!/bin/bash
# summarize_clipboard.sh — Read clipboard contents, summarize via LiteLLM gateway
# Triggered by 'sum' keyword — no arguments needed
# install.sh handles chmod +x
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

GATEWAY_URL="http://192.168.1.52:4000/v1/chat/completions"

# Read clipboard
clipboard=$(pbpaste 2>/dev/null)

if [ -z "$clipboard" ]; then
    echo "Clipboard is empty — copy some text first"
    exit 0
fi

# Get API key
api_key="${LITELLM_MASTER_KEY}"
if [ -z "$api_key" ]; then
    api_key=$(grep -m1 'export LITELLM_MASTER_KEY=' ~/.zshrc 2>/dev/null | sed 's/^export LITELLM_MASTER_KEY=//' | tr -d '"' | tr -d "'")
fi

# Build JSON payload with summarization system prompt
json_payload=$(python3 -c "
import json, sys

content = sys.stdin.read()
payload = {
    'model': 'summarize',
    'messages': [
        {
            'role': 'system',
            'content': 'You are a concise summarizer. Provide a clear, well-structured summary of the given text. Use bullet points for key takeaways. Keep it brief but comprehensive.'
        },
        {
            'role': 'user',
            'content': f'Summarize this:\n\n{content}'
        }
    ],
    'max_tokens': 2048
}
print(json.dumps(payload))
" <<< "$clipboard" 2>/dev/null)

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
    echo "Error: Gateway request timed out"
    exit 0
elif [ $curl_exit -ne 0 ] || [ -z "$response" ]; then
    echo "Error: Failed to reach gateway (curl exit $curl_exit)"
    exit 0
fi

# Extract response
result=$(python3 -c "
import json, sys

try:
    data = json.loads(sys.stdin.read())
except (json.JSONDecodeError, ValueError):
    print('Error: Invalid JSON response from gateway')
    sys.exit(0)

if 'error' in data:
    msg = data['error'].get('message', str(data['error']))
    print(f'Gateway Error: {msg}')
    sys.exit(0)

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

# Copy result to clipboard
echo "$result" | pbcopy

echo "$result"
