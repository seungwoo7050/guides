from __future__ import annotations

import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
VERSION = re.compile(r"^v[1-9][0-9]*$")


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


# [Implementation 1] Store and audit-key ownership
class SecretStore:
    def __init__(self, root: Path) -> None:
        if root.is_symlink():
            raise ValueError("secret store root may not be a symlink")
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.root.chmod(0o700)
        self.audit_key_path = self.root / "audit_hmac_key.bin"
        self._ensure_audit_key()
        self.audit_key = self.audit_key_path.read_bytes()
        if len(self.audit_key) != 32:
            raise ValueError("audit HMAC key must be exactly 32 bytes")

    def _ensure_audit_key(self) -> None:
        if self.audit_key_path.is_symlink():
            raise ValueError("audit HMAC key may not be a symlink")
        if not self.audit_key_path.exists():
            try:
                descriptor = os.open(
                    self.audit_key_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(secrets.token_bytes(32))
                    handle.flush()
                    os.fsync(handle.fileno())
                fsync_directory(self.root)
        self.audit_key_path.chmod(0o600)

    # [Implementation 2] Name, path, mode, and process-lock invariants
    def _directory(self, name: str) -> Path:
        if not NAME.fullmatch(name):
            raise ValueError("invalid secret name")
        directory = self.root / name
        if directory.is_symlink():
            raise ValueError("secret directory may not be a symlink")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
        versions = directory / "versions"
        if versions.is_symlink():
            raise ValueError("versions directory may not be a symlink")
        versions.mkdir(exist_ok=True, mode=0o700)
        versions.chmod(0o700)
        return directory

    @contextmanager
    def _locked(self, directory: Path) -> Iterator[None]:
        lock_path = directory / ".rotation.lock"
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    # [Implementation 3] Secret-safe audit fingerprints
    def _fingerprint(self, value: str) -> str:
        digest = hmac.new(self.audit_key, value.encode(), hashlib.sha256).hexdigest()
        return "hmac-sha256:" + digest[:16]

    def _event(self, event: str, name: str, version: str, fingerprint: str, detail: str = "") -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "name": name,
            "version": version,
            "fingerprint": fingerprint,
            "detail": detail,
        }
        payload = (json.dumps(record, sort_keys=True) + "\n").encode()
        event_path = self.root / "events.jsonl"
        descriptor = os.open(event_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    # [Implementation 4] Atomic version candidate
    def install(
        self,
        name: str,
        version: str,
        value: str,
        validator: Callable[[Path], bool],
    ) -> bool:
        if not VERSION.fullmatch(version):
            raise ValueError("invalid secret version")
        if not value or "\x00" in value or "\n" in value or "\r" in value:
            raise ValueError("secret value must be one non-empty line")
        directory = self._directory(name)
        versions = directory / "versions"

        with self._locked(directory):
            target = versions / version
            if target.exists() or target.is_symlink():
                raise FileExistsError(target)
            fingerprint = self._fingerprint(value)
            temporary = versions / f".{version}.{os.getpid()}.tmp"
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                    handle.write(value)
                    handle.flush()
                    os.fsync(handle.fileno())
                temporary.chmod(0o600)
                os.replace(temporary, target)
                target.chmod(0o600)
                fsync_directory(versions)
            except Exception:
                temporary.unlink(missing_ok=True)
                raise

            self._event("candidate-created", name, version, fingerprint)

            # [Implementation 5] Consumer validation and current pointer
            try:
                accepted = bool(validator(target))
            except Exception:
                accepted = False
                detail = "consumer validation raised"
            else:
                detail = "consumer validation failed"
            if not accepted:
                target.unlink(missing_ok=True)
                fsync_directory(versions)
                self._event("candidate-rejected", name, version, fingerprint, detail)
                return False

            previous = None
            current_path = directory / "current.json"
            if current_path.exists():
                previous = json.loads(current_path.read_text(encoding="utf-8")).get("version")
            pointer = {
                "version": version,
                "fingerprint": fingerprint,
                "previous": previous,
                "activated_at": datetime.now(timezone.utc).isoformat(),
            }
            pointer_tmp = directory / f".current.{os.getpid()}.tmp"
            try:
                with pointer_tmp.open("w", encoding="utf-8") as handle:
                    json.dump(pointer, handle, sort_keys=True)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                pointer_tmp.chmod(0o600)
                os.replace(pointer_tmp, current_path)
                current_path.chmod(0o600)
                fsync_directory(directory)
            finally:
                pointer_tmp.unlink(missing_ok=True)
            self._event("current-switched", name, version, fingerprint, f"previous={previous}")
            return True

    # [Implementation 6] Protected retirement lifecycle
    def current(self, name: str) -> dict[str, str | None]:
        directory = self._directory(name)
        path = directory / "current.json"
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(path)
        return json.loads(path.read_text(encoding="utf-8"))

    def secret_path(self, name: str, version: str | None = None) -> Path:
        directory = self._directory(name)
        selected = version or str(self.current(name)["version"])
        if not VERSION.fullmatch(selected):
            raise ValueError("invalid secret version")
        path = directory / "versions" / selected
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(path)
        return path

    def retire(self, name: str, version: str) -> None:
        if not VERSION.fullmatch(version):
            raise ValueError("invalid secret version")
        directory = self._directory(name)
        with self._locked(directory):
            current = self.current(name)
            if current.get("version") == version:
                raise ValueError("cannot retire current secret")
            target = directory / "versions" / version
            if not target.is_file() or target.is_symlink():
                raise FileNotFoundError(target)
            value = target.read_text(encoding="utf-8")
            fingerprint = self._fingerprint(value)
            target.unlink()
            fsync_directory(target.parent)
            self._event("version-retired", name, version, fingerprint)
