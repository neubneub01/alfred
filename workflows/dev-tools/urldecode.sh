#!/bin/bash
# URL decode the input query
# When called from Alfred, {query} is substituted; standalone usage: ./urldecode.sh "text"
query="${1:-{query}}"
python3 -c "import urllib.parse, sys; print(urllib.parse.unquote(sys.argv[1]))" "$query"
