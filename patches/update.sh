#!/usr/bin/env bash

set -ex;

thisDir=`dirname $0`;

git checkout master;
git branch -D "patches_update" || true;
git checkout -b "patches_update";

for patchFile in `find $thisDir -name "*.patch" -type f`; do
	echo "Upgrading patch $patchFile";
	git am $patchFile;
	git format-patch -1 --stdout > $patchFile;
	git add $patchFile;
	git checkout master;
	git commit --amend --no-edit;
done;
