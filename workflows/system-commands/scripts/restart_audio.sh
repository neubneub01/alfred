#!/bin/bash
# Restart Core Audio
osascript -e 'do shell script "killall coreaudiod" with administrator privileges'
echo "Audio service restarted"
