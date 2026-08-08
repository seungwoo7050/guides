from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tarfile
from pathlib import Path
from typing import Any, BinaryIO

BACKUP_ID = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{6}Z$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_text(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    fsync_directory(path.parent)


def safe_relative_path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is empty")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or relative.parts[:1] != ("uploads",):
        raise ValueError(f"{label} is unsafe: {value}")
    return relative


def validate_source_snapshot(source: Path, database: Path, uploads: Path) -> dict[str, Any]:
    db_data = json.loads(database.read_text(encoding="utf-8"))
    if not isinstance(db_data, dict) or not isinstance(db_data.get("notes"), list):
        raise ValueError("database snapshot schema is invalid")
    for path in uploads.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"upload symlink is not allowed: {path.relative_to(source)}")
        if not path.is_file() and not path.is_dir():
            raise ValueError(f"special upload entry is not allowed: {path.relative_to(source)}")
    for index, note in enumerate(db_data["notes"]):
        if not isinstance(note, dict):
            raise ValueError(f"note {index} is invalid")
        relative = safe_relative_path(note.get("upload"), f"note {index} upload")
        upload = source / relative
        try:
            upload.resolve().relative_to(uploads.resolve())
        except ValueError as exc:
            raise ValueError(f"note {index} upload escapes uploads") from exc
        if not upload.is_file() or upload.is_symlink():
            raise ValueError(f"referenced upload is missing or unsafe: {relative}")
        expected = note.get("upload_sha256")
        if not isinstance(expected, str) or sha256(upload) != expected:
            raise ValueError(f"upload checksum mismatch in source snapshot: {relative}")
    return db_data


def add_regular_file(archive: tarfile.TarFile, path: Path, arcname: Path) -> None:
    info = archive.gettarinfo(str(path), arcname=str(arcname))
    if not info.isfile():
        raise ValueError(f"backup source is not a regular file: {path}")
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.mode = 0o600
    with path.open("rb") as handle:
        archive.addfile(info, handle)


def create_backup(source: Path, destination: Path, backup_id: str, created_at: str) -> Path:
    if not BACKUP_ID.fullmatch(backup_id):
        raise ValueError("invalid backup id")
    if not isinstance(created_at, str) or not created_at.endswith("Z"):
        raise ValueError("created_at must be a UTC timestamp")
    database = source / "database.json"
    uploads = source / "uploads"
    release_file = source / "release.txt"
    if not database.is_file() or database.is_symlink() or not uploads.is_dir() or not release_file.is_file():
        raise ValueError("source is incomplete or unsafe")
    release = release_file.read_text(encoding="utf-8").strip()
    if not release:
        raise ValueError("release is empty")
    db_data = validate_source_snapshot(source, database, uploads)

    destination.mkdir(parents=True, exist_ok=True)
    final = destination / backup_id
    if final.exists():
        raise FileExistsError(final)
    stage = destination / f".{backup_id}.{os.getpid()}.tmp"
    stage.mkdir(mode=0o700)
    try:
        db_target = stage / "database.json"
        shutil.copyfile(database, db_target, follow_symlinks=False)
        db_target.chmod(0o600)
        fsync_file(db_target)

        upload_target = stage / "uploads.tar.gz"
        with tarfile.open(upload_target, "w:gz") as archive:
            for path in sorted(uploads.rglob("*")):
                if path.is_symlink():
                    raise ValueError(f"upload symlink is not allowed: {path.relative_to(source)}")
                if path.is_file():
                    add_regular_file(
                        archive,
                        path,
                        Path("uploads") / path.relative_to(uploads),
                    )
        upload_target.chmod(0o600)
        fsync_file(upload_target)

        artifacts = []
        for path in (db_target, upload_target):
            artifacts.append(
                {
                    "name": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "backup_id": backup_id,
            "created_at": created_at,
            "source": {
                "release": release,
                "database_schema": db_data.get("schema_version"),
                "latest_record_at": db_data.get("latest_record_at"),
            },
            "consistency": {"method": "single-read-only-snapshot", "complete": True},
            "artifacts": artifacts,
        }
        manifest_path = stage / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        manifest_path.chmod(0o600)
        fsync_directory(stage)

        os.replace(stage, final)
        fsync_directory(destination)
        atomic_text(destination / "CURRENT", backup_id + "\n")
        return final
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def copy_archive_member(source: BinaryIO, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            shutil.copyfileobj(source, handle, length=1024 * 1024)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise


def safe_extract(archive: tarfile.TarFile, target: Path) -> None:
    target_resolved = target.resolve()
    members = archive.getmembers()
    for member in members:
        if not member.isfile():
            raise ValueError(f"only regular files are allowed in backup archive: {member.name}")
        relative = safe_relative_path(member.name, "archive member")
        member_path = (target / relative).resolve()
        try:
            member_path.relative_to(target_resolved)
        except ValueError as exc:
            raise ValueError(f"unsafe archive path: {member.name}") from exc
        source = archive.extractfile(member)
        if source is None:
            raise ValueError(f"archive member has no data: {member.name}")
        with source:
            copy_archive_member(source, member_path)


def validate_restored_snapshot(stage: Path) -> dict[str, Any]:
    database = stage / "database.json"
    db_data = json.loads(database.read_text(encoding="utf-8"))
    if not isinstance(db_data, dict) or not isinstance(db_data.get("notes"), list):
        raise ValueError("restored database schema is invalid")
    stage_resolved = stage.resolve()
    for index, note in enumerate(db_data["notes"]):
        if not isinstance(note, dict):
            raise ValueError(f"restored note {index} is invalid")
        relative = safe_relative_path(note.get("upload"), f"restored note {index} upload")
        upload = (stage / relative).resolve()
        try:
            upload.relative_to(stage_resolved)
        except ValueError as exc:
            raise ValueError(f"restored upload escapes target: {relative}") from exc
        if not upload.is_file() or upload.is_symlink():
            raise ValueError(f"referenced upload missing or unsafe: {relative}")
        if sha256(upload) != note.get("upload_sha256"):
            raise ValueError(f"upload checksum mismatch: {relative}")
    return db_data


def restore_backup(backup_directory: Path, target: Path) -> dict[str, Any]:
    manifest_path = backup_directory / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("manifest missing or unsafe")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("consistency", {}).get("complete") is not True:
        raise ValueError("manifest is incomplete")
    artifact_by_name = {
        item.get("name"): item
        for item in manifest.get("artifacts", [])
        if isinstance(item, dict)
    }
    for name in ("database.json", "uploads.tar.gz"):
        item = artifact_by_name.get(name)
        path = backup_directory / name
        if not isinstance(item, dict) or not path.is_file() or path.is_symlink():
            raise ValueError(f"artifact missing or unsafe: {name}")
        if path.stat().st_size != item.get("bytes") or sha256(path) != item.get("sha256"):
            raise ValueError(f"artifact checksum mismatch: {name}")

    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("restore target is not an empty directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.parent / f".{target.name}.restore.{os.getpid()}.tmp"
    stage.mkdir(mode=0o700)
    try:
        db_target = stage / "database.json"
        shutil.copyfile(backup_directory / "database.json", db_target, follow_symlinks=False)
        db_target.chmod(0o600)
        fsync_file(db_target)
        with tarfile.open(backup_directory / "uploads.tar.gz", "r:gz") as archive:
            safe_extract(archive, stage)
        db_data = validate_restored_snapshot(stage)
        fsync_directory(stage)

        if target.exists():
            target.rmdir()
        os.replace(stage, target)
        fsync_directory(target.parent)
        return {
            "status": "restored",
            "backup_id": manifest.get("backup_id"),
            "release": manifest.get("source", {}).get("release"),
            "latest_record_at": db_data.get("latest_record_at"),
            "notes": len(db_data.get("notes", [])),
        }
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
