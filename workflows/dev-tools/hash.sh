#!/bin/bash
# Script Filter: output MD5 and SHA256 hashes as Alfred JSON items
query="{query}"

if [ -z "$query" ]; then
    cat <<EOFJ
{"items":[{"title":"Type something to hash...","subtitle":"Enter text after the hash keyword","valid":false,"icon":{"path":"icon.png"}}]}
EOFJ
    exit 0
fi

md5=$(echo -n "$query" | md5)
sha256=$(echo -n "$query" | shasum -a 256 | awk '{print $1}')

cat <<EOFJ
{
  "items": [
    {
      "uid": "md5",
      "title": "$md5",
      "subtitle": "MD5 - Press Enter to copy",
      "arg": "$md5",
      "icon": { "path": "icon.png" },
      "text": {
        "copy": "$md5",
        "largetype": "$md5"
      }
    },
    {
      "uid": "sha256",
      "title": "$sha256",
      "subtitle": "SHA256 - Press Enter to copy",
      "arg": "$sha256",
      "icon": { "path": "icon.png" },
      "text": {
        "copy": "$sha256",
        "largetype": "$sha256"
      }
    }
  ]
}
EOFJ
