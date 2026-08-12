#!/bin/sh
set -eu

# [Implementation 1] command·hostname·수명 입력을 filesystem 변경 전에 검증합니다.
command=${1:-}
workdir=${2:-}
hostname=${3:-}
value=${4:-}

if [ -z "$command" ] || [ -z "$workdir" ] || [ -z "$hostname" ] || [ -z "$value" ]; then
    echo "사용법: $0 {issue|renew|verify} WORKDIR HOSTNAME VALUE" >&2
    exit 2
fi

case "$hostname" in
  *[!A-Za-z0-9.-]*|.*|*..*|*.)
    echo "올바르지 않은 hostname입니다." >&2
    exit 2
    ;;
esac

mkdir -p "$workdir"
umask 077

# [Implementation 2] GNU와 BSD stat 차이를 감싸 key mode invariant를 동일하게 판정합니다.
file_mode() {
    if stat -c '%a' "$1" >/dev/null 2>&1; then
        stat -c '%a' "$1"
    else
        stat -f '%Lp' "$1"
    fi
}

# [Implementation 3] local CA key와 certificate를 제한 권한의 후보 파일에서 만든 뒤 순차 공개합니다.
init_ca() {
    if [ -f "$workdir/ca.key" ] && [ -f "$workdir/ca.crt" ]; then
        return
    fi
    openssl genpkey \
        -algorithm RSA \
        -pkeyopt rsa_keygen_bits:2048 \
        -out "$workdir/ca.key.tmp" >/dev/null 2>&1
    openssl req \
        -x509 -new -sha256 -days 3650 \
        -key "$workdir/ca.key.tmp" \
        -subj "/CN=Guide Local Root CA" \
        -out "$workdir/ca.crt.tmp" >/dev/null 2>&1
    chmod 600 "$workdir/ca.key.tmp"
    chmod 644 "$workdir/ca.crt.tmp"
    mv "$workdir/ca.key.tmp" "$workdir/ca.key"
    mv "$workdir/ca.crt.tmp" "$workdir/ca.crt"
}

# [Implementation 4] key·CSR·SAN certificate를 격리된 후보 directory에서 생성합니다.
issue_certificate() {
    days=$1
    case "$days" in
      ''|*[!0-9]*) echo "DAYS는 양의 정수여야 합니다." >&2; exit 2 ;;
    esac
    if [ "$days" -le 0 ]; then
        echo "DAYS는 양의 정수여야 합니다." >&2
        exit 2
    fi

    init_ca
    tmp="$workdir/.issue.$$"
    mkdir "$tmp"
    trap 'rm -rf "$tmp"' EXIT HUP INT TERM

    openssl genpkey \
        -algorithm RSA \
        -pkeyopt rsa_keygen_bits:2048 \
        -out "$tmp/server.key" >/dev/null 2>&1

    cat >"$tmp/extensions.cnf" <<EOF
[server_cert]
basicConstraints=critical,CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:$hostname
EOF

    openssl req \
        -new -sha256 \
        -key "$tmp/server.key" \
        -subj "/CN=$hostname" \
        -out "$tmp/server.csr" >/dev/null 2>&1

    openssl x509 \
        -req -sha256 -days "$days" \
        -in "$tmp/server.csr" \
        -CA "$workdir/ca.crt" \
        -CAkey "$workdir/ca.key" \
        -CAcreateserial \
        -extfile "$tmp/extensions.cnf" \
        -extensions server_cert \
        -out "$tmp/server.crt" >/dev/null 2>&1

    openssl verify -CAfile "$workdir/ca.crt" "$tmp/server.crt" >/dev/null
    openssl x509 -in "$tmp/server.crt" -noout -checkhost "$hostname" >/dev/null

    chmod 600 "$tmp/server.key"
    chmod 644 "$tmp/server.crt"
    mv "$tmp/server.key" "$workdir/server.key"
    mv "$tmp/server.crt" "$workdir/server.crt"
    rm -rf "$tmp"
    trap - EXIT HUP INT TERM
}

# [Implementation 5] chain·hostname·expiry·key mode를 모두 통과해야 current를 신뢰합니다.
verify_certificate() {
    min_days=$1
    case "$min_days" in
      ''|*[!0-9]*) echo "MIN_REMAINING_DAYS는 0 이상의 정수여야 합니다." >&2; exit 2 ;;
    esac
    for file in ca.crt server.crt server.key; do
        if [ ! -f "$workdir/$file" ]; then
            echo "필수 파일이 없습니다: $file" >&2
            exit 1
        fi
    done
    openssl verify -CAfile "$workdir/ca.crt" "$workdir/server.crt" >/dev/null
    openssl x509 -in "$workdir/server.crt" -noout -checkhost "$hostname" >/dev/null
    seconds=$((min_days * 86400))
    openssl x509 -in "$workdir/server.crt" -noout -checkend "$seconds" >/dev/null
    key_mode=$(file_mode "$workdir/server.key")
    if [ "$key_mode" != "600" ]; then
        echo "server.key mode가 600이 아닙니다: $key_mode" >&2
        exit 1
    fi
}

# [Implementation 6] issue·renew·verify public CLI를 검증된 lifecycle 함수에 연결합니다.
case "$command" in
  issue|renew)
    issue_certificate "$value"
    ;;
  verify)
    verify_certificate "$value"
    ;;
  *)
    echo "알 수 없는 명령: $command" >&2
    exit 2
    ;;
esac
