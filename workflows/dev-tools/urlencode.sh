#!/bin/bash
# URL encode the input query
# When called from Alfred, {query} is substituted; standalone usage: ./urlencode.sh "text"
query="${1:-{query}}"
python3 -c "import urllib.parse, sys; print(urllib.parse.quote(sys.argv[1], safe=''))" "$query"
