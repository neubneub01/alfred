#!/bin/bash
# run_routine.sh — Execute a routine template, creating tasks in Things 3 via JSON URL scheme
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

routine="$1"
auth_token="${THINGS_AUTH_TOKEN}"
today_date=$(date +"%b %d")

case "$routine" in
    "weekly-review")
        json='[{"type":"to-do","attributes":{"title":"Weekly Review","when":"today","tags":["@deep"],"checklist-items":[{"type":"checklist-item","attributes":{"title":"Clear Inbox to zero"}},{"type":"checklist-item","attributes":{"title":"Review Today & Upcoming — anything stale?"}},{"type":"checklist-item","attributes":{"title":"Review Someday — promote or compost"}},{"type":"checklist-item","attributes":{"title":"Review @waiting — follow up on stalled items"}},{"type":"checklist-item","attributes":{"title":"Check each Area — anything missing?"}},{"type":"checklist-item","attributes":{"title":"Review calendar for next 2 weeks"}},{"type":"checklist-item","attributes":{"title":"Capture lessons learned in Capacities"}},{"type":"checklist-item","attributes":{"title":"Set 3 intentions for next week"}}]}}]'
        label="Weekly Review"
        ;;
    "morning-launch")
        json='[{"type":"to-do","attributes":{"title":"Morning Launch","when":"today","checklist-items":[{"type":"checklist-item","attributes":{"title":"Process Inbox to zero"}},{"type":"checklist-item","attributes":{"title":"Review Today — honest list? Move overflow."}},{"type":"checklist-item","attributes":{"title":"Star THE one thing today"}},{"type":"checklist-item","attributes":{"title":"Tag 3-4 @quick tasks for gaps"}},{"type":"checklist-item","attributes":{"title":"Check calendar — set reminders for timed items"}}]}}]'
        label="Morning Launch"
        ;;
    "evening-shutdown")
        json='[{"type":"to-do","attributes":{"title":"Evening Shutdown","when":"evening","checklist-items":[{"type":"checklist-item","attributes":{"title":"Process Inbox to zero"}},{"type":"checklist-item","attributes":{"title":"Review Today — move incomplete to tomorrow"}},{"type":"checklist-item","attributes":{"title":"Check tomorrow calendar — any prep needed?"}},{"type":"checklist-item","attributes":{"title":"Capture any loose thoughts as tasks"}}]}}]'
        label="Evening Shutdown"
        ;;
    "sprint-planning")
        json="[{\"type\":\"project\",\"attributes\":{\"title\":\"Sprint — Week of ${today_date}\",\"items\":[{\"type\":\"heading\",\"attributes\":{\"title\":\"Backlog\"}},{\"type\":\"to-do\",\"attributes\":{\"title\":\"[Add sprint items]\"}},{\"type\":\"heading\",\"attributes\":{\"title\":\"In Progress\"}},{\"type\":\"heading\",\"attributes\":{\"title\":\"Review / QA\"}},{\"type\":\"heading\",\"attributes\":{\"title\":\"Done\"}}]}}]"
        label="Sprint — Week of ${today_date}"
        ;;
    *)
        echo "Unknown routine: $routine"
        exit 0
        ;;
esac

# URL-encode and open
url=$(python3 -c "
import urllib.parse, sys
json_data = sys.argv[1]
token = sys.argv[2]
encoded = urllib.parse.quote(json_data)
if token:
    print(f'things:///json?data={encoded}&auth-token={token}&reveal=true')
else:
    print(f'things:///json?data={encoded}&reveal=true')
" "$json" "$auth_token" 2>/dev/null)

open "$url"
echo "$label"
