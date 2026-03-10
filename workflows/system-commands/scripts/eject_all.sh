#!/bin/bash
# Eject all external drives
osascript -e 'tell application "Finder" to eject (every disk whose ejectable is true)'
echo "All drives ejected"
