#!/usr/bin/env python3
"""Build and attest the digest, snapshot, and package-pinned Linux verifier."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

BASE_IMAGE = "python:3.12-slim-bookworm@sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2"
TAG = "guide-computer-networks-e2e:python-3.12-bookworm"
DEBIAN_SNAPSHOT = "20260803T000000Z"
RECIPE = "3"
PACKAGES = {
    "ca-certificates": "20230311+deb12u1",
    "grep": "3.8-5",
    "iproute2": "6.1.0-3",
    "iptables": "1.8.9-2",
    "iputils-ping": "3:20221126-1+deb12u1",
    "make": "4.3-4.1",
    "procps": "2:4.0.2-3",
    "tcpdump": "4.99.3-1",
}
PACKAGE_LOCK = ",".join(f"{name}={version}" for name, version in sorted(PACKAGES.items()))
PACKAGE_ARGUMENTS = " ".join(f"{name}={version}" for name, version in sorted(PACKAGES.items()))

DOCKERFILE = f"""FROM {BASE_IMAGE}
RUN printf '%s\\n' \\
      'Types: deb' \\
      'URIs: http://snapshot.debian.org/archive/debian/{DEBIAN_SNAPSHOT}' \\
      'Suites: bookworm bookworm-updates' \\
      'Components: main' \\
      'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \\
      '' \\
      'Types: deb' \\
      'URIs: http://snapshot.debian.org/archive/debian-security/{DEBIAN_SNAPSHOT}' \\
      'Suites: bookworm-security' \\
      'Components: main' \\
      'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \\
      > /etc/apt/sources.list.d/debian.sources \\
 && printf '%s\\n' 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99snapshot \\
 && apt-get update \\
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends {PACKAGE_ARGUMENTS} \\
 && rm -rf /var/lib/apt/lists/*
LABEL guide.computer-networks.verifier="1" \\
      guide.computer-networks.base-image="{BASE_IMAGE}" \\
      guide.computer-networks.debian-snapshot="{DEBIAN_SNAPSHOT}" \\
      guide.computer-networks.package-lock="{PACKAGE_LOCK}" \\
      guide.computer-networks.recipe="{RECIPE}"
"""


def run(*arguments: str, input_text: str | None = None) -> str:
    result = subprocess.run(
        ["docker", *arguments],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def expected_labels() -> dict[str, str]:
    return {
        "guide.computer-networks.verifier": "1",
        "guide.computer-networks.base-image": BASE_IMAGE,
        "guide.computer-networks.debian-snapshot": DEBIAN_SNAPSHOT,
        "guide.computer-networks.package-lock": PACKAGE_LOCK,
        "guide.computer-networks.recipe": RECIPE,
    }


def image_labels(reference: str) -> dict[str, str]:
    raw = run("image", "inspect", "--format", "{{json .Config.Labels}}", reference)
    labels = json.loads(raw)
    if not isinstance(labels, dict):
        raise RuntimeError("verifier image labels가 object가 아닙니다")
    return {str(key): str(value) for key, value in labels.items()}


def installed_packages(reference: str) -> dict[str, str]:
    output = run("run", "--rm", "--pull=never", reference, "dpkg-query", "-W", *sorted(PACKAGES))
    installed: dict[str, str] = {}
    for line in output.splitlines():
        name, version = line.split("\t", 1)
        installed[name] = version
    return installed


def image_is_current() -> bool:
    try:
        return all(image_labels(TAG).get(key) == value for key, value in expected_labels().items())
    except (RuntimeError, json.JSONDecodeError):
        return False


def state_payload() -> dict[str, object]:
    image_id = run("image", "inspect", "--format", "{{.Id}}", TAG)
    actual_packages = installed_packages(image_id)
    if actual_packages != PACKAGES:
        raise RuntimeError(f"verifier package lock 불일치: expected={PACKAGES}, actual={actual_packages}")
    labels = image_labels(image_id)
    for key, value in expected_labels().items():
        if labels.get(key) != value:
            raise RuntimeError(f"verifier image label 불일치: {key}")
    return {
        "base_image": BASE_IMAGE,
        "debian_snapshot": DEBIAN_SNAPSHOT,
        "package_versions": PACKAGES,
        "recipe": RECIPE,
        "verifier_image": TAG,
        "verifier_image_id": image_id,
    }


def check_state(path: Path) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "base_image": BASE_IMAGE,
        "debian_snapshot": DEBIAN_SNAPSHOT,
        "package_versions": PACKAGES,
        "recipe": RECIPE,
        "verifier_image": TAG,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise RuntimeError(f"prepare marker image field 불일치: {key}")
    current = state_payload()
    if payload.get("verifier_image_id") != current["verifier_image_id"]:
        raise RuntimeError("prepare marker verifier image ID가 현재 tag와 다릅니다")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--print-state", action="store_true")
    mode.add_argument("--check-state", type=Path)
    args = parser.parse_args()
    try:
        if args.check_state is not None:
            check_state(args.check_state)
            print("verifier image digest/snapshot/package attestation: PASS")
            return 0
        run("pull", BASE_IMAGE)
        if not image_is_current():
            run("build", "--pull=false", "--tag", TAG, "-", input_text=DOCKERFILE)
        payload = state_payload()
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError, ValueError) as error:
        print(f"verifier image 준비/검증 실패: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
