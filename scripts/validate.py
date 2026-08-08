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
        if path.name in {"target", "__pycache__", ".pytest_cache", ".workspace"}
    ]
    result.require(not generated, f"generated artifacts remain: {[relative(path) for path in generated]}")


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
    seen: dict[str, str] = {}
    for readme in sorted((ROOT / "exercises").rglob("README.md")):
        text = readme.read_text(encoding="utf-8")
        start = text.find("## 완료 기준\n")
        end = text.find("## 검증\n")
        if start < 0 or end < 0:
            continue
        section = re.sub(r"\s+", " ", text[start:end]).strip()
        previous = seen.get(section)
        if previous:
            result.error(f"copied completion/self-explanation sections: {previous}, {relative(readme)}")
        seen[section] = relative(readme)


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
    kafka_files = [
        ROOT / "prepare.sh",
        ROOT / "verify.sh",
        ROOT / "exercises/90-optional-labs/single-broker-kraft/skeleton/compose.yaml",
        ROOT / "exercises/90-optional-labs/single-broker-kraft/reference/compose.yaml",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in kafka_files)
    result.require(
        "apache/kafka:4.3.1@sha256:77e3df9054047a88b520d0cc46e16696d3b22022e1d580aeccd2632df6532837" in combined,
        "Kafka must pin the approved 4.3.1 immutable digest",
    )
    result.require("apache/kafka:latest" not in combined, "floating Kafka latest tag is forbidden")


def check_scripts(result: Validation) -> None:
    for path in sorted(ROOT.rglob("*.sh")):
        if any(part in {"target", ".guide"} for part in path.parts):
            continue
        mode = path.stat().st_mode
        result.require(
            bool(mode & stat.S_IXUSR),
            f"shell script is not executable: {relative(path)}",
        )

    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {"target", ".guide"} for part in path.parts):
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


def main() -> int:
    os.chdir(ROOT)
    result = Validation()
    check_expected_tree(result)
    check_markdown(result)
    check_unique_pedagogy(result)
    check_text_hygiene(result)
    check_java_exercises(result)
    check_maven_modules(result)
    check_pins(result)
    check_scripts(result)
    return result.finish()


if __name__ == "__main__":
    raise SystemExit(main())
