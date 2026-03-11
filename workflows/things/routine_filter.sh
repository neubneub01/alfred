#!/bin/bash
# routine_filter.sh — Script filter showing routine templates for Things 3
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

query="$1"

python3 -c "
import json, sys

query = sys.argv[1].lower().strip() if len(sys.argv) > 1 else ''

items = [
    {
        'uid': 'weekly-review',
        'title': 'Weekly Review',
        'subtitle': '30 min — Process, review, plan the week ahead',
        'arg': 'weekly-review',
        'icon': {'path': 'icon.png'}
    },
    {
        'uid': 'morning-launch',
        'title': 'Morning Launch',
        'subtitle': '10 min — Inbox zero, star THE thing, tag quick wins',
        'arg': 'morning-launch',
        'icon': {'path': 'icon.png'}
    },
    {
        'uid': 'evening-shutdown',
        'title': 'Evening Shutdown',
        'subtitle': '5 min — Process inbox, reschedule, prep tomorrow',
        'arg': 'evening-shutdown',
        'icon': {'path': 'icon.png'}
    },
    {
        'uid': 'sprint-planning',
        'title': 'Sprint Planning',
        'subtitle': 'Create sprint project: Backlog / Active / Review / Done',
        'arg': 'sprint-planning',
        'icon': {'path': 'icon.png'}
    },
]

if query:
    filtered = [i for i in items if query in i['title'].lower() or query in i['subtitle'].lower()]
else:
    filtered = items

if not filtered:
    filtered = [{'title': 'No matching routine', 'valid': False}]

print(json.dumps({'items': filtered}))
" "$query"
