#!/bin/bash
# do_task.sh — Quick capture a task into Things 3
# Modifiers: @today @tonight @tomorrow @someday @anytime !deadline #tag
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

query="$1"

if [ -z "$query" ]; then
    echo "Type a task after 'do'"
    exit 0
fi

# Use python3 to parse modifiers and build the Things URL
result=$(python3 -c "
import urllib.parse
import re
import sys

query = sys.argv[1]
title = query
params = {}

# Parse @when modifiers (case-insensitive)
when_map = {
    '@tonight': 'evening',
    '@evening': 'evening',
    '@tomorrow': 'tomorrow',
    '@someday': 'someday',
    '@today': 'today',
    '@anytime': 'anytime',
}
for modifier, value in when_map.items():
    pattern = re.compile(re.escape(modifier), re.IGNORECASE)
    if pattern.search(title):
        params['when'] = value
        title = pattern.sub('', title)
        break

# Parse !deadline (e.g., !friday, !2026-03-15, !tomorrow)
deadline_match = re.search(r'!(\S+)', title)
if deadline_match:
    params['deadline'] = deadline_match.group(1)
    title = title.replace(deadline_match.group(0), '')

# Parse #tags — maps to Things @-prefixed tags
tags = []
for tag_match in re.finditer(r'#(\S+)', title):
    tags.append('@' + tag_match.group(1))
    title = title.replace(tag_match.group(0), '')
if tags:
    params['tags'] = ','.join(tags)

# Clean up title
title = ' '.join(title.split()).strip()
params['title'] = title

# Build Things URL
param_str = '&'.join(
    f'{k}={urllib.parse.quote(str(v))}' for k, v in params.items()
)
url = f'things:///add?{param_str}&reveal=true'

# Output: line 1 = URL, line 2 = clean title for notification
print(url)
print(title)
" "$query" 2>/dev/null)

if [ -z "$result" ]; then
    echo "Error parsing task"
    exit 0
fi

url=$(echo "$result" | head -1)
clean_title=$(echo "$result" | tail -1)

open "$url"
echo "$clean_title"
