#!/bin/bash
# Process Filter for Alfred Script Filter
# Searches running processes and outputs Alfred JSON format

query="$1"

# Function to escape a string for JSON
json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\t'/\\t}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    printf '%s' "$s"
}

# Build the JSON items array
items=""
separator=""

if [ -z "$query" ]; then
    # No query: show top 10 CPU-consuming processes (exclude header)
    process_lines=$(ps aux -r | awk 'NR>1 && NR<=11')
else
    # Query provided: search for matching processes
    process_lines=$(ps aux | grep -i "[${query:0:1}]${query:1}" | grep -v "process_filter\.sh")
fi

while IFS= read -r line; do
    [ -z "$line" ] && continue

    pid=$(echo "$line" | awk '{print $2}')
    cpu=$(echo "$line" | awk '{print $3}')
    mem=$(echo "$line" | awk '{print $4}')
    command=$(echo "$line" | awk '{for(i=11;i<=NF;i++) printf "%s ", $i; print ""}' | sed 's/ *$//')
    name=$(basename "$(echo "$command" | awk '{print $1}')")

    [ -z "$pid" ] && continue
    [ "$pid" = "$$" ] && continue

    escaped_name=$(json_escape "$name")
    escaped_command=$(json_escape "$command")
    escaped_subtitle=$(json_escape "PID: ${pid} | CPU: ${cpu}% | MEM: ${mem}% | ${command}")

    items="${items}${separator}{\"uid\":\"${pid}\",\"title\":\"${escaped_name}\",\"subtitle\":\"${escaped_subtitle}\",\"arg\":\"${pid}\",\"icon\":{\"type\":\"fileicon\",\"path\":\"/System/Applications/Utilities/Activity Monitor.app\"}}"
    separator=","
done <<< "$process_lines"

# Output Alfred JSON
printf '{"items":[%s]}\n' "$items"
