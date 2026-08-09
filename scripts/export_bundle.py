#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from process_runner import CommandSpawnError, run_process
from source_manifest import SourceManifestError, build_manifest, copy_source_subset

ROOT = Path(__file__).resolve().parents[1]
EXPO = ROOT / "node_modules/.bin/expo"


def fail(message: str, output: str = "") -> None:
    detail = f"\n{output[-5000:]}" if output else ""
    raise SystemExit(f"BUNDLE ERROR: {message}{detail}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def regular_output_file(output: Path, raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute() or ".." in Path(raw).parts:
        fail(f"{label} path가 안전한 relative path가 아닙니다: {raw!r}")
    candidate = output / raw
    try:
        metadata = candidate.lstat()
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(output.resolve(strict=True))
    except (FileNotFoundError, OSError, ValueError) as error:
        fail(f"{label}가 output root 안의 existing file이 아닙니다: {raw!r}: {error}")
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        fail(f"{label}가 regular non-symlink file이 아닙니다: {raw!r}")
    return candidate


def output_manifest(output: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    files: list[Path] = []
    pending = [output]
    while pending:
        directory = pending.pop()
        for path in sorted(directory.iterdir(), key=lambda candidate: candidate.name):
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                fail(f"bundle output symlink는 허용하지 않습니다: {path.relative_to(output)}")
            if stat.S_ISDIR(metadata.st_mode):
                pending.append(path)
            elif stat.S_ISREG(metadata.st_mode):
                files.append(path)
            else:
                fail(f"bundle output special entry는 허용하지 않습니다: {path.relative_to(output)}")
    for path in sorted(files, key=lambda candidate: candidate.relative_to(output).as_posix()):
        relative = path.relative_to(output).as_posix()
        size = path.stat().st_size
        digest.update(relative.encode() + b"\0" + str(size).encode() + b"\0")
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        digest.update(b"\0")
    return digest.hexdigest(), len(files)


def validate_bundle_output(output: Path, platform: str) -> dict[str, object]:
    metadata_path = regular_output_file(output, "metadata.json", "metadata")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"metadata JSON을 읽지 못했습니다: {error}")
    if not isinstance(metadata, dict) or metadata.get("bundler") != "metro":
        fail("metadata가 Metro export contract를 보고하지 않습니다.")
    file_metadata = metadata.get("fileMetadata")
    if not isinstance(file_metadata, dict) or set(file_metadata) != {platform}:
        fail(
            f"metadata platform이 요청과 정확히 일치하지 않습니다: expected={platform} "
            f"actual={sorted(file_metadata) if isinstance(file_metadata, dict) else file_metadata!r}"
        )
    platform_metadata = file_metadata[platform]
    if not isinstance(platform_metadata, dict):
        fail(f"metadata.{platform}가 object가 아닙니다.")
    bundle = regular_output_file(output, platform_metadata.get("bundle"), "referenced bundle")
    assets = platform_metadata.get("assets")
    if not isinstance(assets, list):
        fail(f"metadata.{platform}.assets가 list가 아닙니다.")
    asset_paths: list[str] = []
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict):
            fail(f"asset metadata가 object가 아닙니다: index={index}")
        asset_file = regular_output_file(output, asset.get("path"), f"asset[{index}]")
        asset_paths.append(asset_file.relative_to(output).as_posix())
    manifest_sha, file_count = output_manifest(output)
    return {
        "platform": platform,
        "bundle_path": bundle.relative_to(output).as_posix(),
        "bundle_sha256": sha256(bundle),
        "artifact_manifest_sha256": manifest_sha,
        "artifact_file_count": file_count,
        "referenced_asset_count": len(asset_paths),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export an Expo bundle in isolated generated state")
    parser.add_argument("--project", choices=("reference", "skeleton"), required=True)
    parser.add_argument("--platform", choices=("android", "ios"), required=True)
    args = parser.parse_args()

    if not EXPO.is_file() or not (ROOT / "node_modules").is_dir():
        fail("dependencies가 없습니다. 먼저 ./prepare.sh를 실행하십시오.")
    relative_source = Path(f"exercises/field-notes/{args.project}")
    try:
        manifest = build_manifest(ROOT)
    except SourceManifestError as error:
        fail(str(error))

    with tempfile.TemporaryDirectory(prefix=f"mobile-app-{args.project}-{args.platform}-") as temporary:
        temporary_root = Path(temporary)
        project = temporary_root / "project"
        output = temporary_root / "bundle"
        try:
            copied = copy_source_subset(
                ROOT, relative_source, project, entries=manifest
            )
        except SourceManifestError as error:
            fail(str(error))
        (project / "node_modules").symlink_to(ROOT / "node_modules", target_is_directory=True)
        try:
            result = run_process(
                [
                    str(EXPO),
                    "export",
                    "--platform",
                    args.platform,
                    "--output-dir",
                    str(output),
                    "--clear",
                ],
                cwd=project,
                timeout_seconds=600,
                env={**os.environ, "CI": "1", "EXPO_NO_TELEMETRY": "1"},
                combine_output=True,
                grace_seconds=5,
            )
        except CommandSpawnError as error:
            fail(str(error))
        combined = result.stdout.strip()
        if result.timed_out:
            fail("Expo export timed out; process group을 종료했습니다.", combined)
        if result.returncode != 0:
            fail(f"Expo export failed exit={result.returncode}", combined)
        evidence = {
            "project": args.project,
            "copied_source_files": copied,
            **validate_bundle_output(output, args.platform),
        }
        print(
            f"BUNDLE OK project={args.project} platform={args.platform} "
            f"files={evidence['artifact_file_count']} "
            f"bundle_sha256={evidence['bundle_sha256']} "
            f"artifact_manifest_sha256={evidence['artifact_manifest_sha256']}"
        )
        print("EVIDENCE_JSON " + json.dumps(evidence, ensure_ascii=False, sort_keys=True))
        print("BUNDLE LIMIT: export is not native compile, signing, install, device, or store evidence")


if __name__ == "__main__":
    main()
