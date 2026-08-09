#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$ROOT"

python3 - <<'PY'
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

root = Path.cwd()
if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10 이상이 필요합니다.")

required = [
    root / "README.md",
    root / "docs/00-roadmap.md",
    root / "docs/16-capstone.md",
    root / "exercises/README.md",
    root / "exercises/07-isolated-attack-path/fixtures/state.json",
    root / "exercises/07-isolated-attack-path/reference/ledgerlab_policy.py",
    root / "exercises/07-isolated-attack-path/skeleton/ledgerlab_policy.py",
    root / "exercises/07-isolated-attack-path/tests/check.py",
    root / "exercises/07-isolated-attack-path/tests/check_quality.py",
    root / "reference/safe-lab-policy.md",
    root / "reference/manual-review-guide.md",
    root / "projects/synthetic-service-security-review/README.md",
    root / "projects/synthetic-service-security-review/scenario/candidate-findings.json",
    root / "projects/synthetic-service-security-review/templates/findings.json",
    root / "scripts/new_workspace.py",
    root / "scripts/capstone_behavior.py",
    root / "scripts/capture_capstone_behavior.py",
    root / "scripts/source_fingerprint.py",
    root / "scripts/test_tooling.py",
    root / "scripts/test_verify_repository.py",
    root / "scripts/test_verify_capstone.py",
    root / "scripts/verify_repository.py",
    root / "scripts/verify_capstone.py",
]
for path in required:
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"필수 파일이 없습니다: {path.relative_to(root)}")

for path in [root / "prepare.sh", root / "verify.sh"]:
    if path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
        raise SystemExit(f"실행 가능한 필수 파일이 아닙니다: {path.relative_to(root)}")

result = subprocess.run(
    [sys.executable, str(root / "scripts/source_fingerprint.py")],
    cwd=root,
    text=True,
    capture_output=True,
    check=False,
)
if result.returncode != 0:
    raise SystemExit(result.stderr.strip() or "source fingerprint 계산에 실패했습니다.")
fingerprint = result.stdout.strip()


def secure_directory(path: Path) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"marker 경로가 저장소 밖입니다: {path}") from exc
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise SystemExit(f"marker 상위 경로가 symlink입니다: {current.relative_to(root)}")
        if current.exists():
            if not current.is_dir():
                raise SystemExit(f"marker 상위 경로가 디렉터리가 아닙니다: {current.relative_to(root)}")
            continue
        current.mkdir(mode=0o700)
        if current.is_symlink() or not current.is_dir():
            raise SystemExit(f"marker 디렉터리를 안전하게 만들지 못했습니다: {current.relative_to(root)}")


marker = root / ".guide/cybersecurity/prepared.json"
secure_directory(marker.parent)
if marker.is_symlink() or (marker.exists() and not marker.is_file()):
    raise SystemExit(f"prepare marker가 안전한 일반 파일이 아닙니다: {marker.relative_to(root)}")

payload = {
    "schema_version": 1,
    "guide": "cybersecurity",
    "fingerprint_version": 2,
    "prepared_at": datetime.now(timezone.utc).isoformat(),
    "python": ".".join(map(str, sys.version_info[:3])),
    "source_sha256": fingerprint,
    "network_required": False,
    "administrator_privileges_required": False,
}
temporary: Path | None = None
try:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=marker.parent,
        prefix=".prepared.",
        suffix=".tmp",
        delete=False,
    ) as stream:
        temporary = Path(stream.name)
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temporary.chmod(stat.S_IRUSR | stat.S_IWUSR)
    os.replace(temporary, marker)
    temporary = None
finally:
    if temporary is not None:
        temporary.unlink(missing_ok=True)

print(f"PREPARED {marker.relative_to(root)}")
print(f"SOURCE SHA256 {fingerprint}")
PY
