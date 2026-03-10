#!/bin/bash
# Toggle Bluetooth based on argument
if [ "$1" = "on" ]; then
    if command -v blueutil &>/dev/null; then
        blueutil -p 1
    else
        osascript -e 'tell application "System Events" to tell process "ControlCenter"
            click menu bar item "Bluetooth" of menu bar 2
            delay 0.5
            click checkbox 1 of window 1
        end tell'
    fi
    echo "Bluetooth turned on"
elif [ "$1" = "off" ]; then
    if command -v blueutil &>/dev/null; then
        blueutil -p 0
    else
        osascript -e 'tell application "System Events" to tell process "ControlCenter"
            click menu bar item "Bluetooth" of menu bar 2
            delay 0.5
            click checkbox 1 of window 1
        end tell'
    fi
    echo "Bluetooth turned off"
fi
