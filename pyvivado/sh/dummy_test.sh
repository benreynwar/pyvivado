#!/usr/bin/env bash
echo "DEBUG: Passed argument is $1"
if [ "$1" = "moose" ]; then
    echo "ERROR: That is such a bad argument that this script will return 1."
    exit 1
fi
if [ "$1" = "fish" ]; then
    echo "INFO: Yay! It passed."
    exit 0
else
    echo "ERROR: The script only accepts an argument of 'fish'"
    exit 0
fi
