#!/bin/bash
# Run macOS maintenance scripts
osascript -e 'do shell script "periodic daily weekly monthly" with administrator privileges'
echo "Maintenance scripts completed"
