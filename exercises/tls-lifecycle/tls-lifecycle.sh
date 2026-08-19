#!/bin/sh
set -eu

# [Implementation 1] CLI input and hostname contract
command=${1:-}
workdir=${2:-}
hostname=${3:-}
value=${4:-}
if [ -z "$command" ] || [ -z "$workdir" ] || [ -z "$hostname" ] || [ -z "$value" ]; then
    echo "usage: $0 {issue|renew|verify} WORKDIR HOSTNAME VALUE" >&2
    exit 2
fi
case "$command" in issue|renew|verify) ;; *) echo "unknown command: $command" >&2; exit 2 ;; esac
case "$hostname" in
    *[!A-Za-z0-9.-]*|.*|*..*|*.) echo "invalid hostname" >&2; exit 2 ;;
esac
case "$value" in ''|*[!0-9]*) echo "VALUE must be a non-negative integer" >&2; exit 2 ;; esac
if [ "$command" != verify ] && [ "$value" -le 0 ]; then
    echo "DAYS must be a positive integer" >&2
    exit 2
fi

umask 077
mkdir -p "$workdir/versions"

# [Implementation 2] Portable private-key mode check
file_mode() {
    if stat -L -c '%a' "$1" >/dev/null 2>&1; then
        stat -L -c '%a' "$1"
    else
        stat -L -f '%Lp' "$1"
    fi
}

# [Implementation 3] Local CA ownership
init_ca() {
    if [ -f "$workdir/ca.key" ] && [ -f "$workdir/ca.crt" ]; then
        [ "$(file_mode "$workdir/ca.key")" = 600 ] || { echo "ca.key mode must be 600" >&2; exit 1; }
        return
    fi
    [ ! -e "$workdir/ca.key" ] && [ ! -e "$workdir/ca.crt" ] || {
        echo "incomplete CA state" >&2
        exit 1
    }
    candidate=$(mktemp -d "$workdir/.ca.XXXXXX")
    trap 'rm -rf "$candidate"' EXIT HUP INT TERM
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
        -out "$candidate/ca.key" >/dev/null 2>&1
    openssl req -x509 -new -sha256 -days 3650 \
        -key "$candidate/ca.key" \
        -subj "/CN=Standalone Local Root CA" \
        -out "$candidate/ca.crt" >/dev/null 2>&1
    chmod 600 "$candidate/ca.key"
    chmod 644 "$candidate/ca.crt"
    mv "$candidate/ca.key" "$workdir/ca.key"
    mv "$candidate/ca.crt" "$workdir/ca.crt"
    rmdir "$candidate"
    trap - EXIT HUP INT TERM
}

issue_certificate() {
    days=$1
    init_ca

    # [Implementation 4] Versioned certificate candidate
    candidate=$(mktemp -d "$workdir/versions/.candidate.XXXXXX")
    trap 'rm -rf "$candidate"' EXIT HUP INT TERM
    openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
        -out "$candidate/server.key" >/dev/null 2>&1
    cat > "$candidate/extensions.cnf" <<EOF
[server_cert]
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:$hostname
EOF
    openssl req -new -sha256 \
        -key "$candidate/server.key" \
        -subj "/CN=$hostname" \
        -out "$candidate/server.csr" >/dev/null 2>&1
    openssl x509 -req -sha256 -days "$days" \
        -in "$candidate/server.csr" \
        -CA "$workdir/ca.crt" \
        -CAkey "$workdir/ca.key" \
        -CAcreateserial \
        -extfile "$candidate/extensions.cnf" \
        -extensions server_cert \
        -out "$candidate/server.crt" >/dev/null 2>&1
    chmod 600 "$candidate/server.key"
    chmod 644 "$candidate/server.crt"

    # [Implementation 5] Candidate trust verification
    openssl verify -CAfile "$workdir/ca.crt" "$candidate/server.crt" >/dev/null
    openssl x509 -in "$candidate/server.crt" -noout -checkhost "$hostname" >/dev/null
    openssl x509 -in "$candidate/server.crt" -noout -checkend 0 >/dev/null
    [ "$(file_mode "$candidate/server.key")" = 600 ] || { echo "candidate key mode must be 600" >&2; exit 1; }

    serial=$(openssl x509 -in "$candidate/server.crt" -noout -serial | sed 's/^serial=//')
    version="certificate-$serial"
    final="$workdir/versions/$version"
    [ ! -e "$final" ] || { echo "certificate version already exists: $version" >&2; exit 1; }
    rm -f "$candidate/server.csr" "$candidate/extensions.cnf"
    mv "$candidate" "$final"
    trap - EXIT HUP INT TERM

    # [Implementation 6] Atomic current certificate publication
    link_tmp="$workdir/.current.$$"
    rm -f "$link_tmp"
    ln -s "versions/$version" "$link_tmp"
    python3 - "$link_tmp" "$workdir/current" <<'PY_ATOMIC_REPLACE'
import os
import sys
os.replace(sys.argv[1], sys.argv[2])
PY_ATOMIC_REPLACE
    [ -e "$workdir/server.key" ] || ln -s current/server.key "$workdir/server.key"
    [ -e "$workdir/server.crt" ] || ln -s current/server.crt "$workdir/server.crt"
    printf '%s\n' "$version"
}

verify_certificate() {
    min_days=$1
    [ -L "$workdir/current" ] || { echo "current certificate pointer is missing" >&2; exit 1; }
    for file in ca.crt server.crt server.key; do
        [ -f "$workdir/$file" ] || { echo "required file is missing: $file" >&2; exit 1; }
    done
    openssl verify -CAfile "$workdir/ca.crt" "$workdir/server.crt" >/dev/null
    openssl x509 -in "$workdir/server.crt" -noout -checkhost "$hostname" >/dev/null
    openssl x509 -in "$workdir/server.crt" -noout -checkend "$((min_days * 86400))" >/dev/null
    mode=$(file_mode "$workdir/server.key")
    [ "$mode" = 600 ] || { echo "server.key mode must be 600, found $mode" >&2; exit 1; }
}

# [Implementation 7] Lifecycle command dispatch
case "$command" in
    issue|renew) issue_certificate "$value" ;;
    verify) verify_certificate "$value" ;;
esac
