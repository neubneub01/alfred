#!/bin/bash

cat << 'EOF'
{
  "items": [
    {
      "uid": "homelab-neubneub",
      "title": "neubneub",
      "subtitle": "ssh root@192.168.1.188",
      "arg": "ssh root@192.168.1.188",
      "autocomplete": "neubneub",
      "icon": {
        "type": "fileicon",
        "path": "/System/Applications/Utilities/Terminal.app"
      }
    },
    {
      "uid": "homelab-neub",
      "title": "neub",
      "subtitle": "ssh root@192.168.1.166",
      "arg": "ssh root@192.168.1.166",
      "autocomplete": "neub",
      "icon": {
        "type": "fileicon",
        "path": "/System/Applications/Utilities/Terminal.app"
      }
    },
    {
      "uid": "homelab-neub3",
      "title": "neub3",
      "subtitle": "ssh root@192.168.1.22",
      "arg": "ssh root@192.168.1.22",
      "autocomplete": "neub3",
      "icon": {
        "type": "fileicon",
        "path": "/System/Applications/Utilities/Terminal.app"
      }
    }
  ]
}
EOF
