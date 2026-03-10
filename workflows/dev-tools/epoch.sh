#!/bin/bash
# Handle epoch time - show current or convert timestamp
query="{query}"

if [ -z "$query" ]; then
    # No argument: show current Unix timestamp
    date +%s
else
    # Argument provided: convert timestamp to human-readable date
    date -r "$query" '+%Y-%m-%d %H:%M:%S %Z'
fi
