#!/bin/bash
# Script Filter for Bluetooth on/off options
cat << 'JSONEOF'
{
  "items": [
    {
      "uid": "bt-on",
      "title": "Bluetooth On",
      "subtitle": "Turn Bluetooth on",
      "arg": "on",
      "icon": {
        "path": "icon.png"
      }
    },
    {
      "uid": "bt-off",
      "title": "Bluetooth Off",
      "subtitle": "Turn Bluetooth off",
      "arg": "off",
      "icon": {
        "path": "icon.png"
      }
    }
  ]
}
JSONEOF
