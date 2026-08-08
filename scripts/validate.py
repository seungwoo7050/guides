#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import stat
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_DOCS = {
    "docs/00-roadmap.md",
    "docs/01-boundaries-and-failure/01-partial-failure-and-uncertain-outcomes.md",
    "docs/01-boundaries-and-failure/02-service-boundaries-and-data-ownership.md",
    "docs/01-boundaries-and-failure/03-synchronous-and-asynchronous-decisions.md",
    "docs/02-delivery-and-consistency/01-idempotency-and-single-effects.md",
    "docs/02-delivery-and-consistency/02-outbox-saga-and-reconciliation.md",
    "docs/02-delivery-and-consistency/03-contracts-versioning-and-order.md",
    "docs/02-delivery-and-consistency/04-read-models-and-late-events.md",
    "docs/03-resilience-and-load/01-timeouts-retries-circuit-breakers-and-dlq.md",
    "docs/03-resilience-and-load/02-backpressure-bulkheads-and-load-shedding.md",
    "docs/04-release-and-evidence/01-multi-repository-builds-and-release-manifests.md",
    "docs/04-release-and-evidence/02-distributed-observability.md",
    "docs/04-release-and-evidence/03-end-to-end-chaos-and-failure-evidence.md",
    "docs/04-release-and-evidence/04-performance-gates-and-claims.md",
    "docs/05-capstone.md",
    "docs/90-optional-labs/01-single-broker-kraft.md",
}

JAVA_EXERCISES = {
    "exercises/01-boundaries-and-failure/01-uncertain-outcome",
    "exercises/01-boundaries-and-failure/02-service-boundary",
    "exercises/01-boundaries-and-failure/03-request-decision",
    "exercises/02-delivery-and-consistency/01-duplicate-delivery",
    "exercises/02-delivery-and-consistency/02-outbox-reconciliation",
    "exercises/02-delivery-and-consistency/03-contracts-and-order",
    "exercises/02-delivery-and-consistency/04-read-model-rebuild",
    "exercises/03-resilience-and-load/01-retry-budget",
    "exercises/03-resilience-and-load/02-backpressure",
    "exercises/04-release-and-evidence/02-observability-correlation",
    "exercises/04-release-and-evidence/03-chaos-evidence",
    "exercises/04-release-and-evidence/04-performance-gate",
    "exercises/05-capstone/reservation-flow",
}

NON_JAVA_EXERCISES = {
    "exercises/04-release-and-evidence/01-release-manifest",
    "exercises/90-optional-labs/single-broker-kraft",
}

EXPECTED_MODULES = [
    "exercises/test-support",
    *[f"{path}/reference" for path in sorted(JAVA_EXERCISES)],
]

FORBIDDEN_PATHS = {
    "docs/01-service-boundaries-and-dependency-direction.md",
    "docs/02-synchronous-and-asynchronous-decisions.md",
    "docs/03-idempotency-and-exactly-once-effects.md",
    "docs/04-outbox-saga-and-reconciliation.md",
    "docs/05-event-contracts-versioning-and-order.md",
    "docs/06-read-models-late-events-and-races.md",
    "docs/07-timeouts-retries-circuit-breakers-and-dlq.md",
    "docs/08-multi-repository-builds-and-release-manifests.md",
    "docs/09-end-to-end-chaos-and-failure-evidence.md",
    "docs/10-performance-gates-and-claims.md",
    "exercises/duplicate-delivery",
    "exercises/event-contract-drift",
    "exercises/out-of-order-events",
    "exercises/performance-gate",
    "exercises/release-manifest",
    "exercises/request-decision",
    "exercises/single-broker-kraft",
    "projects/reliable-delivery-pipeline",
    "reference",
    "scripts/preflight.sh",
    "scripts/smoke-javac.sh",
}

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
H1 = re.compile(r"^# (?!#)", re.MULTILINE)
FENCED_CODE = re.compile(r"^```[^\n]*\n.*?^```[ \t]*$", re.MULTILINE | re.DOTALL)
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)
PEDAGOGY = ("## 목표", "## 완료 기준", "## 자기 설명", "## 검증")
XML_NS = {"m": "http://maven.apache.org/POM/4.0.0"}


class Validation:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.error(message)

    def finish(self) -> int:
        if self.errors:
            print("repository validation failed:", file=sys.stderr)
            for message in self.errors:
                print(f"  - {message}", file=sys.stderr)
            return 1
        print("repository structure and learning contracts verified")
        return 0


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def learner_workspace(relative_path: Path) -> bool:
    return bool(relative_path.parts) and relative_path.parts[0] == ".workspace"


def generated_path(relative_path: Path) -> bool:
    parts = relative_path.parts
    for index, part in enumerate(parts):
        prefix = parts[:index]
        if part == "target":
            if not prefix:
                return True
            if prefix == ("exercises", "test-support"):
                return True
            if prefix and prefix[0] == "exercises" and prefix[-1] in {"reference", "skeleton"}:
                return True
        if part in {"__pycache__", ".pytest_cache"} and prefix and prefix[0] in {
            "scripts", "exercises"
        }:
            return True
    return relative_path.suffix in {".pyc", ".pyo", ".jfr"}


def markdown_files() -> list[Path]:
    files = [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]
    files.extend(sorted((ROOT / "docs").rglob("*.md")))
    files.extend(sorted((ROOT / "exercises").rglob("README.md")))
    return [path for path in files if path.is_file()]


def check_expected_tree(result: Validation) -> None:
    actual_docs = {
        relative(path)
        for path in (ROOT / "docs").rglob("*.md")
        if path.is_file()
    }
    result.require(
        actual_docs == EXPECTED_DOCS,
        "docs tree differs from the roadmap "
        f"(missing={sorted(EXPECTED_DOCS - actual_docs)}, "
        f"unexpected={sorted(actual_docs - EXPECTED_DOCS)})",
    )

    expected_exercises = JAVA_EXERCISES | NON_JAVA_EXERCISES
    actual_exercises = {
        relative(path.parent)
        for path in (ROOT / "exercises").rglob("README.md")
        if path.is_file()
    }
    result.require(
        actual_exercises == expected_exercises,
        "exercise tree differs from the curriculum "
        f"(missing={sorted(expected_exercises - actual_exercises)}, "
        f"unexpected={sorted(actual_exercises - expected_exercises)})",
    )

    for exercise in sorted(expected_exercises):
        result.require((ROOT / exercise / "README.md").is_file(), f"missing {exercise}/README.md")

    for exercise in sorted(JAVA_EXERCISES):
        for variant in ("skeleton", "reference"):
            base = ROOT / exercise / variant
            result.require((base / "pom.xml").is_file(), f"missing {exercise}/{variant}/pom.xml")
            result.require((base / "src/main/java").is_dir(), f"missing main sources in {exercise}/{variant}")
            result.require((base / "src/test/java").is_dir(), f"missing test sources in {exercise}/{variant}")

    required_root = {
        "prepare.sh",
        "verify.sh",
        "Makefile",
        "pom.xml",
        "mvnw",
        ".mvn/jvm.config",
        ".mvn/wrapper/maven-wrapper.properties",
        "config/repository-files.txt",
        "scripts/validate.py",
        "scripts/verify-java.sh",
        "scripts/verify-skeletons.sh",
        "scripts/verify-nonjava.sh",
        "scripts/repository_state.py",
        "scripts/test-validator.py",
    }
    for path in sorted(required_root):
        result.require((ROOT / path).is_file(), f"missing required file: {path}")

    for path in sorted(FORBIDDEN_PATHS):
        result.require(not (ROOT / path).exists(), f"obsolete path remains after prepare: {path}")

    generated = [
        path for path in ROOT.rglob("*")
        if not learner_workspace(path.relative_to(ROOT))
        and generated_path(path.relative_to(ROOT))
    ]
    result.require(not generated, f"generated artifacts remain: {[relative(path) for path in generated]}")


def check_repository_manifest(result: Validation) -> None:
    manifest = ROOT / "config/repository-files.txt"
    if not manifest.is_file():
        return
    expected = {
        line.strip()
        for line in manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    actual: set[str] = set()
    for path in ROOT.rglob("*"):
        rel_path = path.relative_to(ROOT)
        if not rel_path.parts or rel_path.parts[0] in {".git", ".guide"}:
            continue
        if learner_workspace(rel_path) or generated_path(rel_path) or path.name == ".DS_Store":
            continue
        if path.is_file() or path.is_symlink():
            actual.add(rel_path.as_posix())
    result.require(
        actual == expected,
        "managed repository tree differs from its exact manifest "
        f"(missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)})",
    )
    for expected_path in sorted(expected):
        candidate = ROOT / expected_path
        result.require(
            candidate.is_file() and not candidate.is_symlink(),
            f"managed path must be a regular file, not a symlink: {expected_path}",
        )


def check_markdown(result: Validation) -> None:
    for path in markdown_files():
        text = path.read_text(encoding="utf-8")
        rel = relative(path)
        prose = FENCED_CODE.sub("", text)
        result.require(len(H1.findall(prose)) == 1, f"{rel} must contain exactly one H1")
        result.require(text.count("```") % 2 == 0, f"{rel} has an unclosed fenced code block")
        if path.name == "README.md" and rel.startswith("exercises/"):
            offsets = []
            for heading in PEDAGOGY:
                result.require(text.count(heading + "\n") == 1, f"{rel} must contain exactly one {heading}")
                offsets.append(text.find(heading + "\n"))
            result.require(offsets == sorted(offsets), f"{rel} pedagogy headings must be ordered")
            complete_start = text.find("## 완료 기준\n")
            explain_start = text.find("## 자기 설명\n")
            verify_start = text.find("## 검증\n")
            completion = text[complete_start:explain_start]
            explanation = text[explain_start:verify_start]
            bullets = re.findall(r"^-\s+\S", completion, re.MULTILINE)
            questions = [line.strip() for line in explanation.splitlines() if line.startswith("-")]
            result.require(len(bullets) >= 3, f"{rel} completion criteria need at least three observable bullets")
            result.require(
                len(questions) >= 2 and all(line.endswith("?") for line in questions),
                f"{rel} self-explanation needs at least two questions ending in ?",
            )

        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip()
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            raw_path, _, fragment = target.partition("#")
            target = urllib.parse.unquote(raw_path.split("?", 1)[0])
            if target.startswith("/"):
                result.error(f"{rel} uses an absolute local link: {raw_target}")
                continue
            resolved = (path if not target else path.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                result.error(f"{rel} links outside the repository: {raw_target}")
                continue
            if resolved.is_dir():
                resolved = resolved / "README.md"
            result.require(resolved.exists(), f"broken link in {rel}: {raw_target}")
            if fragment and resolved.is_file() and resolved.suffix == ".md":
                linked = resolved.read_text(encoding="utf-8")
                anchors = {
                    re.sub(r"[^\w\-가-힣 ]", "", title.lower()).strip().replace(" ", "-")
                    for title in HEADING.findall(linked)
                }
                result.require(urllib.parse.unquote(fragment).lower() in anchors,
                               f"broken anchor in {rel}: {raw_target}")


def check_unique_pedagogy(result: Validation) -> None:
    seen_completion: dict[str, str] = {}
    seen_explanation: dict[str, str] = {}
    for readme in sorted((ROOT / "exercises").rglob("README.md")):
        text = readme.read_text(encoding="utf-8")
        completion_start = text.find("## 완료 기준\n")
        explanation_start = text.find("## 자기 설명\n")
        verify_start = text.find("## 검증\n")
        if min(completion_start, explanation_start, verify_start) < 0:
            continue
        completion = re.sub(
            r"\s+", " ", text[completion_start:explanation_start]
        ).strip()
        explanation = re.sub(
            r"\s+", " ", text[explanation_start:verify_start]
        ).strip()
        previous_completion = seen_completion.get(completion)
        if previous_completion:
            result.error(
                f"copied completion section: {previous_completion}, {relative(readme)}"
            )
        previous_explanation = seen_explanation.get(explanation)
        if previous_explanation:
            result.error(
                f"copied self-explanation section: {previous_explanation}, {relative(readme)}"
            )
        seen_completion[completion] = relative(readme)
        seen_explanation[explanation] = relative(readme)


def check_learner_commands(result: Validation) -> None:
    for exercise in sorted(JAVA_EXERCISES):
        readme = ROOT / exercise / "README.md"
        text = readme.read_text(encoding="utf-8")
        verify_start = text.find("## 검증\n")
        workspace_name = re.sub(r"^\d+-", "", Path(exercise).name)
        command = f"./scripts/verify-java.sh .workspace/{workspace_name}"
        result.require(
            verify_start >= 0 and command in text[verify_start:],
            f"{relative(readme)} must document learner command: {command}",
        )
    release = ROOT / "exercises/04-release-and-evidence/01-release-manifest/README.md"
    release_command = (
        "python3 exercises/04-release-and-evidence/01-release-manifest/tests/"
        "verify_manifest.py .workspace/release-manifest/manifest_check.py"
    )
    result.require(
        release_command in release.read_text(encoding="utf-8"),
        f"{relative(release)} must document learner command: {release_command}",
    )


def check_text_hygiene(result: Validation) -> None:
    owned_roots = [
        ROOT / ".gitignore",
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "Makefile",
        ROOT / "pom.xml",
        ROOT / "prepare.sh",
        ROOT / "verify.sh",
        ROOT / "docs",
        ROOT / "exercises",
        ROOT / "scripts",
    ]
    paths: list[Path] = []
    for owned in owned_roots:
        if owned.is_file():
            paths.append(owned)
        elif owned.is_dir():
            paths.extend(path for path in owned.rglob("*") if path.is_file())

    generated_names = {".git", "target", ".workspace", "__pycache__", ".guide"}
    for path in sorted(set(paths)):
        if any(part in generated_names for part in path.parts):
            continue
        try:
            data = path.read_bytes()
        except OSError as error:
            result.error(f"cannot read {relative(path)}: {error}")
            continue
        rel = relative(path)
        if b"\r\n" in data:
            result.error(f"CRLF line endings are not allowed: {rel}")
        if b"\x00" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                result.error(f"trailing whitespace: {rel}:{number}")
                break


def check_java_exercises(result: Validation) -> None:
    for exercise in sorted(JAVA_EXERCISES):
        skeleton = ROOT / exercise / "skeleton"
        reference = ROOT / exercise / "reference"

        skeleton_tests = {
            path.relative_to(skeleton / "src/test/java")
            for path in (skeleton / "src/test/java").rglob("*.java")
        }
        reference_tests = {
            path.relative_to(reference / "src/test/java")
            for path in (reference / "src/test/java").rglob("*.java")
        }
        result.require(
            skeleton_tests == reference_tests and bool(skeleton_tests),
            f"{exercise} skeleton/reference test sets must match",
        )
        for test_path in sorted(skeleton_tests):
            left = (skeleton / "src/test/java" / test_path).read_bytes()
            right = (reference / "src/test/java" / test_path).read_bytes()
            result.require(
                left == right,
                f"{exercise} must run byte-identical tests against skeleton and reference",
            )

        for path in reference.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in {".java", ".xml", ".py", ".sh"}:
                continue
            text = path.read_text(encoding="utf-8")
            result.require(
                "TODO" not in text and "FIXME" not in text,
                f"reference implementation contains unfinished marker: {relative(path)}",
            )


def check_maven_modules(result: Validation) -> None:
    pom = ROOT / "pom.xml"
    try:
        tree = ET.parse(pom)
    except ET.ParseError as error:
        result.error(f"invalid root pom.xml: {error}")
        return

    modules = [
        element.text.strip()
        for element in tree.findall("./m:modules/m:module", XML_NS)
        if element.text
    ]
    result.require(
        modules == EXPECTED_MODULES,
        "root pom modules must exactly match reference exercises "
        f"(expected={EXPECTED_MODULES}, actual={modules})",
    )
    for module in modules:
        result.require((ROOT / module / "pom.xml").is_file(), f"module has no pom.xml: {module}")

    pom_text = pom.read_text(encoding="utf-8")
    result.require("<maven.compiler.release>17</maven.compiler.release>" in pom_text,
                   "root Maven build must target Java release 17")


def check_pins(result: Validation) -> None:
    wrapper = (ROOT / ".mvn/wrapper/maven-wrapper.properties").read_text(encoding="utf-8")
    result.require("wrapperVersion=3.3.4" in wrapper, "Maven Wrapper launcher must pin 3.3.4")
    result.require("apache-maven-3.9.16-bin.zip" in wrapper, "Maven Wrapper must pin Maven 3.9.16")
    result.require(
        "distributionSha256Sum=5af3b743dd8b876b5c45da33b676251e5f1687712644abb4ee519ca56e1d89ce" in wrapper,
        "Maven Wrapper must pin the official Maven 3.9.16 SHA-256",
    )
    approved = (
        "apache/kafka:4.3.1@sha256:"
        "77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837"
    )
    for relative_path in ("prepare.sh", "verify.sh"):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        result.require(
            f'KAFKA_IMAGE="{approved}"' in text,
            f"{relative_path} must pin the exact approved Kafka image",
        )
    for relative_path in (
        "exercises/90-optional-labs/single-broker-kraft/skeleton/compose.yaml",
        "exercises/90-optional-labs/single-broker-kraft/reference/compose.yaml",
    ):
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        images = re.findall(r"^\s*image:\s*(\S+)\s*$", text, re.MULTILINE)
        result.require(
            images == [approved],
            f"{relative_path} must declare only the exact approved Kafka image",
        )


def check_scripts(result: Validation) -> None:
    for path in sorted(ROOT.rglob("*.sh")):
        relative_path = path.relative_to(ROOT)
        if learner_workspace(relative_path) or any(
            part in {"target", ".guide"} for part in relative_path.parts
        ):
            continue
        mode = path.stat().st_mode
        result.require(
            bool(mode & stat.S_IXUSR),
            f"shell script is not executable: {relative(path)}",
        )

    for path in sorted(ROOT.rglob("*.py")):
        relative_path = path.relative_to(ROOT)
        if learner_workspace(relative_path) or any(
            part in {"target", ".guide"} for part in relative_path.parts
        ):
            continue
        text = path.read_text(encoding="utf-8")
        try:
            compile(text, str(path), "exec")
        except SyntaxError as error:
            result.error(f"invalid Python syntax in {relative(path)}: {error}")

    for relative_path in (
        "mvnw",
        "prepare.sh",
        "verify.sh",
        "scripts/repository_state.py",
        "scripts/test-validator.py",
        "scripts/validate.py",
    ):
        path = ROOT / relative_path
        result.require(
            path.is_file() and bool(path.stat().st_mode & stat.S_IXUSR),
            f"required command is not executable: {relative_path}",
        )

    nonjava = (ROOT / "scripts/verify-nonjava.sh").read_text(encoding="utf-8")
    kraft = (
        ROOT / "exercises/90-optional-labs/single-broker-kraft/verify.sh"
    ).read_text(encoding="utf-8")
    result.require(
        "GUIDE_SEMANTIC: invalid manifest was accepted (expected duplicate)" in nonjava,
        "release-manifest skeleton must use its designated semantic failure",
    )
    result.require(
        "INVALID_REPLICATION_FACTOR" in kraft
        and "__consumer_offsets" in kraft
        and "direct partition consumer failed; group result would be ambiguous" in kraft,
        "KRaft skeleton must distinguish direct-consumer success from the designated group failure",
    )

    for documentation in (ROOT / "README.md", ROOT / "CONTRIBUTING.md"):
        text = documentation.read_text(encoding="utf-8")
        for command in (
            "make prepare\n",
            "make check\n",
            "VERIFY_LOG=/tmp/guide-distributed-services-verify.log make verify\n",
            "make clean\n",
        ):
            result.require(
                command in text,
                f"{relative(documentation)} must document public command: {command.strip()}",
            )

    verifier = (ROOT / "verify.sh").read_text(encoding="utf-8")
    result.require(
        "--exclude='/.workspace/'" not in verifier,
        "verify.sh must copy learner .workspace for source preservation",
    )
    preparer = (ROOT / "prepare.sh").read_text(encoding="utf-8")
    for name, text in (("prepare.sh", preparer), ("verify.sh", verifier)):
        result.require(
            "--exclude='/.git'" in text and "--exclude='/.git/'" not in text,
            f"{name} must exclude linked-worktree .git files from isolated copies",
        )
        result.require(
            "export GIT_OPTIONAL_LOCKS=0" in text,
            f"{name} must forbid optional Git index writes",
        )
        result.require(
            "\n  mvnw\n" in text,
            f"{name} preparation fingerprint must include mvnw",
        )
        result.require(
            'find "$ROOT/exercises" -type f -name pom.xml | sort' in text,
            f"{name} preparation fingerprint must include every exercise pom.xml",
        )
    state_helper = (ROOT / "scripts/repository_state.py").read_text(encoding="utf-8")
    result.require(
        '"raw_bytes_sha256"' in state_helper and '"GIT_OPTIONAL_LOCKS": "0"' in state_helper,
        "repository state must hash raw linked-worktree index bytes without optional writes",
    )
    result.require(
        'MARKER_TMP=""' in preparer
        and '  if [[ -n "$MARKER_TMP" ]]; then\n'
        '    rm -f -- "$MARKER_TMP"\n'
        '  fi' in preparer
        and "run_managed write_marker_file" in preparer,
        "prepare must track and clean its atomic marker writer and exact temporary path",
    )
    learner_verifier = (ROOT / "scripts/verify-java.sh").read_text(encoding="utf-8")
    result.require(
        "canonical_test_root" in learner_verifier
        and "workspace slug must map to exactly one canonical skeleton" in learner_verifier,
        "learner Java verification must bind workspace implementations to canonical tests",
    )
    result.require(
        'test_root="$(canonical_test_root "$module")"' in learner_verifier
        and 'find "$test_root" -type f -name \'*.java\'' in learner_verifier,
        "learner Java verification must compile canonical tests rather than workspace tests",
    )
    for field in (
        "docker_compose_version",
        "python_version",
        "git_version",
        "rsync_version",
    ):
        result.require(
            f'"{field}"' in preparer and f'"{field}"' in verifier,
            f"prepare/verify marker contract must record and validate {field}",
        )


def main() -> int:
    os.chdir(ROOT)
    result = Validation()
    check_expected_tree(result)
    check_repository_manifest(result)
    check_markdown(result)
    check_unique_pedagogy(result)
    check_learner_commands(result)
    check_text_hygiene(result)
    check_java_exercises(result)
    check_maven_modules(result)
    check_pins(result)
    check_scripts(result)
    return result.finish()


if __name__ == "__main__":
    raise SystemExit(main())
