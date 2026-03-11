#!/bin/bash
# plan_project.sh — Create a Things 3 project from Alfred
# Usage: plan Project Name
#        plan Project Name / Task 1, Task 2, Task 3
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

query="$1"

if [ -z "$query" ]; then
    echo "Type a project name after 'plan'"
    exit 0
fi

url=$(python3 -c "
import urllib.parse
import sys

query = sys.argv[1]
params = {}

# Split on / to get project name and optional tasks
if ' / ' in query:
    parts = query.split(' / ', 1)
    project_name = parts[0].strip()
    tasks_str = parts[1].strip()
    tasks = [t.strip() for t in tasks_str.split(',') if t.strip()]
else:
    project_name = query.strip()
    tasks = []

params['title'] = project_name
params['reveal'] = 'true'

if tasks:
    # Newline-separated list of to-do titles
    params['to-dos'] = chr(10).join(tasks)

param_str = '&'.join(
    f'{k}={urllib.parse.quote(str(v))}' for k, v in params.items()
)
print(f'things:///add-project?{param_str}')
" "$query" 2>/dev/null)

if [ -z "$url" ]; then
    echo "Error creating project"
    exit 0
fi

open "$url"

# Extract project name for notification
project_name=$(echo "$query" | sed 's| /.*||')
echo "$project_name"
