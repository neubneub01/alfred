#!/bin/bash
# Toggle hidden files in Finder
STATUS=$(defaults read com.apple.finder AppleShowAllFiles 2>/dev/null)
if [ "$STATUS" = "TRUE" ] || [ "$STATUS" = "YES" ] || [ "$STATUS" = "1" ]; then
    defaults write com.apple.finder AppleShowAllFiles -bool false
    echo "Hidden files are now hidden"
else
    defaults write com.apple.finder AppleShowAllFiles -bool true
    echo "Hidden files are now visible"
fi
killall Finder
