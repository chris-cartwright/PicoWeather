#!/usr/bin/env bash

if ! command -v mpremote >/dev/null 2>&1; then
    echo "mpremote not found"
    exit 1
fi

if [ ! -f mips.txt ]; then
    echo "mips.txt not found"
fi


xargs mpremote mip install <mips.txt