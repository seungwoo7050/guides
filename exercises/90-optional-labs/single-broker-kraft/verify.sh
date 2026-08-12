#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
PREFIX="${GUIDE_DOCKER_PROJECT_PREFIX:-guide-distributed-kraft-${UID:-0}-$$-${RANDOM:-0}}"
SKELETON_PROJECT="${PREFIX}-skeleton"
REFERENCE_PROJECT="${PREFIX}-reference"
MESSAGE="guide-message-1"

log() {
  printf '[kraft] %s\n' "$*"
}

compose() {
  local project="$1"
  local file="$2"
  shift 2
  GUIDE_RUN_ID="$PREFIX" docker compose -p "$project" -f "$file" "$@"
}

cleanup() {
  compose "$SKELETON_PROJECT" "$SCRIPT_DIR/skeleton/compose.yaml" down --volumes --remove-orphans >/dev/null 2>&1 || true
  compose "$REFERENCE_PROJECT" "$SCRIPT_DIR/reference/compose.yaml" down --volumes --remove-orphans >/dev/null 2>&1 || true
}

signal_exit() {
  local code="$1"
  trap - EXIT HUP INT TERM
  cleanup
  exit "$code"
}

static_check() {
  python3 - "$SCRIPT_DIR" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
skeleton = (root / "skeleton/compose.yaml").read_text(encoding="utf-8")
reference = (root / "reference/compose.yaml").read_text(encoding="utf-8")

required_skeleton = {
    'KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "3"',
    'KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: "3"',
    'KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: "2"',
}
required_reference = {
    'KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: "1"',
    'KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: "1"',
    'KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: "1"',
}
missing = [value for value in required_skeleton if value not in skeleton]
missing += [value for value in required_reference if value not in reference]
if missing:
    raise SystemExit("missing expected KRaft settings: " + ", ".join(sorted(missing)))
for text in (skeleton, reference):
    if "apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837" not in text:
        raise SystemExit("Kafka image must pin the approved 4.3.1 immutable digest")
    if "pull_policy: never" not in text:
        raise SystemExit("KRaft verification must not pull during verify")
print("KRaft static contract verified")
PY

  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    compose "$SKELETON_PROJECT" "$SCRIPT_DIR/skeleton/compose.yaml" config >/dev/null
    compose "$REFERENCE_PROJECT" "$SCRIPT_DIR/reference/compose.yaml" config >/dev/null
  fi
}

wait_for_broker() {
  local project="$1"
  local file="$2"
  local attempt
  for attempt in $(seq 1 60); do
    if compose "$project" "$file" exec -T kafka \
      /opt/kafka/bin/kafka-topics.sh \
      --bootstrap-server localhost:9092 \
      --list >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  compose "$project" "$file" logs kafka >&2 || true
  return 1
}

run_case() {
  local name="$1"
  local project="$2"
  local file="$3"
  local expect_success="$4"
  local direct_output
  local broker_logs
  local output
  local status

  log "starting $name"
  compose "$project" "$file" up -d
  wait_for_broker "$project" "$file"

  compose "$project" "$file" exec -T kafka \
    /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --create \
    --if-not-exists \
    --topic guide-events \
    --partitions 1 \
    --replication-factor 1 >/dev/null

  printf '%s\n' "$MESSAGE" | compose "$project" "$file" exec -T kafka \
    /opt/kafka/bin/kafka-console-producer.sh \
    --bootstrap-server localhost:9092 \
    --topic guide-events >/dev/null

  direct_output="$(
    compose "$project" "$file" exec -T kafka \
      /opt/kafka/bin/kafka-console-consumer.sh \
      --bootstrap-server localhost:9092 \
      --topic guide-events \
      --partition 0 \
      --offset earliest \
      --max-messages 1 \
      --timeout-ms 12000 2>&1
  )" || {
    printf '%s\n' "$direct_output" >&2
    printf '%s direct partition consumer failed; group result would be ambiguous\n' "$name" >&2
    return 1
  }
  [[ "$direct_output" == *"$MESSAGE"* ]] || {
    printf '%s\n' "$direct_output" >&2
    printf '%s direct partition consumer did not read the message\n' "$name" >&2
    return 1
  }

  set +e
  output="$(
    compose "$project" "$file" exec -T kafka \
      /opt/kafka/bin/kafka-console-consumer.sh \
      --bootstrap-server localhost:9092 \
      --topic guide-events \
      --group guide-verification \
      --from-beginning \
      --max-messages 1 \
      --timeout-ms 12000 2>&1
  )"
  status=$?
  set -e

  if [[ "$expect_success" == "yes" ]]; then
    if [[ $status -ne 0 || "$output" != *"$MESSAGE"* ]]; then
      printf '%s\n' "$output" >&2
      printf 'reference group consumer did not read the message\n' >&2
      return 1
    fi
  else
    if [[ $status -eq 0 && "$output" == *"$MESSAGE"* ]]; then
      printf 'skeleton unexpectedly supported a group consumer\n' >&2
      return 1
    fi
    broker_logs="$(compose "$project" "$file" logs kafka 2>&1 || true)"
    if [[ "$broker_logs" != *"__consumer_offsets"* \
      || "$broker_logs" != *"INVALID_REPLICATION_FACTOR"* ]]; then
      printf '%s\n' "$output" >&2
      printf '%s\n' "$broker_logs" >&2
      printf 'skeleton group consumer did not fail at the designated internal-topic replication contract\n' >&2
      return 1
    fi
  fi

  compose "$project" "$file" down --volumes --remove-orphans >/dev/null
  log "$name behaved as expected"
}

case "${1:-}" in
  --cleanup)
    cleanup
    exit 0
    ;;
  --static)
    static_check
    exit 0
    ;;
  "")
    ;;
  *)
    printf 'usage: %s [--static|--cleanup]\n' "$0" >&2
    exit 2
    ;;
esac

static_check
command -v docker >/dev/null 2>&1 || {
  printf 'docker is required for the KRaft integration check\n' >&2
  exit 1
}
docker compose version >/dev/null 2>&1 || {
  printf 'Docker Compose v2 is required\n' >&2
  exit 1
}
docker info >/dev/null 2>&1 || {
  printf 'Docker daemon is not available\n' >&2
  exit 1
}

trap cleanup EXIT
trap 'signal_exit 129' HUP
trap 'signal_exit 130' INT
trap 'signal_exit 143' TERM
cleanup
run_case "misconfigured skeleton" "$SKELETON_PROJECT" "$SCRIPT_DIR/skeleton/compose.yaml" no
run_case "correct reference" "$REFERENCE_PROJECT" "$SCRIPT_DIR/reference/compose.yaml" yes
log "single-broker KRaft exercise verified"
