#!/bin/bash
# Alfred Workflow Installer
# Copies all workflows into Alfred's workflow directory

set -euo pipefail

ALFRED_WORKFLOWS="$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$ALFRED_WORKFLOWS"

echo "Installing Alfred workflows..."

for workflow_dir in "$SCRIPT_DIR"/workflows/*/; do
    workflow_name=$(basename "$workflow_dir")

    if [ ! -f "$workflow_dir/info.plist" ]; then
        echo "  SKIP: $workflow_name (no info.plist)"
        continue
    fi

    target="$ALFRED_WORKFLOWS/user.workflow.$workflow_name"

    if [ -L "$target" ]; then
        echo "  UPDATE: $workflow_name (replacing symlink with copy)"
        rm "$target"
    elif [ -d "$target" ]; then
        echo "  UPDATE: $workflow_name (replacing existing)"
        rm -rf "$target"
    else
        echo "  INSTALL: $workflow_name"
    fi

    cp -R "$workflow_dir" "$target/"
done

# Restart Alfred to pick up changes
killall Alfred 2>/dev/null
sleep 1
open -a "Alfred 5" 2>/dev/null || open -a "Alfred" 2>/dev/null

echo ""
echo "Done! Alfred has been restarted with the new workflows."
