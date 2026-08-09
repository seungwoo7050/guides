#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, content: str = "fixture\n", mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(mode)


def fixture(root: Path) -> Path:
    root.mkdir()
    for relative in ["prepare.sh", "verify.sh", "scripts/source_fingerprint.py", "scripts/new_workspace.py"]:
        source = SOURCE_ROOT / relative
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    write(
        root / "scripts/verify_repository.py",
        "import sys\n"
        "from pathlib import Path\n"
        "if not Path('docs/16-capstone.md').is_file():\n"
        "    raise SystemExit('STUB MISSING REQUIRED')\n"
        "if '--workspaces-only' in sys.argv and not Path('exercises/01-scope-and-evidence/work').is_dir():\n"
        "    raise SystemExit('STUB MISSING EXERCISE WORK')\n"
        "print('STUB REPOSITORY OK')\n",
    )
    write(
        root / "scripts/verify_capstone.py",
        "import sys\n"
        "from pathlib import Path\n"
        "if len(sys.argv) > 1 and not Path(sys.argv[1]).is_dir():\n"
        "    raise SystemExit('STUB MISSING CAPSTONE WORK')\n"
        "print('STUB CAPSTONE OK')\n",
    )
    write(root / "scripts/capstone_behavior.py", "print('STUB BEHAVIOR OK')\n")
    write(root / "scripts/capture_capstone_behavior.py", "print('STUB CAPTURE OK')\n")
    write(root / "scripts/test_tooling.py", "print('STUB TOOLING TEST OK')\n")
    write(root / "scripts/test_verify_repository.py", "print('STUB REPOSITORY META OK')\n")
    write(root / "scripts/test_verify_capstone.py", "print('STUB CAPSTONE META OK')\n")
    for relative in [
        "README.md",
        "docs/00-roadmap.md",
        "docs/16-capstone.md",
        "exercises/README.md",
        "exercises/07-isolated-attack-path/fixtures/state.json",
        "exercises/07-isolated-attack-path/reference/ledgerlab_policy.py",
        "exercises/07-isolated-attack-path/skeleton/ledgerlab_policy.py",
        "exercises/07-isolated-attack-path/tests/check.py",
        "exercises/07-isolated-attack-path/tests/check_quality.py",
        "reference/safe-lab-policy.md",
        "reference/manual-review-guide.md",
        "projects/synthetic-service-security-review/README.md",
        "projects/synthetic-service-security-review/scenario/candidate-findings.json",
        "projects/synthetic-service-security-review/templates/findings.json",
    ]:
        content = "{}\n" if relative.endswith(".json") else "fixture\n"
        write(root / relative, content)
    return root


def run(root: Path, *command: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    clean_env = dict(os.environ)
    clean_env.pop("VERIFY_LOG", None)
    clean_env.pop("CYBERSECURITY_VERIFY_WORK", None)
    if env:
        clean_env.update(env)
    return subprocess.run(
        list(command),
        cwd=root,
        env=clean_env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def require(condition: bool, message: str, result: subprocess.CompletedProcess[str] | None = None) -> None:
    if condition:
        return
    detail = "" if result is None else f"\nexit={result.returncode}\n{output(result)}"
    raise AssertionError(message + detail)


def remove_default_log(result: subprocess.CompletedProcess[str]) -> None:
    for line in result.stdout.splitlines():
        if line.startswith("VERIFY LOG "):
            path = Path(line.removeprefix("VERIFY LOG "))
            if path.parent.resolve() == Path("/tmp").resolve():
                path.unlink(missing_ok=True)


def prepare(root: Path) -> subprocess.CompletedProcess[str]:
    return run(root, "./prepare.sh")


def verify(root: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = run(root, "./verify.sh", env=env)
    if not env or "VERIFY_LOG" not in env:
        remove_default_log(result)
    return result


def fingerprint(root: Path) -> str:
    result = run(root, sys.executable, "scripts/source_fingerprint.py")
    require(result.returncode == 0, "fingerprint 계산 실패", result)
    return result.stdout.strip()


def test_prepare_and_failure_propagation(suite: Path) -> int:
    root = fixture(suite / "base")
    result = verify(root)
    require(result.returncode != 0 and "먼저 ./prepare.sh" in output(result), "prepare 전 verify가 성공했습니다.", result)

    before_mode = stat.S_IMODE((root / "verify.sh").stat().st_mode)
    before = fingerprint(root)
    result = prepare(root)
    require(result.returncode == 0 and "PREPARED" in output(result), "prepare가 실패했습니다.", result)
    marker = root / ".guide/cybersecurity/prepared.json"
    require(stat.S_IMODE(marker.stat().st_mode) == 0o600, "marker mode가 0600이 아닙니다.")
    require(before_mode == stat.S_IMODE((root / "verify.sh").stat().st_mode), "prepare가 source mode를 바꿨습니다.")
    require(before == fingerprint(root), "prepare marker가 source fingerprint를 바꿨습니다.")

    result = verify(root)
    require(result.returncode == 0 and "[SKIP] learner-work" in output(result), "기본 verify 또는 SKIP 피드백 실패", result)

    (root / "README.md").write_text("changed\n", encoding="utf-8")
    result = verify(root)
    text = output(result)
    require(result.returncode != 0, "source drift 뒤 verify가 성공했습니다.", result)
    require("[FAIL] prepared-source-fingerprint" in text, "source drift 실패 label이 없습니다.", result)
    require("[PASS] repository-reference-meta" in text, "후속 성공이 실행되지 않아 실패 전파를 검증하지 못했습니다.", result)
    require("[SUMMARY] checks=2 pass=1 fail=1 skip=1" in text, "실패 summary가 정확하지 않습니다.", result)
    return 3


def test_explicit_exclusions_and_mode(suite: Path) -> int:
    root = fixture(suite / "exclusions")
    baseline = fingerprint(root)
    for path, content in [
        (root / ".guide/local.json", "marker"),
        (root / "exercises/01-scope-and-evidence/work/answer.md", "answer"),
        (root / "projects/synthetic-service-security-review/work/report.md", "report"),
        (root / "scripts/__pycache__/cache.pyc", "cache"),
        (root / ".DS_Store", "metadata"),
    ]:
        write(path, content)
    require(fingerprint(root) == baseline, "명시된 generated/work 경로가 fingerprint에 포함됐습니다.")

    readme = root / "README.md"
    original_mode = stat.S_IMODE(readme.stat().st_mode)
    readme.chmod(original_mode | stat.S_IXUSR)
    require(fingerprint(root) != baseline, "source file mode 변경을 fingerprint가 감지하지 못했습니다.")
    return 2


def test_missing_and_marker_symlinks(suite: Path) -> int:
    missing = fixture(suite / "missing")
    (missing / "README.md").unlink()
    result = prepare(missing)
    require(result.returncode != 0 and "필수 파일이 없습니다" in output(result), "필수 파일 누락 prepare가 성공했습니다.", result)

    verify_missing = fixture(suite / "verify-missing")
    result = prepare(verify_missing)
    require(result.returncode == 0, "missing verify test prepare 실패", result)
    (verify_missing / "docs/16-capstone.md").unlink()
    result = verify(verify_missing)
    require(result.returncode != 0 and "fail=2" in output(result), "prepare 뒤 필수 파일 누락 verify가 성공했습니다.", result)

    marker_root = fixture(suite / "marker-link")
    marker_parent = marker_root / ".guide/cybersecurity"
    marker_parent.mkdir(parents=True)
    victim = suite / "marker-victim.json"
    write(victim, "do-not-change\n")
    (marker_parent / "prepared.json").symlink_to(victim)
    result = prepare(marker_root)
    require(result.returncode != 0 and "marker" in output(result).lower(), "marker symlink prepare가 성공했습니다.", result)
    require(victim.read_text(encoding="utf-8") == "do-not-change\n", "marker symlink target이 변경됐습니다.")

    parent_root = fixture(suite / "marker-parent-link")
    external = suite / "external-guide"
    external.mkdir()
    (parent_root / ".guide").symlink_to(external, target_is_directory=True)
    result = prepare(parent_root)
    require(result.returncode != 0 and "symlink" in output(result), "marker parent symlink prepare가 성공했습니다.", result)
    require(not (external / "cybersecurity").exists(), "marker parent symlink 밖에 파일을 만들었습니다.")

    verify_marker = fixture(suite / "verify-marker-parent-link")
    result = prepare(verify_marker)
    require(result.returncode == 0, "marker parent verify test prepare 실패", result)
    marker_payload = (verify_marker / ".guide/cybersecurity/prepared.json").read_text(encoding="utf-8")
    shutil.rmtree(verify_marker / ".guide")
    external_verify = suite / "external-verify-guide/cybersecurity"
    external_verify.mkdir(parents=True)
    write(external_verify / "prepared.json", marker_payload)
    (verify_marker / ".guide").symlink_to(external_verify.parent, target_is_directory=True)
    result = verify(verify_marker)
    require(result.returncode != 0 and "marker 경로가 symlink" in output(result), "marker parent symlink verify가 성공했습니다.", result)
    return 5


def test_log_contract(suite: Path) -> int:
    root = fixture(suite / "logs-repo")
    result = prepare(root)
    require(result.returncode == 0, "log test prepare 실패", result)
    logs = suite / "logs"
    logs.mkdir()

    existing = logs / "existing.log"
    write(existing, "preserve\n")
    result = verify(root, {"VERIFY_LOG": str(existing)})
    require(result.returncode != 0 and "덮어쓸 수 없습니다" in output(result), "existing VERIFY_LOG를 거부하지 않았습니다.", result)
    require(existing.read_text(encoding="utf-8") == "preserve\n", "existing VERIFY_LOG를 덮어썼습니다.")

    victim = logs / "victim.log"
    write(victim, "preserve-link-target\n")
    link = logs / "link.log"
    link.symlink_to(victim)
    result = verify(root, {"VERIFY_LOG": str(link)})
    require(result.returncode != 0 and "symlink" in output(result), "symlink VERIFY_LOG를 거부하지 않았습니다.", result)
    require(victim.read_text(encoding="utf-8") == "preserve-link-target\n", "VERIFY_LOG symlink target을 덮어썼습니다.")

    inside = root / "verification.log"
    result = verify(root, {"VERIFY_LOG": str(inside)})
    require(result.returncode != 0 and "저장소 내부" in output(result), "저장소 내부 VERIFY_LOG를 허용했습니다.", result)
    require(not inside.exists(), "거부한 저장소 내부 log를 만들었습니다.")

    accepted = logs / "new.log"
    result = verify(root, {"VERIFY_LOG": str(accepted)})
    require(result.returncode == 0 and accepted.is_file(), "새 외부 VERIFY_LOG를 만들지 못했습니다.", result)
    require("[SUMMARY] checks=2 pass=2 fail=0 skip=1" in accepted.read_text(encoding="utf-8"), "외부 log summary가 없습니다.")
    result = verify(root, {"VERIFY_LOG": str(accepted)})
    require(result.returncode != 0, "같은 VERIFY_LOG를 두 번째로 덮어썼습니다.", result)
    return 5


def test_workspace_no_overwrite(suite: Path) -> int:
    root = fixture(suite / "workspace")
    write(root / "exercises/01-scope-and-evidence/template/assessment-charter.md", "template\n")
    result = run(root, sys.executable, "scripts/new_workspace.py", "exercise", "01-scope-and-evidence")
    require(result.returncode == 0, "exercise workspace 생성 실패", result)
    answer = root / "exercises/01-scope-and-evidence/work/assessment-charter.md"
    answer.write_text("learner answer\n", encoding="utf-8")
    result = run(root, sys.executable, "scripts/new_workspace.py", "exercise", "01-scope-and-evidence")
    require(result.returncode != 0 and "덮어쓰지 않습니다" in output(result), "기존 workspace를 덮어썼습니다.", result)
    require(answer.read_text(encoding="utf-8") == "learner answer\n", "기존 learner answer가 변경됐습니다.")

    write(root / "exercises/02-threat-model/template/threat-model.md", "template\n")
    outside = suite / "workspace-victim"
    outside.mkdir()
    work_link = root / "exercises/02-threat-model/work"
    work_link.symlink_to(outside, target_is_directory=True)
    result = run(root, sys.executable, "scripts/new_workspace.py", "exercise", "02-threat-model")
    require(result.returncode != 0 and "덮어쓰지 않습니다" in output(result), "symlink workspace를 허용했습니다.", result)
    require(list(outside.iterdir()) == [], "workspace symlink target에 파일을 썼습니다.")
    return 2


def test_explicit_work_mode(suite: Path) -> int:
    root = fixture(suite / "work-mode")
    result = prepare(root)
    require(result.returncode == 0, "work mode test prepare 실패", result)
    result = verify(root, {"CYBERSECURITY_VERIFY_WORK": "1"})
    text = output(result)
    require(result.returncode != 0 and "[FAIL] exercise-workspaces" in text, "exercise work 누락을 거부하지 않았습니다.", result)
    require("[FAIL] capstone-work" in text and "skip=0" in text, "Capstone work 누락 또는 work-mode summary가 잘못됐습니다.", result)

    (root / "exercises/01-scope-and-evidence/work").mkdir(parents=True)
    (root / "projects/synthetic-service-security-review/work").mkdir(parents=True)
    result = verify(root, {"CYBERSECURITY_VERIFY_WORK": "1"})
    require(result.returncode == 0 and "checks=4 pass=4 fail=0 skip=0" in output(result), "명시적 work mode routing이 실패했습니다.", result)
    return 2


def main() -> int:
    if sys.version_info < (3, 10):
        print("Python 3.10 이상이 필요합니다.", file=sys.stderr)
        return 1
    cases = 0
    with tempfile.TemporaryDirectory(prefix="cybersecurity-tooling-test-") as temporary:
        suite = Path(temporary)
        cases += test_prepare_and_failure_propagation(suite)
        cases += test_explicit_exclusions_and_mode(suite)
        cases += test_missing_and_marker_symlinks(suite)
        cases += test_log_contract(suite)
        cases += test_workspace_no_overwrite(suite)
        cases += test_explicit_work_mode(suite)
    print(f"TOOLING TEST OK cases={cases}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"TOOLING TEST ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
