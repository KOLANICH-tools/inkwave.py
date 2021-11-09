#!/usr/bin/env bash

./inkwaveC -t $1 > ${1}_c.txt
python3 -m inkwave -t $1 > ${1}_py.txt
