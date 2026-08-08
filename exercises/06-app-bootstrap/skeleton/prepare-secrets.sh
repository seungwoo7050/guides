#!/bin/sh
set -eu
base_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$base_dir/secrets"
for name in db_root_password db_password; do
    target="$base_dir/secrets/$name.txt"
    example="$target.example"
    if [ ! -f "$target" ]; then
        cp "$example" "$target"
        chmod 0600 "$target"
    fi
done
