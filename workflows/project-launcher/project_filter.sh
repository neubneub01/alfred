#!/bin/bash

# Project directories to scan
DIRS=(
    "/Volumes/NVMe2tbCrucial500/Code"
    "$HOME/Documents/GitHub"
)

query="$1"

# Collect all project directories (1 level deep) with modification times
projects=()
while IFS= read -r line; do
    projects+=("$line")
done < <(
    for dir in "${DIRS[@]}"; do
        if [[ -d "$dir" ]]; then
            find "$dir" -mindepth 1 -maxdepth 1 -type d -not -name '.*' -exec stat -f '%m %N' {} \;
        fi
    done | sort -rn
)

# Build JSON output
items=""
count=0

for entry in "${projects[@]}"; do
    # Split timestamp from path
    mtime="${entry%% *}"
    path="${entry#* }"
    name="$(basename "$path")"

    # Filter by query if provided (case-insensitive)
    if [[ -n "$query" ]]; then
        if ! echo "$name" | grep -qi "$query"; then
            continue
        fi
    fi

    # Build JSON item
    if [[ -n "$items" ]]; then
        items="$items,"
    fi

    items="$items
    {
        \"uid\": \"$path\",
        \"title\": \"$name\",
        \"subtitle\": \"$path\",
        \"arg\": \"$path\",
        \"autocomplete\": \"$name\",
        \"icon\": {
            \"type\": \"fileicon\",
            \"path\": \"/Applications/Visual Studio Code.app\"
        },
        \"valid\": true
    }"

    count=$((count + 1))
    if [[ $count -ge 20 ]]; then
        break
    fi
done

# Output Alfred JSON
cat <<EOF
{
    "items": [$items
    ]
}
EOF
