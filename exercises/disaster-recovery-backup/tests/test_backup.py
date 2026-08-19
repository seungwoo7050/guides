from __future__ import annotations

import gzip
import io
import json
import shutil
import tarfile
import tempfile
import unittest
from pathlib import Path

from backup import checksum, create_backup, restore_backup, validate_source, verify_backup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "examples/source"


# [Implementation 9] Recovery integrity verification
class BackupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)
        self.backups = self.workspace / "backups"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_create_verify_and_restore_round_trip(self) -> None:
        backup = create_backup(SOURCE, self.backups, "backup-001")
        manifest = verify_backup(self.backups)
        self.assertEqual(manifest["backup_id"], "backup-001")
        self.assertEqual((self.backups / "CURRENT").read_text(), "backup-001\n")
        target = self.workspace / "restored"
        restore_backup(self.backups, target)
        database, release, uploads = validate_source(target)
        self.assertEqual(database["latest_record_at"], "2026-08-07T01:55:00Z")
        self.assertEqual(release, "release-v1.4")
        self.assertEqual([str(path) for path in uploads], ["uploads/note-1.txt", "uploads/note-2.txt"])
        self.assertEqual((target / "uploads/note-2.txt").read_text(), "second attachment with unicode: 복구\n")
        self.assertEqual(backup.stat().st_mode & 0o777, 0o700)

    def test_upload_archive_is_deterministic_for_same_source(self) -> None:
        first = create_backup(SOURCE, self.backups, "backup-a")
        second = create_backup(SOURCE, self.backups, "backup-b")
        self.assertEqual(checksum(first / "uploads.tar.gz"), checksum(second / "uploads.tar.gz"))
        self.assertEqual(checksum(first / "database.json"), checksum(second / "database.json"))

    def test_corruption_is_detected_before_target_publication(self) -> None:
        backup = create_backup(SOURCE, self.backups, "backup-corrupt")
        with (backup / "database.json").open("ab") as handle:
            handle.write(b"corrupt")
        target = self.workspace / "must-not-exist"
        with self.assertRaisesRegex(ValueError, "artifact integrity mismatch"):
            restore_backup(self.backups, target, "backup-corrupt")
        self.assertFalse(target.exists())

    def test_archive_traversal_is_rejected_even_with_updated_manifest(self) -> None:
        backup = create_backup(SOURCE, self.backups, "backup-malicious")
        archive_path = backup / "uploads.tar.gz"
        with archive_path.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w") as archive:
                    payload = b"escape"
                    info = tarfile.TarInfo("../escape.txt")
                    info.size = len(payload)
                    archive.addfile(info, io.BytesIO(payload))
        manifest_path = backup / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["artifacts"]["uploads.tar.gz"] = {
            "sha256": checksum(archive_path),
            "size": archive_path.stat().st_size,
        }
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
        with self.assertRaisesRegex(ValueError, "upload path must be relative|unsafe upload path"):
            restore_backup(self.backups, self.workspace / "target", "backup-malicious")
        self.assertFalse((self.workspace / "escape.txt").exists())

    def test_source_upload_checksum_mismatch_is_rejected(self) -> None:
        source = self.workspace / "source"
        shutil.copytree(SOURCE, source)
        (source / "uploads/note-1.txt").write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "upload checksum mismatch"):
            create_backup(source, self.backups, "backup-invalid")


if __name__ == "__main__":
    unittest.main()
