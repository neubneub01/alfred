#!/bin/bash
# Toggle Wi-Fi
DEVICE=$(networksetup -listallhardwareports | awk '/Wi-Fi/{getline; print $2}')
STATUS=$(networksetup -getairportpower "$DEVICE" | awk '{print $NF}')
if [ "$STATUS" = "On" ]; then
    networksetup -setairportpower "$DEVICE" off
    echo "Wi-Fi turned off"
else
    networksetup -setairportpower "$DEVICE" on
    echo "Wi-Fi turned on"
fi
