#!/bin/bash
# Kill process by PID
pid="$1"

if [ -z "$pid" ]; then
    echo "No PID provided"
    exit 1
fi

process_name=$(ps -p "$pid" -o comm= 2>/dev/null)

if kill -9 "$pid" 2>/dev/null; then
    echo "Killed ${process_name:-process} (PID: ${pid})"
else
    echo "Failed to kill PID ${pid} (may need sudo or already terminated)"
    exit 1
fi
