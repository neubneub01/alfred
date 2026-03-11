#!/bin/bash
# plan_ai.sh — AI-powered project planning: Claude decomposes a goal → Things 3 project
# Uses Claude API to break down a goal, then creates structured project via Things JSON URL scheme
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

query="$1"

if [ -z "$query" ]; then
    echo "Describe a goal after 'brainstorm'"
    exit 0
fi

# ANTHROPIC_API_KEY is set via Alfred workflow variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "No API key. Set ANTHROPIC_API_KEY in Alfred workflow variables."
    exit 0
fi

model="${MODEL:-claude-sonnet-4-20250514}"
auth_token="${THINGS_AUTH_TOKEN}"

# Build the Claude API request — ask for structured task decomposition
json_payload=$(python3 -c "
import json, sys

goal = sys.argv[1]
model = sys.argv[2]

prompt = '''You are a task decomposition expert. Break down this goal into a Things 3 project structure.

Goal: ''' + goal + '''

Return ONLY valid JSON (no markdown fences, no explanation):
{
  \"title\": \"Project title (clear, concise)\",
  \"headings\": [
    {
      \"title\": \"Section Name\",
      \"tasks\": [\"Task 1\", \"Task 2\", \"Task 3\"]
    }
  ]
}

Rules:
- 2-4 headings maximum
- 3-5 tasks per heading
- Every task starts with a verb (actionable)
- Task titles under 60 characters
- Headings represent logical phases or categories
- Order tasks by dependency/sequence within each heading'''

payload = {
    'model': model,
    'max_tokens': 1024,
    'messages': [{'role': 'user', 'content': prompt}]
}
print(json.dumps(payload))
" "$query" "$model" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$json_payload" ]; then
    echo "Error building request"
    exit 0
fi

# Call Claude API
response=$(curl -s --max-time 30 \
    "https://api.anthropic.com/v1/messages" \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "content-type: application/json" \
    -d "$json_payload" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$response" ]; then
    echo "Error reaching Claude API"
    exit 0
fi

# Parse Claude's response → build Things JSON URL → open it
result=$(python3 -c "
import json, sys, urllib.parse

data = json.loads(sys.stdin.read())

if 'error' in data:
    msg = data['error'].get('message', 'Unknown error')
    print(f'API Error: {msg}')
    sys.exit(0)

if 'content' not in data or len(data['content']) == 0:
    print('Error: Empty response from Claude')
    sys.exit(0)

text = data['content'][0]['text'].strip()

# Handle markdown code fences if Claude includes them
if text.startswith('\`\`\`'):
    lines = text.split('\n')
    text = '\n'.join(lines[1:])
    if text.endswith('\`\`\`'):
        text = text[:-3].strip()

try:
    plan = json.loads(text)
except json.JSONDecodeError as e:
    print(f'Error: Could not parse AI response — {e}')
    sys.exit(0)

# Build Things JSON structure
items = []
for heading in plan.get('headings', []):
    items.append({
        'type': 'heading',
        'attributes': {'title': heading['title']}
    })
    for task in heading.get('tasks', []):
        items.append({
            'type': 'to-do',
            'attributes': {'title': task}
        })

things_json = [{
    'type': 'project',
    'attributes': {
        'title': plan.get('title', 'AI Plan'),
        'items': items
    }
}]

auth_token = sys.argv[1]
encoded = urllib.parse.quote(json.dumps(things_json))

if auth_token:
    url = f'things:///json?data={encoded}&auth-token={auth_token}&reveal=true'
else:
    url = f'things:///json?data={encoded}&reveal=true'

print(url)

# Summary for notification
task_count = sum(len(h.get('tasks', [])) for h in plan.get('headings', []))
heading_count = len(plan.get('headings', []))
print(f\"{plan.get('title', 'Plan')}: {heading_count} sections, {task_count} tasks\")
" "$auth_token" <<< "$response" 2>/dev/null)

if [ -z "$result" ]; then
    echo "Error processing AI response"
    exit 0
fi

# First line is URL, second is summary
url=$(echo "$result" | head -1)
summary=$(echo "$result" | tail -1)

# Check if first line looks like an error (not a URL)
if [[ ! "$url" == things://* ]]; then
    echo "$url"
    exit 0
fi

open "$url"
echo "$summary"
