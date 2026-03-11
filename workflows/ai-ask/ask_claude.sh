#!/bin/bash
# ask_claude.sh - Send a question to Claude API and return the response

query="$1"

# ANTHROPIC_API_KEY is set via Alfred workflow variables (info.plist)
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "No API key. Set ANTHROPIC_API_KEY in Alfred workflow variables."
    exit 0
fi

# Check for empty query
if [ -z "$query" ]; then
    echo "Please provide a question after 'ai'"
    exit 0
fi

# Default model if not set
model="${MODEL:-claude-sonnet-4-20250514}"

# Build the JSON payload using python3 to safely escape the query
json_payload=$(python3 -c "
import json, sys
query = sys.argv[1]
payload = {
    'model': sys.argv[2],
    'max_tokens': 1024,
    'messages': [
        {
            'role': 'user',
            'content': query
        }
    ]
}
print(json.dumps(payload))
" "$query" "$model" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$json_payload" ]; then
    echo "Error: Failed to build request payload"
    exit 0
fi

# Call the Anthropic Messages API
response=$(curl -s --max-time 30 \
    "https://api.anthropic.com/v1/messages" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$json_payload" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$response" ]; then
    echo "Error: Failed to reach Claude API (check your internet connection)"
    exit 0
fi

# Extract the response text using python3
result=$(python3 -c "
import json, sys

try:
    data = json.loads(sys.stdin.read())
except (json.JSONDecodeError, ValueError):
    print('Error: Invalid response from API')
    sys.exit(0)

# Check for API errors
if 'error' in data:
    error_msg = data['error'].get('message', 'Unknown API error')
    error_type = data['error'].get('type', 'error')
    print(f'API Error ({error_type}): {error_msg}')
    sys.exit(0)

# Extract text from content blocks
if 'content' in data and len(data['content']) > 0:
    texts = []
    for block in data['content']:
        if block.get('type') == 'text':
            texts.append(block['text'])
    if texts:
        print('\n'.join(texts))
    else:
        print('Error: No text in response')
else:
    print('Error: Unexpected response format')
" <<< "$response")

if [ -z "$result" ]; then
    echo "Error: Empty response from Claude"
    exit 0
fi

echo "$result"
