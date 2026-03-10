#!/bin/bash
# Convert between hex color and RGB
query="{query}"

# Remove leading # if present
query=$(echo "$query" | sed 's/^#//')

# Check if input looks like RGB (contains comma)
if echo "$query" | grep -q ','; then
    # RGB to Hex
    r=$(echo "$query" | cut -d',' -f1 | tr -d ' ')
    g=$(echo "$query" | cut -d',' -f2 | tr -d ' ')
    b=$(echo "$query" | cut -d',' -f3 | tr -d ' ')
    printf "#%02X%02X%02X\n" "$r" "$g" "$b"
else
    # Hex to RGB
    # Handle 3-char hex shorthand
    if [ ${#query} -eq 3 ]; then
        r=$(printf "%d" "0x${query:0:1}${query:0:1}")
        g=$(printf "%d" "0x${query:1:1}${query:1:1}")
        b=$(printf "%d" "0x${query:2:1}${query:2:1}")
    elif [ ${#query} -eq 6 ]; then
        r=$(printf "%d" "0x${query:0:2}")
        g=$(printf "%d" "0x${query:2:2}")
        b=$(printf "%d" "0x${query:4:2}")
    else
        echo "Invalid input. Use hex (e.g. FF5733) or RGB (e.g. 255,87,51)"
        exit 1
    fi
    echo "rgb($r, $g, $b)"
fi
