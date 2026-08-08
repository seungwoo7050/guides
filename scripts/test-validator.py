#!/usr/bin/env python3
"""Prove that repository validation rejects representative contract defects."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import re
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def copy_repository(destination: Path) -> None:
    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".git", ".guide", "target", "__pycache__"}}

    shutil.copytree(ROOT, destination, symlinks=True, ignore=ignore)


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", "scripts/validate.py"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def mutate_text(root: Path, relative: str, old: str, new: str) -> None:
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"mutant precondition missing in {relative}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def create_text(root: Path, relative: str, text: str = "mutant\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def replace_with_external_symlink(root: Path, relative: str) -> None:
    path = root / relative
    external = root.parent / "external-managed-file.md"
    external.write_text("# external\n", encoding="utf-8")
    path.unlink()
    path.symlink_to(external)


def copy_pedagogy_section(root: Path, heading: str, next_heading: str) -> None:
    source = root / "exercises/01-boundaries-and-failure/01-uncertain-outcome/README.md"
    target = root / "exercises/01-boundaries-and-failure/02-service-boundary/README.md"
    source_text = source.read_text(encoding="utf-8")
    target_text = target.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(?ms)^{re.escape(heading)}\n.*?(?=^{re.escape(next_heading)}\n)"
    )
    source_section = pattern.search(source_text)
    if source_section is None or pattern.search(target_text) is None:
        raise AssertionError(f"missing pedagogy section: {heading}")
    target.write_text(
        pattern.sub(source_section.group(0), target_text, count=1),
        encoding="utf-8",
    )


def main() -> int:
    baseline = validate(ROOT)
    if baseline.returncode:
        raise SystemExit("validator baseline failed:\n" + baseline.stdout + baseline.stderr)

    mutations = [
        (
            "missing required document",
            lambda root: (root / "docs/00-roadmap.md").unlink(),
        ),
        (
            "missing pedagogy heading",
            lambda root: mutate_text(
                root,
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/README.md",
                "## 자기 설명",
                "## 설명",
            ),
        ),
        (
            "unfinished reference",
            lambda root: mutate_text(
                root,
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/reference/src/main/java/dev/guides/distributed/uncertain/UncertainOutcome.java",
                "public final class UncertainOutcome",
                "// TODO unfinished reference\npublic final class UncertainOutcome",
            ),
        ),
        (
            "divergent skeleton test",
            lambda root: mutate_text(
                root,
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/skeleton/src/test/java/dev/guides/distributed/uncertain/UncertainOutcomeTest.java",
                "public final class UncertainOutcomeTest",
                "public final class UncertainOutcomeTest /* divergent */",
            ),
        ),
        (
            "obsolete path",
            lambda root: (root / "reference").mkdir(),
        ),
        (
            "floating Kafka tag",
            lambda root: mutate_text(
                root,
                "exercises/90-optional-labs/single-broker-kraft/reference/compose.yaml",
                "apache/kafka:4.3.1",
                "apache/kafka:latest",
            ),
        ),
        (
            "per-file Kafka version drift",
            lambda root: mutate_text(
                root,
                "exercises/90-optional-labs/single-broker-kraft/reference/compose.yaml",
                "apache/kafka:4.3.1@sha256:",
                "apache/kafka:4.3.0@sha256:",
            ),
        ),
        (
            "unexpected managed file",
            lambda root: create_text(root, "scripts/unexpected-file.txt"),
        ),
        (
            "unexpected top-level file",
            lambda root: create_text(root, "notes.txt"),
        ),
        (
            "managed file replaced by external symlink",
            lambda root: replace_with_external_symlink(root, "README.md"),
        ),
        (
            "broken heading anchor",
            lambda root: mutate_text(
                root,
                "README.md",
                "[학습 로드맵](docs/00-roadmap.md)",
                "[학습 로드맵](docs/00-roadmap.md#missing-anchor)",
            ),
        ),
        (
            "wrong executable mode",
            lambda root: (root / "prepare.sh").chmod(0o644),
        ),
        (
            "generated artifact",
            lambda root: create_text(root, "exercises/test-support/target/generated.txt"),
        ),
        (
            "Maven checksum drift",
            lambda root: mutate_text(
                root,
                ".mvn/wrapper/maven-wrapper.properties",
                "distributionSha256Sum=5af3b743",
                "distributionSha256Sum=0af3b743",
            ),
        ),
        (
            "self-explanation without question",
            lambda root: mutate_text(
                root,
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/README.md",
                "중복 효과가 생길 수 있습니까?",
                "중복 효과가 생길 수 있습니다.",
            ),
        ),
        (
            "copied completion section",
            lambda root: copy_pedagogy_section(root, "## 완료 기준", "## 자기 설명"),
        ),
        (
            "copied self-explanation section",
            lambda root: copy_pedagogy_section(root, "## 자기 설명", "## 검증"),
        ),
        (
            "too few completion bullets",
            lambda root: mutate_text(
                root,
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/README.md",
                "- 응답 유실 뒤에도 같은 `operationId` 조회가 `ACCEPTED`를 돌려줍니다.\n",
                "",
            ),
        ),
        (
            "missing learner command",
            lambda root: mutate_text(
                root,
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/README.md",
                "./scripts/verify-java.sh .workspace/uncertain-outcome",
                "./scripts/verify-java.sh .workspace/wrong-path",
            ),
        ),
        (
            "missing designated KRaft diagnosis",
            lambda root: mutate_text(
                root,
                "exercises/90-optional-labs/single-broker-kraft/verify.sh",
                "INVALID_REPLICATION_FACTOR",
                "AnyKafkaFailure",
            ),
        ),
        (
            "missing public make clean",
            lambda root: mutate_text(
                root,
                "CONTRIBUTING.md",
                "make clean",
                "clean 명령 누락",
            ),
        ),
        (
            "learner workspace excluded from formal copy",
            lambda root: mutate_text(
                root,
                "verify.sh",
                "    --exclude='/.guide/' \\\n",
                "    --exclude='/.guide/' \\\n    --exclude='/.workspace/' \\\n",
            ),
        ),
        (
            "mvnw missing from preparation fingerprint",
            lambda root: mutate_text(
                root,
                "prepare.sh",
                "\n  mvnw\n",
                "\n  # mvnw omitted\n",
            ),
        ),
        (
            "child POMs missing from preparation fingerprint",
            lambda root: mutate_text(
                root,
                "verify.sh",
                'find "$ROOT/exercises" -type f -name pom.xml | sort',
                'find "$ROOT/exercises" -type f -name omitted.xml | sort',
            ),
        ),
        (
            "tool identity missing from marker",
            lambda root: mutate_text(
                root,
                "verify.sh",
                '"docker_compose_version"',
                '"docker_compose_omitted"',
            ),
        ),
        (
            "optional Git index writes enabled",
            lambda root: mutate_text(
                root,
                "verify.sh",
                "export GIT_OPTIONAL_LOCKS=0",
                "export GIT_OPTIONAL_LOCKS=1",
            ),
        ),
        (
            "linked-worktree Git file copied",
            lambda root: mutate_text(
                root,
                "verify.sh",
                "--exclude='/.git'",
                "--exclude='/.git/'",
            ),
        ),
        (
            "learner verifier no longer binds canonical tests",
            lambda root: mutate_text(
                root,
                "scripts/verify-java.sh",
                'test_root="$(canonical_test_root "$module")"',
                'test_root="$module/src/test/java"',
            ),
        ),
        (
            "atomic marker temporary cleanup missing",
            lambda root: mutate_text(
                root,
                "prepare.sh",
                '    rm -f -- "$MARKER_TMP"\n',
                '    : "marker temporary cleanup omitted"\n',
            ),
        ),
    ]

    for name, mutate in mutations:
        with tempfile.TemporaryDirectory(prefix="guide-distributed-validator-") as temporary:
            clone = Path(temporary) / "repository"
            copy_repository(clone)
            mutate(clone)
            outcome = validate(clone)
            if outcome.returncode == 0:
                raise AssertionError(f"validator accepted mutant: {name}")
            print(f"[PASS] validator rejected {name}")

    with tempfile.TemporaryDirectory(prefix="guide-distributed-workspace-") as temporary:
        clone = Path(temporary) / "repository"
        copy_repository(clone)
        create_text(clone, ".workspace/learner/arbitrary.py", "this is learner data\n")
        create_text(clone, ".workspace/learner/arbitrary.sh", "learner shell bytes\n")
        create_text(clone, ".workspace/learner/profile.jfr", "learner evidence bytes\n")
        outcome = validate(clone)
        if outcome.returncode != 0:
            raise AssertionError(
                "validator treated top-level learner workspace as curriculum:\n"
                + outcome.stdout
                + outcome.stderr
            )
        print("[PASS] validator excludes top-level learner workspace from curriculum checks")

    with tempfile.TemporaryDirectory(prefix="guide-distributed-learner-tests-") as temporary:
        clone = Path(temporary) / "repository"
        copy_repository(clone)
        workspace = clone / ".workspace/uncertain-outcome"
        shutil.copytree(
            clone / "exercises/01-boundaries-and-failure/01-uncertain-outcome/skeleton",
            workspace,
        )
        mutate_text(
            clone,
            ".workspace/uncertain-outcome/src/test/java/dev/guides/distributed/uncertain/UncertainOutcomeTest.java",
            "        responseLossDoesNotEraseCommittedResult();\n"
            "        sameOperationReturnsSameEffect();\n"
            "        conflictingInputIsRejected();\n",
            "",
        )
        outcome = subprocess.run(
            ["scripts/verify-java.sh", ".workspace/uncertain-outcome"],
            cwd=clone,
            env={**os.environ, "GUIDE_VERIFY_WORK_DIR": str(Path(temporary) / "results")},
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if outcome.returncode == 0 or "응답 유실 뒤 저장된 결과" not in outcome.stderr:
            raise AssertionError("learner verifier trusted mutable workspace tests")
        print("[PASS] learner verifier ignored mutable tests and used canonical tests")

    with tempfile.TemporaryDirectory(prefix="guide-distributed-runtime-mutant-") as temporary:
        clone = Path(temporary) / "repository"
        copy_repository(clone)
        mutate_text(
            clone,
            "exercises/01-boundaries-and-failure/01-uncertain-outcome/skeleton/src/main/java/dev/guides/distributed/uncertain/UncertainOutcome.java",
            "return new Result(operationId, Status.UNKNOWN, 0);",
            'System.out.println("응답 유실 뒤 저장된 결과를 조회해야 합니다");\n'
            '            throw new AssertionError("unrelated injected failure");',
        )
        outcome = subprocess.run(
            [
                "scripts/verify-skeletons.sh",
                "exercises/01-boundaries-and-failure/01-uncertain-outcome/skeleton",
            ],
            cwd=clone,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if outcome.returncode == 0 or "unintended reason" not in outcome.stderr:
            raise AssertionError("runtime verifier accepted an unintended skeleton failure")
        print("[PASS] runtime verifier rejected unintended skeleton failure")

    with tempfile.TemporaryDirectory(prefix="guide-distributed-release-mutant-") as temporary:
        clone = Path(temporary) / "repository"
        copy_repository(clone)
        mutate_text(
            clone,
            "exercises/04-release-and-evidence/01-release-manifest/skeleton/manifest_check.py",
            '    document = json.loads(Path(argv[1]).read_text(encoding="utf-8"))',
            '    print("GUIDE_SEMANTIC: invalid manifest was accepted (expected duplicate)")\n'
            '    raise AssertionError("unrelated injected failure")\n'
            '    document = json.loads(Path(argv[1]).read_text(encoding="utf-8"))',
        )
        outcome = subprocess.run(
            ["scripts/verify-nonjava.sh"],
            cwd=clone,
            env={**os.environ, "GUIDE_VALIDATOR_SELF_TEST": "release"},
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if outcome.returncode == 0 or "unintended reason" not in outcome.stderr:
            raise AssertionError("release verifier accepted an unintended skeleton failure")
        print("[PASS] release verifier rejected unintended skeleton failure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
