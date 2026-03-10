#!/bin/bash
# Alfred Workflow Installer
# Symlinks all workflows into Alfred's workflow directory

set -euo pipefail

ALFRED_WORKFLOWS="$HOME/Library/Application Support/Alfred/Alfred.alfredpreferences/workflows"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$ALFRED_WORKFLOWS"

echo "Installing Alfred workflows..."

for workflow_dir in "$SCRIPT_DIR"/workflows/*/; do
    workflow_name=$(basename "$workflow_dir")

    # Check for info.plist (required for Alfred to recognize it)
    if [ ! -f "$workflow_dir/info.plist" ]; then
        echo "  SKIP: $workflow_name (no info.plist)"
        continue
    fi

    target="$ALFRED_WORKFLOWS/user.workflow.$workflow_name"

    if [ -L "$target" ]; then
        echo "  UPDATE: $workflow_name (re-linking)"
        rm "$target"
    elif [ -d "$target" ]; then
        echo "  SKIP: $workflow_name (non-symlink dir exists, remove manually to replace)"
        continue
    else
        echo "  INSTALL: $workflow_name"
    fi

    ln -s "$workflow_dir" "$target"
done

echo ""
echo "Done! Restart Alfred (or reload workflows) to pick up changes."
echo "  Alfred > Preferences > Workflows should now show the new workflows."
