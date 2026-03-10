#!/bin/bash
# Base64 decode the input query
echo -n "{query}" | base64 -D
