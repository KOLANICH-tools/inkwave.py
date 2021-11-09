#!/usr/bin/env bash

#meld ${1} $(echo "${1}" | sed s/_c.txt/_py.txt/)
diff -U 3 ${1} $(echo "${1}" | sed s/_c.txt/_py.txt/)
