#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from guide_state import (  # noqa: E402
    GUIDE_ID,
    IMAGE_REFS,
    capture,
    copy_source,
    git_index_state,
    validate_marker_payload,
)


def run(
    arguments: list[str],
    *,
    cwd: Path,
    environment: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=cwd,
        env=dict(environment) if environment is not None else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def run_validator(root: Path) -> subprocess.CompletedProcess[str]:
    return run(["python3", "scripts/validate.py"], cwd=root)


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"mutant 입력을 찾지 못했습니다: {path}: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def remove_roadmap(root: Path) -> None:
    (root / "docs/00-roadmap.md").unlink()


def add_managed_file(root: Path) -> None:
    (root / "scripts/unexpected.py").write_text("print('unexpected')\n", encoding="utf-8")


def add_managed_target(root: Path) -> None:
    path = root / "docs/target"
    path.mkdir()
    (path / "sentinel.txt").write_text("generated\n", encoding="utf-8")


def add_class_artifact(root: Path) -> None:
    (root / "Leaked.class").write_bytes(b"\xca\xfe\xba\xbe")


def break_file_link(root: Path) -> None:
    path = root / "README.md"
    path.write_text(
        path.read_text(encoding="utf-8") + "\n[깨진 파일](docs/missing.md)\n",
        encoding="utf-8",
    )


def break_anchor(root: Path) -> None:
    path = root / "README.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n[깨진 anchor](docs/00-roadmap.md#존재하지-않는-anchor)\n",
        encoding="utf-8",
    )


def break_executable_mode(root: Path) -> None:
    (root / "scripts/guide_state.py").chmod(0o644)


def break_wrapper_with_decoy(root: Path) -> None:
    path = root / ".mvn/wrapper/maven-wrapper.properties"
    replace(path, "wrapperVersion=3.3.4", "wrapperVersion=3.3.3")
    path.write_text(
        path.read_text(encoding="utf-8") + "# wrapperVersion=3.3.4\n",
        encoding="utf-8",
    )


def copy_rubric(root: Path) -> None:
    source = root / "exercises/security-boundaries/README.md"
    target = root / "exercises/application-boundaries/README.md"
    source_text = source.read_text(encoding="utf-8")
    target_text = target.read_text(encoding="utf-8")
    explanation = source_text.split("## 자기 설명", 1)[1].split("## 검증", 1)[0]
    prefix, remainder = target_text.split("## 자기 설명", 1)
    _old, suffix = remainder.split("## 검증", 1)
    target.write_text(
        prefix + "## 자기 설명" + explanation + "## 검증" + suffix,
        encoding="utf-8",
    )


def drift_test(root: Path) -> None:
    path = root / (
        "exercises/application-boundaries/skeleton/src/test/java/"
        "dev/guides/spring/boundaries/PreviewControllerTest.java"
    )
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")


def break_effective_version_with_decoy(root: Path) -> None:
    path = root / "pom.xml"
    replace(
        path,
        "<testcontainers.version>2.0.5</testcontainers.version>",
        "<testcontainers.version>2.0.4</testcontainers.version>",
    )
    path.write_text(
        path.read_text(encoding="utf-8")
        + "\n<!-- <testcontainers.version>2.0.5</testcontainers.version> -->\n",
        encoding="utf-8",
    )


def override_boot_managed_plugin(root: Path) -> None:
    path = root / "pom.xml"
    replace(
        path,
        "<artifactId>maven-surefire-plugin</artifactId>",
        "<artifactId>maven-surefire-plugin</artifactId>\n"
        "          <version>3.5.6</version>",
    )


def remove_boot_flyway_integration(root: Path) -> None:
    path = root / "exercises/transaction-locking/skeleton/pom.xml"
    replace(
        path,
        "    <dependency><groupId>org.springframework.boot</groupId>"
        "<artifactId>spring-boot-flyway</artifactId></dependency>\n",
        "",
    )


def remove_kafka_container_module(root: Path) -> None:
    path = root / "exercises/kafka-avro-contract/skeleton/pom.xml"
    replace(
        path,
        "    <dependency><groupId>org.testcontainers</groupId>"
        "<artifactId>testcontainers-kafka</artifactId>"
        "<scope>test</scope></dependency>\n",
        "",
    )


def add_reference_todo(root: Path) -> None:
    path = root / "exercises/application-boundaries/reference/src/main/resources/application.yml"
    path.write_text(path.read_text(encoding="utf-8") + "# TODO later\n", encoding="utf-8")


def add_legacy_reference(root: Path) -> None:
    path = root / "reference"
    path.mkdir(exist_ok=True)
    (path / "version-baseline.md").write_text("# Legacy\n", encoding="utf-8")


def float_runtime_image_with_decoy(root: Path) -> None:
    path = root / (
        "exercises/transaction-locking/skeleton/src/test/java/"
        "dev/guides/spring/locking/InventoryConcurrencyIntegrationTest.java"
    )
    exact = IMAGE_REFS[0]
    replace(path, exact, "postgres:18.4-alpine")
    path.write_text(
        path.read_text(encoding="utf-8") + f"\n// decoy: {exact}\n",
        encoding="utf-8",
    )


def restore_tracked_skeleton_flow(root: Path) -> None:
    path = root / "exercises/application-boundaries/README.md"
    replace(
        path,
        "./scripts/new-workspace.sh application-boundaries",
        "./mvnw -f exercises/application-boundaries/skeleton/pom.xml test",
    )


def remove_public_clean_command(root: Path) -> None:
    for name in ("README.md", "CONTRIBUTING.md"):
        path = root / name
        path.write_text(
            path.read_text(encoding="utf-8").replace("make clean", "make tidy"),
            encoding="utf-8",
        )


def broaden_generated_ignore(root: Path) -> None:
    path = root / ".gitignore"
    replace(path, "/target/", "**/target/")


def remove_int_reset(root: Path) -> None:
    path = root / "scripts/run_in_session.py"
    replace(
        path,
        "signal.SIGHUP, signal.SIGINT, signal.SIGTERM",
        "signal.SIGHUP, signal.SIGTERM",
    )


MUTANTS: tuple[tuple[str, Callable[[Path], None], str], ...] = (
    ("exact-tree-missing", remove_roadmap, "정확한 managed tree가 다릅니다"),
    ("exact-tree-extra", add_managed_file, "정확한 managed tree가 다릅니다"),
    ("generated-directory", add_managed_target, "허용되지 않은 생성 directory"),
    ("generated-class", add_class_artifact, "생성물이 source tree에 남아"),
    ("broken-file-link", break_file_link, "대상이 없는 링크"),
    ("broken-anchor", break_anchor, "대상이 없는 Markdown anchor"),
    ("executable-mode", break_executable_mode, "파일 mode가 manifest와 다릅니다"),
    ("wrapper-decoy", break_wrapper_with_decoy, "Maven Wrapper effective 설정"),
    ("copied-rubric", copy_rubric, "복사된 자기 설명"),
    ("test-drift", drift_test, "같은 test 계약"),
    ("effective-version-decoy", break_effective_version_with_decoy, "root POM effective property"),
    ("boot-managed-plugin", override_boot_managed_plugin, "Spring Boot parent 관리 판본"),
    ("boot4-flyway-module", remove_boot_flyway_integration, "Boot 4 Flyway 통합"),
    ("kafka-container-module", remove_kafka_container_module, "Kafka 4.3.1 container 모듈"),
    ("reference-todo", add_reference_todo, "reference에 미완성 표식"),
    ("legacy-path", add_legacy_reference, "prepare.sh가 삭제해야 할 폐기 경로"),
    ("floating-runtime-image", float_runtime_image_with_decoy, "실행 Java 코드의 Docker image reference"),
    ("tracked-skeleton-flow", restore_tracked_skeleton_flow, "안전한 canonical workspace 명령"),
    ("public-command", remove_public_clean_command, "공개 명령이 없습니다: make clean"),
    ("broad-generated-ignore", broaden_generated_ignore, "learner target/.workspace를 광범위하게 제외"),
    ("signal-reset", remove_int_reset, "process-group signal helper 계약"),
)


def require_standard_preflight(result: subprocess.CompletedProcess[str], label: str) -> None:
    required = ("VERIFY LOG: ", "RESULT: FAIL")
    if (
        result.returncode != 2
        or re.search(r"SUMMARY: passed=\d+ failed=1 skipped=0", result.stdout) is None
        or any(value not in result.stdout for value in required)
    ):
        raise RuntimeError(f"{label} preflight schema/rc가 다릅니다:\n{result.stdout}")


def check_log_preflights(base: Path, temporary: Path) -> None:
    before = capture(base)
    environment = os.environ.copy()

    environment["VERIFY_LOG"] = "relative.log"
    relative = run(["./verify.sh"], cwd=base, environment=environment)
    require_standard_preflight(relative, "relative log")
    if (base / "relative.log").exists():
        raise RuntimeError("relative VERIFY_LOG가 저장소를 변경했습니다.")

    internal_parent = base / "must-not-exist"
    environment["VERIFY_LOG"] = str(internal_parent / "verify.log")
    internal = run(["./verify.sh"], cwd=base, environment=environment)
    require_standard_preflight(internal, "internal log")
    if internal_parent.exists():
        raise RuntimeError("containment 확인 전에 repository 내부 directory를 만들었습니다.")

    symlink_parent = temporary / "log-link"
    symlink_parent.symlink_to(base / "docs", target_is_directory=True)
    environment["VERIFY_LOG"] = str(symlink_parent / "verify.log")
    linked = run(["./verify.sh"], cwd=base, environment=environment)
    require_standard_preflight(linked, "symlink log")
    if (base / "docs/verify.log").exists():
        raise RuntimeError("symlink VERIFY_LOG가 repository 내부 파일을 만들었습니다.")

    fake_bin = temporary / "fake-bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    fake_docker.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_docker.chmod(0o755)
    environment.pop("VERIFY_LOG", None)
    environment["PATH"] = f"{fake_bin}{os.pathsep}{environment['PATH']}"
    default = run(["./verify.sh"], cwd=base, environment=environment)
    require_standard_preflight(default, "default log")
    match = re.search(
        r"VERIFY LOG: (/(?:private/)?tmp/guide-backend-spring-boot-verify-[^\n]+)",
        default.stdout,
    )
    if match is None or not Path(match.group(1)).is_file():
        raise RuntimeError(f"default external verify log가 없습니다:\n{default.stdout}")
    Path(match.group(1)).unlink()
    if capture(base) != before:
        raise RuntimeError("invalid VERIFY_LOG/default preflight가 source state를 변경했습니다.")
    print("[PASS] invalid/default VERIFY_LOG rc=2·표준 출력·nonmutation")


def check_marker_contract(temporary: Path) -> None:
    maven_home = temporary / "marker/maven-home"
    repository = temporary / "marker/m2"
    maven_home.mkdir(parents=True)
    repository.mkdir()
    tools = {
        "java": 'openjdk version "21.0.8"',
        "javac": "javac 21.0.8",
        "maven": "Apache Maven 3.9.16",
        "python": "Python 3.12.0",
        "git": "git version 2.50.0",
        "docker": "28.0.0",
    }
    images = {reference: f"sha256:{number:064x}" for number, reference in enumerate(IMAGE_REFS, 1)}
    marker: dict[str, object] = {
        "schema": 1,
        "guide_id": GUIDE_ID,
        "preparation_input_fingerprint": "fingerprint",
        "cache": {
            "maven_home": str(maven_home),
            "maven_repository": str(repository),
        },
        "tools": tools,
        "images": images,
    }
    validate_marker_payload(
        marker,
        fingerprint="fingerprint",
        expected_maven_home=maven_home,
        expected_repository=repository,
        tools=tools,
        images=images,
    )

    mutations: tuple[tuple[str, Callable[[dict[str, object]], None]], ...] = (
        ("extra-schema-key", lambda value: value.__setitem__("head", "decoy")),
        ("stale-fingerprint", lambda value: value.__setitem__("preparation_input_fingerprint", "old")),
        ("wrong-tool", lambda value: value["tools"].__setitem__("docker", "old")),  # type: ignore[union-attr]
        ("missing-image-ref", lambda value: value["images"].pop(IMAGE_REFS[0])),  # type: ignore[union-attr]
        ("invalid-image-id", lambda value: value["images"].__setitem__(IMAGE_REFS[0], "sha256:bad")),  # type: ignore[union-attr]
        ("wrong-cache", lambda value: value["cache"].__setitem__("maven_repository", str(temporary / "elsewhere"))),  # type: ignore[union-attr]
    )
    for name, mutate in mutations:
        candidate = copy.deepcopy(marker)
        mutate(candidate)
        try:
            validate_marker_payload(
                candidate,
                fingerprint="fingerprint",
                expected_maven_home=maven_home,
                expected_repository=repository,
                tools=tools,
                images=images,
            )
        except SystemExit:
            print(f"[PASS] bad marker mutant: {name}")
        else:
            raise RuntimeError(f"bad marker mutant를 허용했습니다: {name}")


def git_command(arguments: list[str], cwd: Path) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Fixture",
            "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
            "GIT_COMMITTER_NAME": "Fixture",
            "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        }
    )
    result = run(["git", *arguments], cwd=cwd, environment=environment)
    if result.returncode != 0:
        raise RuntimeError(f"git fixture 실패: {' '.join(arguments)}\n{result.stdout}")


def check_linked_raw_index(temporary: Path) -> None:
    repository = temporary / "index-repository"
    linked = temporary / "index-linked"
    repository.mkdir()
    git_command(["init", "-q"], repository)
    (repository / "tracked.txt").write_text("base\n", encoding="utf-8")
    git_command(["add", "tracked.txt"], repository)
    git_command(["commit", "-q", "-m", "fixture"], repository)
    git_command(["worktree", "add", "-q", "-b", "linked", str(linked)], repository)
    if not (linked / ".git").is_file():
        raise RuntimeError("linked worktree fixture의 .git이 file이 아닙니다.")
    (linked / "tracked.txt").write_text("staged\n", encoding="utf-8")
    git_command(["add", "tracked.txt"], linked)
    git_command(["update-index", "--index-version", "2"], linked)
    version_two = git_index_state(linked)
    git_command(["update-index", "--index-version", "4"], linked)
    version_four = git_index_state(linked)
    if version_two["staged_entries_sha256"] != version_four["staged_entries_sha256"]:
        raise RuntimeError("index version 변경이 staged entries를 바꿨습니다.")
    if version_two["raw_bytes_sha256"] == version_four["raw_bytes_sha256"]:
        raise RuntimeError("linked worktree raw index byte 변경을 검출하지 못했습니다.")
    print("[PASS] linked worktree actual raw index bytes·staged entries 분리 검출")


def check_learner_sentinels(base: Path, temporary: Path) -> None:
    learner = temporary / "learner-sentinels"
    copy_source(base, learner)
    target = learner / "learner-files/target"
    workspace = learner / "learner-files/.workspace"
    target.mkdir(parents=True)
    workspace.mkdir()
    (target / "sentinel.txt").write_text("target learner data\n", encoding="utf-8")
    (workspace / "sentinel.txt").write_text("workspace learner data\n", encoding="utf-8")
    (learner / "learner-files/target-link").symlink_to("target/sentinel.txt")
    before = capture(learner)
    replica = temporary / "learner-replica"
    copy_source(learner, replica)
    if capture(replica) != before:
        raise RuntimeError("path-specific copy가 learner target/.workspace를 보존하지 못했습니다.")
    validation = run_validator(learner)
    if (
        validation.returncode == 0
        or "정확한 managed tree가 다릅니다" not in validation.stdout
        or "허용되지 않은 생성 directory" in validation.stdout
    ):
        raise RuntimeError(
            "learner overlay를 exact tree 차이로 보고하지 않았거나 "
            f"target/.workspace를 broad generated로 오분류했습니다:\n{validation.stdout}"
        )
    cleaned = run(["make", "clean"], cwd=learner)
    if cleaned.returncode != 0 or capture(learner) != before:
        raise RuntimeError("make clean이 learner target/.workspace를 변경했습니다.")
    print("[PASS] learner target/.workspace bytes·mode·symlink와 clean 보존")


def check_workspace_safety(base: Path, temporary: Path) -> None:
    fixture = temporary / "workspace-safety"
    copy_source(base, fixture)
    before = capture(fixture)

    traversal = run(
        ["./scripts/new-workspace.sh", "../outside"],
        cwd=fixture,
    )
    if traversal.returncode == 0 or (temporary / "outside").exists():
        raise RuntimeError("workspace slug 경로 탈출을 차단하지 못했습니다.")

    created = run(
        ["./scripts/new-workspace.sh", "application-boundaries"],
        cwd=fixture,
    )
    workspace = fixture / ".workspace/application-boundaries"
    if created.returncode != 0 or not workspace.is_dir():
        raise RuntimeError(f"안전한 workspace 생성이 실패했습니다:\n{created.stdout}")
    if capture(fixture) != before:
        raise RuntimeError("canonical .workspace 생성이 preparation fingerprint를 바꿨습니다.")
    pom = (workspace / "pom.xml").read_text(encoding="utf-8")
    if "<relativePath>../../pom.xml</relativePath>" not in pom:
        raise RuntimeError("workspace POM이 repository root parent를 가리키지 않습니다.")

    duplicate_before = capture(workspace)
    duplicate = run(
        ["./scripts/new-workspace.sh", "application-boundaries"],
        cwd=fixture,
    )
    if duplicate.returncode == 0 or capture(workspace) != duplicate_before:
        raise RuntimeError("기존 workspace를 덮어썼습니다.")
    validated = run(
        ["python3", "scripts/workspace.py", "validate", "application-boundaries"],
        cwd=fixture,
    )
    if validated.returncode != 0:
        raise RuntimeError(f"workspace 공개 test 검사가 실패했습니다:\n{validated.stdout}")

    test = workspace / (
        "src/test/java/dev/guides/spring/boundaries/PreviewControllerTest.java"
    )
    test.write_text(test.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    drift = run(
        ["python3", "scripts/workspace.py", "validate", "application-boundaries"],
        cwd=fixture,
    )
    if drift.returncode == 0 or "byte-identical 공개 tests" not in drift.stdout:
        raise RuntimeError("workspace 공개 test 변조를 차단하지 못했습니다.")

    target_sentinel = workspace / "target/learner-sentinel.txt"
    target_sentinel.parent.mkdir()
    target_sentinel.write_text("preserve\n", encoding="utf-8")
    cleaned = run(["make", "clean"], cwd=fixture)
    if cleaned.returncode != 0 or target_sentinel.read_text(encoding="utf-8") != "preserve\n":
        raise RuntimeError("make clean이 learner workspace를 지웠습니다.")

    linked_fixture = temporary / "workspace-root-symlink"
    copy_source(base, linked_fixture)
    outside = temporary / "workspace-outside"
    outside.mkdir()
    (linked_fixture / ".workspace").symlink_to(outside, target_is_directory=True)
    linked = run(
        ["./scripts/new-workspace.sh", "security-boundaries"],
        cwd=linked_fixture,
    )
    if linked.returncode == 0 or any(outside.iterdir()):
        raise RuntimeError("symlink .workspace 경로 탈출을 차단하지 못했습니다.")
    print("[PASS] canonical .workspace 생성·경로 탈출·test drift·보존 계약")


def check_designated_runtime_mutant(base: Path, temporary: Path) -> None:
    mutant = temporary / "designated-runtime"
    copy_source(base, mutant)
    controller = mutant / (
        "exercises/application-boundaries/skeleton/src/main/java/"
        "dev/guides/spring/boundaries/PreviewController.java"
    )
    needle = "  public PreviewResponse preview(@Valid @RequestBody PreviewRequest request) {\n"
    replacement = needle + (
        "    if (request.quantity() == 101) {\n"
        "      throw new AssertionError(\"Status expected:<409> but was:<200>\");\n"
        "    }\n"
    )
    replace(controller, needle, replacement)

    environment = os.environ.copy()
    maven_home = environment.get(
        "MAVEN_USER_HOME", str(ROOT / ".guide/backend-spring-boot/maven-home")
    )
    repository = environment.get(
        "GUIDE_MAVEN_REPOSITORY", str(ROOT / ".guide/backend-spring-boot/m2")
    )
    if not Path(maven_home).is_dir() or not Path(repository).is_dir():
        raise RuntimeError("designated runtime mutant용 prepared Maven cache가 없습니다.")
    environment["MAVEN_USER_HOME"] = maven_home
    environment["GUIDE_MAVEN_REPOSITORY"] = repository
    result = run(
        ["./scripts/verify-skeletons.sh", "application-boundaries"],
        cwd=mutant,
        environment=environment,
    )
    if result.returncode == 0 or "지정" not in result.stdout:
        raise RuntimeError(f"임의 AssertionError runtime mutant를 허용했습니다:\n{result.stdout}")
    print("[PASS] arbitrary AssertionError designated runtime mutant 거부")


def main() -> int:
    try:
        with tempfile.TemporaryDirectory(prefix="spring-validator-self-test-") as raw:
            temporary = Path(raw)
            base = temporary / "base"
            copy_source(ROOT, base)
            baseline = run_validator(base)
            if baseline.returncode != 0:
                raise RuntimeError(f"validator 기준 tree가 실패했습니다.\n{baseline.stdout}")

            for name, mutate, expected in MUTANTS:
                mutant = temporary / name
                copy_source(base, mutant)
                mutate(mutant)
                result = run_validator(mutant)
                if result.returncode == 0 or expected not in result.stdout:
                    raise RuntimeError(
                        f"mutant를 검출하지 못했습니다: {name}\n{result.stdout}"
                    )
                print(f"[PASS] validator mutant: {name}")

            check_learner_sentinels(base, temporary)
            check_workspace_safety(base, temporary)
            check_marker_contract(temporary)
            check_linked_raw_index(temporary)
            check_log_preflights(base, temporary)
            check_designated_runtime_mutant(base, temporary)
    except (OSError, RuntimeError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        print(f"validator 자기검증 실패: {error}", file=sys.stderr)
        return 1

    print("Spring Boot validator·preflight·marker·runtime mutant 자기검증 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
