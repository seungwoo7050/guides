#!/bin/sh
set -eu

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
cd -- "$script_dir"

mode=${1:-all}
case "$mode" in
    all|skeleton|failure)
        [ "$#" -eq 1 ] || {
            printf '%s\n' '사용법: ./check.sh all|skeleton|failure' >&2
            exit 2
        }
        exec "${PYTHON:-python3}" ./check.py "$mode"
        ;;
    reference)
        [ "$#" -le 2 ] || {
            printf '%s\n' '사용법: ./check.sh reference [checkpoint]' >&2
            exit 2
        }
        exec "${PYTHON:-python3}" ./check.py reference "${2:-all}"
        ;;
    workspace)
        [ "$#" -le 2 ] || {
            printf '%s\n' '사용법: ./check.sh workspace [checkpoint]' >&2
            exit 2
        }
        exec "${PYTHON:-python3}" ./check.py implementation workspace "${2:-all}"
        ;;
    implementation)
        [ "$#" -ge 2 ] && [ "$#" -le 3 ] || {
            printf '%s\n' '사용법: ./check.sh implementation <directory> [checkpoint]' >&2
            exit 2
        }
        exec "${PYTHON:-python3}" ./check.py implementation "$2" "${3:-all}"
        ;;
    *)
        printf '%s\n' '사용법: ./check.sh all|reference|skeleton|failure|workspace|implementation' >&2
        exit 2
        ;;
esac
