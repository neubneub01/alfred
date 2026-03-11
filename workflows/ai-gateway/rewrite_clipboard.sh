#!/bin/bash
# rewrite_clipboard.sh — Read clipboard, rewrite with specified style via LiteLLM gateway
# Usage: rewrite_clipboard.sh STYLE
# Styles: formal, casual, concise, expand, fix-grammar
# install.sh handles chmod +x
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

GATEWAY_URL="http://192.168.1.52:4000/v1/chat/completions"

style="${1:-concise}"

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

# Map style to system prompt
system_prompt=$(python3 -c "
import sys

style = sys.argv[1]
prompts = {
    'formal': 'Rewrite the following text in a professional, formal tone. Maintain the original meaning but use precise, polished language appropriate for business communication.',
    'casual': 'Rewrite the following text in a friendly, casual tone. Keep the core message but make it conversational and approachable.',
    'concise': 'Rewrite the following text to be as concise as possible. Remove filler words, redundancies, and unnecessary phrases. Keep every important point but use fewer words.',
    'expand': 'Expand the following text with more detail, examples, and explanation. Flesh out any points that are too brief. Maintain the original tone.',
    'fix-grammar': 'Fix all grammar, spelling, and punctuation errors in the following text. Do not change the tone or meaning — only correct mistakes. If the text is already correct, return it unchanged.'
}

prompt = prompts.get(style, prompts['concise'])
print(prompt)
" "$style" 2>/dev/null)

if [ -z "$system_prompt" ]; then
    system_prompt="Rewrite the following text to be clearer and more concise."
fi

# Build JSON payload
json_payload=$(python3 -c "
import json, sys

content = sys.stdin.read()
system = sys.argv[1]

payload = {
    'model': 'chat',
    'messages': [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': content}
    ],
    'max_tokens': 4096
}
print(json.dumps(payload))
" "$system_prompt" <<< "$clipboard" 2>/dev/null)

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

echo "[$style] $result"
