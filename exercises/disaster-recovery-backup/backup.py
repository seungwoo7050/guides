#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import tarfile
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

BACKUP_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


# [Implementation 1] Durable checksum and pointer primitives
def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_text(path: Path, text: str, mode: int = 0o600) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _safe_upload_path(value: Any) -> PurePosixPath:
    if not isinstance(value, str):
        raise ValueError("upload path must be a string")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or path.parts[0] != "uploads":
        raise ValueError(f"upload path must be relative to uploads/: {value}")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"unsafe upload path: {value}")
    return path


# [Implementation 2] Source snapshot and path validation
def validate_source(source: Path) -> tuple[dict[str, Any], str, list[PurePosixPath]]:
    if source.is_symlink() or not source.is_dir():
        raise ValueError("source must be a real directory")
    database_path = source / "database.json"
    release_path = source / "release.txt"
    try:
        database = json.loads(database_path.read_text(encoding="utf-8"))
        release = release_path.read_text(encoding="utf-8").strip()
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"source snapshot is unreadable: {exc}") from exc
    if not isinstance(database, dict):
        raise ValueError("database.json root must be an object")
    if not isinstance(database.get("schema_version"), int) or database["schema_version"] <= 0:
        raise ValueError("database schema_version must be a positive integer")
    if not isinstance(database.get("latest_record_at"), str) or not database["latest_record_at"]:
        raise ValueError("database latest_record_at is required")
    notes = database.get("notes")
    if not isinstance(notes, list):
        raise ValueError("database notes must be an array")
    if not release or "\n" in release or "\r" in release:
        raise ValueError("release.txt must contain one non-empty line")

    upload_paths: list[PurePosixPath] = []
    seen: set[PurePosixPath] = set()
    for index, note in enumerate(notes):
        if not isinstance(note, dict):
            raise ValueError(f"notes[{index}] must be an object")
        relative = _safe_upload_path(note.get("upload"))
        if relative in seen:
            raise ValueError(f"duplicate upload path: {relative}")
        seen.add(relative)
        upload = source.joinpath(*relative.parts)
        if upload.is_symlink() or not upload.is_file():
            raise ValueError(f"upload is not a regular file: {relative}")
        expected = note.get("upload_sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"notes[{index}].upload_sha256 is invalid")
        if checksum(upload) != expected:
            raise ValueError(f"upload checksum mismatch: {relative}")
        upload_paths.append(relative)
    return database, release, sorted(upload_paths, key=str)


# [Implementation 3] Deterministic archive entries
def write_upload_archive(source: Path, uploads: list[PurePosixPath], destination: Path) -> None:
    with destination.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for relative in uploads:
                    file_path = source.joinpath(*relative.parts)
                    info = tarfile.TarInfo(str(relative))
                    info.size = file_path.stat().st_size
                    info.mode = 0o600
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    with file_path.open("rb") as handle:
                        archive.addfile(info, handle)
        raw.flush()
        os.fsync(raw.fileno())


# [Implementation 4] Staged backup artifact and manifest
def create_backup(source: Path, backup_root: Path, backup_id: str) -> Path:
    if not BACKUP_ID.fullmatch(backup_id):
        raise ValueError("invalid backup id")
    backup_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup_root.chmod(0o700)
    final = backup_root / backup_id
    if final.exists() or final.is_symlink():
        raise FileExistsError(final)
    database, release, uploads = validate_source(source)
    candidate = backup_root / f".candidate.{uuid.uuid4().hex}"
    candidate.mkdir(mode=0o700)
    try:
        database_path = candidate / "database.json"
        release_path = candidate / "release.txt"
        archive_path = candidate / "uploads.tar.gz"
        atomic_text(database_path, json.dumps(database, sort_keys=True, separators=(",", ":")) + "\n")
        atomic_text(release_path, release + "\n")
        write_upload_archive(source, uploads, archive_path)
        archive_path.chmod(0o600)
        manifest = {
            "schema_version": 1,
            "backup_id": backup_id,
            "source": {
                "database_schema": database["schema_version"],
                "latest_record_at": database["latest_record_at"],
                "release": release,
                "upload_count": len(uploads),
            },
            "artifacts": {
                name: {"sha256": checksum(candidate / name), "size": (candidate / name).stat().st_size}
                for name in ("database.json", "release.txt", "uploads.tar.gz")
            },
        }
        atomic_text(candidate / "manifest.json", json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        for path in candidate.iterdir():
            if path.is_file():
                path.chmod(0o600)

        # [Implementation 5] Atomic backup publication
        os.replace(candidate, final)
        fsync_directory(backup_root)
        atomic_text(backup_root / "CURRENT", backup_id + "\n")
        return final
    except Exception:
        shutil.rmtree(candidate, ignore_errors=True)
        raise


def select_backup(backup_root: Path, backup_id: str | None) -> Path:
    if backup_id is None:
        try:
            backup_id = (backup_root / "CURRENT").read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ValueError(f"CURRENT pointer is unreadable: {exc}") from exc
    if not BACKUP_ID.fullmatch(backup_id):
        raise ValueError("invalid backup id")
    path = backup_root / backup_id
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"backup is not a real directory: {backup_id}")
    return path


def verify_backup(backup_root: Path, backup_id: str | None = None) -> dict[str, Any]:
    backup = select_backup(backup_root, backup_id)
    try:
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"manifest is unreadable: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("unsupported backup manifest")
    if manifest.get("backup_id") != backup.name:
        raise ValueError("manifest backup_id does not match directory")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("manifest artifacts must be an object")
    for name in ("database.json", "release.txt", "uploads.tar.gz"):
        metadata = artifacts.get(name)
        path = backup / name
        if not isinstance(metadata, dict) or path.is_symlink() or not path.is_file():
            raise ValueError(f"artifact is missing or invalid: {name}")
        if metadata.get("sha256") != checksum(path) or metadata.get("size") != path.stat().st_size:
            raise ValueError(f"artifact integrity mismatch: {name}")
    return manifest


# [Implementation 6] Safe restore extraction
def extract_uploads(archive_path: Path, target: Path) -> None:
    target.mkdir(mode=0o700)
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            relative = _safe_upload_path(member.name)
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f"archive member is not a regular file: {member.name}")
            destination = target.joinpath(*relative.parts[1:])
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            extracted = archive.extractfile(member)
            if extracted is None:
                raise ValueError(f"archive member cannot be read: {member.name}")
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                shutil.copyfileobj(extracted, handle)
                handle.flush()
                os.fsync(handle.fileno())


# [Implementation 7] Atomic restore publication
def restore_backup(backup_root: Path, target: Path, backup_id: str | None = None) -> Path:
    if target.exists() or target.is_symlink():
        raise FileExistsError("restore target must not exist")
    manifest = verify_backup(backup_root, backup_id)
    backup = select_backup(backup_root, str(manifest["backup_id"]))
    target.parent.mkdir(parents=True, exist_ok=True)
    candidate = target.parent / f".{target.name}.restore.{uuid.uuid4().hex}"
    candidate.mkdir(mode=0o700)
    try:
        shutil.copyfile(backup / "database.json", candidate / "database.json")
        shutil.copyfile(backup / "release.txt", candidate / "release.txt")
        (candidate / "database.json").chmod(0o600)
        (candidate / "release.txt").chmod(0o600)
        extract_uploads(backup / "uploads.tar.gz", candidate / "uploads")
        validate_source(candidate)
        for path in (candidate / "database.json", candidate / "release.txt"):
            with path.open("rb") as handle:
                os.fsync(handle.fileno())
        fsync_directory(candidate / "uploads")
        fsync_directory(candidate)
        os.replace(candidate, target)
        fsync_directory(target.parent)
        return target
    except Exception:
        shutil.rmtree(candidate, ignore_errors=True)
        raise


# [Implementation 8] Backup and restore CLI
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create, verify, and restore a self-contained application backup.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create")
    create.add_argument("source", type=Path)
    create.add_argument("backup_root", type=Path)
    create.add_argument("backup_id")
    verify = subparsers.add_parser("verify")
    verify.add_argument("backup_root", type=Path)
    verify.add_argument("--backup-id")
    restore = subparsers.add_parser("restore")
    restore.add_argument("backup_root", type=Path)
    restore.add_argument("target", type=Path)
    restore.add_argument("--backup-id")
    args = parser.parse_args(argv)
    try:
        if args.command == "create":
            result = create_backup(args.source, args.backup_root, args.backup_id)
            print(result)
        elif args.command == "verify":
            result = verify_backup(args.backup_root, args.backup_id)
            print(json.dumps(result, sort_keys=True))
        else:
            result = restore_backup(args.backup_root, args.target, args.backup_id)
            print(result)
    except (ValueError, FileExistsError) as exc:
        print(f"error: {exc}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
