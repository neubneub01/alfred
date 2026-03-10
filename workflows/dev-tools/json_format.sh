#!/bin/bash
# Pretty-print JSON from clipboard and copy result
result=$(pbpaste | python3 -m json.tool 2>&1)
if [ $? -eq 0 ]; then
    echo "$result" | pbcopy
    echo "JSON formatted and copied to clipboard"
else
    echo "Invalid JSON: $result"
fi
