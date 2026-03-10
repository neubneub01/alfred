#!/bin/bash
# Flush DNS cache
osascript -e 'do shell script "dscacheutil -flushcache; killall -HUP mDNSResponder" with administrator privileges'
echo "DNS cache flushed"
