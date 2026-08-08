#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import hashlib
import io
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("backup_solution", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"skeleton", "reference"}:
        print("사용법: verify.py [skeleton|reference]", file=sys.stderr)
        return 2
    module = load_module(ROOT / sys.argv[1] / "backup.py")
    errors: list[str] = []
    source = ROOT / "fixtures" / "source"

    with tempfile.TemporaryDirectory() as temp:
        temp_root = Path(temp)
        destination = temp_root / "backups"
        try:
            backup = module.create_backup(
                source,
                destination,
                "2026-08-07T020000Z",
                "2026-08-07T02:00:00Z",
            )
        except Exception as exc:
            print(f"backup·restore 검사 실패: create_backup 예외: {exc}", file=sys.stderr)
            return 1
        if not isinstance(backup, Path):
            errors.append("create_backup은 생성한 backup Path를 반환해야 합니다.")
        manifest_path = backup / "manifest.json"
        current_path = destination / "CURRENT"
        if not manifest_path.is_file():
            errors.append("manifest.json이 없습니다.")
        if not current_path.is_file() or current_path.read_text().strip() != backup.name:
            errors.append("완성된 backup 뒤 CURRENT pointer가 올바르지 않습니다.")
        if errors:
            print(f"backup·restore 검사 실패: {len(errors)}건", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"manifest를 읽을 수 없습니다: {exc}")
            manifest = {}
        artifacts = manifest.get("artifacts", [])
        if {item.get("name") for item in artifacts if isinstance(item, dict)} != {"database.json", "uploads.tar.gz"}:
            errors.append("database와 uploads artifact metadata가 없습니다.")
        for item in artifacts:
            if not isinstance(item, dict) or not isinstance(item.get("bytes"), int) or item.get("bytes", 0) <= 0:
                errors.append(f"artifact size가 올바르지 않습니다: {item}")
            if not isinstance(item.get("sha256"), str) or len(item.get("sha256", "")) != 64:
                errors.append(f"artifact sha256이 올바르지 않습니다: {item}")

        restore = temp_root / "restore"
        try:
            result = module.restore_backup(backup, restore)
        except Exception as exc:
            errors.append(f"정상 backup 복원이 실패했습니다: {exc}")
            result = {}
        if result.get("status") != "restored" or result.get("notes") != 2:
            errors.append(f"복원 결과가 올바르지 않습니다: {result}")
        try:
            restored_db = json.loads((restore / "database.json").read_text(encoding="utf-8"))
            if len(restored_db.get("notes", [])) != 2:
                errors.append("복원된 database row 수가 다릅니다.")
            if not (restore / "uploads" / "note-1.txt").is_file() or not (restore / "uploads" / "note-2.txt").is_file():
                errors.append("복원된 upload가 없습니다.")
        except Exception as exc:
            errors.append(f"복원 결과를 읽을 수 없습니다: {exc}")

        nonempty = temp_root / "nonempty"
        nonempty.mkdir()
        (nonempty / "keep.txt").write_text("do not overwrite\n", encoding="utf-8")
        try:
            module.restore_backup(backup, nonempty)
            errors.append("비어 있지 않은 대상 덮어쓰기를 허용했습니다.")
        except (ValueError, FileExistsError):
            pass
        except Exception as exc:
            errors.append(f"비어 있지 않은 대상에서 예상하지 않은 예외입니다: {exc}")

        corrupt = temp_root / "corrupt"
        shutil.copytree(backup, corrupt)
        with (corrupt / "uploads.tar.gz").open("ab") as handle:
            handle.write(b"corruption")
        try:
            module.restore_backup(corrupt, temp_root / "corrupt-restore")
            errors.append("손상된 artifact 복원을 허용했습니다.")
        except (ValueError, OSError):
            pass
        except Exception as exc:
            errors.append(f"손상 artifact에서 예상하지 않은 예외입니다: {exc}")

        if (source / "manifest.json").exists() or (source / "CURRENT").exists():
            errors.append("create_backup이 source를 수정했습니다.")

        malicious = temp_root / "malicious"
        shutil.copytree(backup, malicious)
        payload = b"must-not-escape\n"
        with tarfile.open(malicious / "uploads.tar.gz", "w:gz") as archive:
            info = tarfile.TarInfo("../escape.txt")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        malicious_manifest = json.loads((malicious / "manifest.json").read_text(encoding="utf-8"))
        for item in malicious_manifest.get("artifacts", []):
            if item.get("name") == "uploads.tar.gz":
                item["bytes"] = (malicious / "uploads.tar.gz").stat().st_size
                item["sha256"] = sha256(malicious / "uploads.tar.gz")
        (malicious / "manifest.json").write_text(
            json.dumps(malicious_manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        malicious_target = temp_root / "malicious-restore"
        try:
            module.restore_backup(malicious, malicious_target)
            errors.append("경로 탈출 archive 복원을 허용했습니다.")
        except (ValueError, OSError):
            pass
        except Exception as exc:
            errors.append(f"악성 archive에서 예상하지 않은 예외입니다: {exc}")
        if (temp_root / "escape.txt").exists():
            errors.append("악성 archive가 restore target 밖에 파일을 만들었습니다.")
        if malicious_target.exists() and any(malicious_target.iterdir()):
            errors.append("실패한 악성 restore가 부분 결과를 노출했습니다.")

        unsafe_source = temp_root / "unsafe-source"
        shutil.copytree(source, unsafe_source)
        symlink = unsafe_source / "uploads" / "unsafe-link"
        try:
            symlink.symlink_to(unsafe_source / "release.txt")
        except OSError:
            pass
        else:
            try:
                module.create_backup(
                    unsafe_source,
                    temp_root / "unsafe-backups",
                    "2026-08-07T030000Z",
                    "2026-08-07T03:00:00Z",
                )
                errors.append("upload symlink가 있는 source backup을 허용했습니다.")
            except (ValueError, OSError):
                pass

    if errors:
        print(f"backup·restore 검사 실패: {len(errors)}건", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("통과: atomic backup, manifest, checksum, safe restore와 reference integrity")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
