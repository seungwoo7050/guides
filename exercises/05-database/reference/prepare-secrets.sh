#!/bin/sh
set -eu
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
umask 077
for name in db_root_password db_password; do
    target="$base_dir/secrets/$name.txt"
    if [ ! -f "$target" ]; then
        cp "$target.example" "$target"
        chmod 0600 "$target"
    fi
done
