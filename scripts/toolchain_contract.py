#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from process_runner import CommandSpawnError, run_process

ROOT = Path(__file__).resolve().parents[1]


def command_version(command: list[str]) -> str:
    try:
        result = run_process(command, cwd=ROOT, timeout_seconds=15)
    except CommandSpawnError as error:
        raise SystemExit(f"TOOLCHAIN ERROR: {error}") from error
    if result.timed_out:
        raise SystemExit(f"TOOLCHAIN ERROR: {' '.join(command)} timed out")
    if result.returncode != 0:
        raise SystemExit(
            f"TOOLCHAIN ERROR: {' '.join(command)} failed: {(result.stderr or result.stdout).strip()}"
        )
    return result.stdout.strip().removeprefix("v")


def contract() -> dict[str, str]:
    return json.loads((ROOT / "toolchain.json").read_text())


def validate() -> dict[str, str]:
    expected = contract()
    package = json.loads((ROOT / "package.json").read_text())
    nvmrc = (ROOT / ".nvmrc").read_text().strip()

    declarations = {
        ".nvmrc": nvmrc,
        "packageManager": package.get("packageManager"),
        "engines.node": package.get("engines", {}).get("node"),
        "engines.npm": package.get("engines", {}).get("npm"),
    }
    required = {
        ".nvmrc": expected["node"],
        "packageManager": f"npm@{expected['npm']}",
        "engines.node": expected["nodeEngine"],
        "engines.npm": expected["npmEngine"],
    }
    drift = [
        f"{key}: expected={required[key]!r} actual={value!r}"
        for key, value in declarations.items()
        if value != required[key]
    ]
    if drift:
        raise SystemExit("TOOLCHAIN ERROR: version 정본 drift: " + "; ".join(drift))

    python_minimum = tuple(int(part) for part in expected["pythonMinimum"].split("."))
    if sys.version_info[:2] < python_minimum:
        raise SystemExit(
            f"TOOLCHAIN ERROR: Python {expected['pythonMinimum']}+ required; "
            f"actual={sys.version.split()[0]}"
        )

    actual = {
        "node": command_version(["node", "--version"]),
        "npm": command_version(["npm", "--version"]),
        "python": sys.version.split()[0],
    }
    for key in ("node", "npm"):
        if actual[key] != expected[key]:
            raise SystemExit(
                f"TOOLCHAIN ERROR: {key} {expected[key]} required; actual={actual[key]}"
            )
    return actual


def main() -> None:
    actual = validate()
    print(
        f"TOOLCHAIN OK node={actual['node']} npm={actual['npm']} python={actual['python']}"
    )


if __name__ == "__main__":
    main()
