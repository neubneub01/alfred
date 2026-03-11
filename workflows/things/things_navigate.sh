#!/bin/bash
# things_navigate.sh — Script filter for Things 3 navigation
# Shows views and Areas, filterable by typing
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

query="$1"

python3 -c "
import json, sys

query = sys.argv[1].lower().strip() if len(sys.argv) > 1 else ''

items = [
    {'uid': 'today',     'title': 'Today',     'subtitle': 'Your honest commitment for today',    'arg': 'things:///show?id=today'},
    {'uid': 'inbox',     'title': 'Inbox',     'subtitle': 'Capture bucket — process to zero',    'arg': 'things:///show?id=inbox'},
    {'uid': 'upcoming',  'title': 'Upcoming',  'subtitle': 'Scheduled future tasks',              'arg': 'things:///show?id=upcoming'},
    {'uid': 'anytime',   'title': 'Anytime',   'subtitle': 'Available tasks with no specific date','arg': 'things:///show?id=anytime'},
    {'uid': 'someday',   'title': 'Someday',   'subtitle': 'The greenhouse — review weekly',      'arg': 'things:///show?id=someday'},
    {'uid': 'logbook',   'title': 'Logbook',   'subtitle': 'Completed tasks archive',             'arg': 'things:///show?id=logbook'},
    {'uid': 'deadlines', 'title': 'Deadlines', 'subtitle': 'Tasks with due dates',                'arg': 'things:///show?id=deadlines'},
    {'uid': 'repeating', 'title': 'Repeating', 'subtitle': 'Recurring task templates',            'arg': 'things:///show?id=repeating'},
    # Areas
    {'uid': 'career',    'title': 'Career',          'subtitle': 'Area: Job search, professional development',  'arg': 'things:///show?query=Career'},
    {'uid': 'finance',   'title': 'Finance & Admin', 'subtitle': 'Area: Bills, admin tasks, errands',           'arg': 'things:///show?query=Finance%20%26%20Admin'},
    {'uid': 'fitness',   'title': 'Fitness',         'subtitle': 'Area: Training, health',                      'arg': 'things:///show?query=Fitness'},
    {'uid': 'homelab',   'title': 'Homelab',         'subtitle': 'Area: Proxmox, Docker, networking',           'arg': 'things:///show?query=Homelab'},
    {'uid': 'personal',  'title': 'Personal',        'subtitle': 'Area: Everything else',                       'arg': 'things:///show?query=Personal'},
    {'uid': 'tax',       'title': 'Tax & Advisory',  'subtitle': 'Area: Professional tax expertise',            'arg': 'things:///show?query=Tax%20%26%20Advisory'},
]

if query:
    filtered = [i for i in items if query in i['title'].lower() or query in i['subtitle'].lower()]
else:
    filtered = items

if not filtered:
    filtered = [{'title': 'No matches', 'valid': False}]

print(json.dumps({'items': filtered}))
" "$query"
