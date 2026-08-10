#!/usr/bin/env python3
"""Validate guide layout, learning-kit structure, and local Markdown links."""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path
from urllib.parse import unquote

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
DOC_PATTERN = re.compile(r"^(\d{2})-[a-z0-9-]+\.md$")
SCENARIO_ITEM = re.compile(r"^\s*(\d+)\.\s+\S", re.MULTILINE)
FAILURE_ROW = re.compile(r"^\|\s*F\d+\s*\|", re.MULTILINE)

LABS = (
    "01-image-and-memory-audit",
    "02-interrupt-event-path",
    "03-sensor-driver-state-machine",
    "04-deadline-and-priority-review",
    "05-power-loss-persistence",
    "06-update-rollback-model",
)
LEARNING_PARTS = ("starter", "reference", "fixtures", "known-wrong")

REQUIRED = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSES/CC-BY-4.0.txt",
    "LICENSES/MIT.txt",
    "Makefile",
    "prepare.sh",
    "verify.sh",
    "scripts/check_docs.py",
    "scripts/check_external_links.py",
    "scripts/check_learning_contracts.py",
    "scripts/source_fingerprint.py",
    "scripts/run_with_timeout.py",
    "scripts/test_verifier.py",
    "scripts/test_verify_safety.py",
    "scripts/test_workspace_tools.py",
    "scripts/new-workspace.sh",
    "docs/00-roadmap.md",
    "docs/01-firmware-boundary/01-host-target-and-firmware-lifecycle.md",
    "docs/01-firmware-boundary/02-cross-build-elf-map-and-memory-budget.md",
    "docs/01-firmware-boundary/03-reset-startup-and-linker-contract.md",
    "docs/01-firmware-boundary/04-mmio-registers-and-volatile.md",
    "docs/02-events-and-drivers/05-gpio-uart-timers-and-driver-boundaries.md",
    "docs/02-events-and-drivers/06-interrupts-priority-and-deferred-work.md",
    "docs/02-events-and-drivers/07-i2c-spi-transactions-and-device-state.md",
    "docs/02-events-and-drivers/08-dma-cache-and-buffer-ownership.md",
    "docs/03-time-and-concurrency/09-clocks-timeouts-deadlines-and-wraparound.md",
    "docs/03-time-and-concurrency/10-superloop-state-machines-and-event-queues.md",
    "docs/03-time-and-concurrency/11-rtos-tasks-queues-and-priority-inversion.md",
    "docs/03-time-and-concurrency/12-memory-budgets-stacks-and-allocation.md",
    "docs/04-reliability-and-lifecycle/13-reset-cause-watchdog-and-fault-recovery.md",
    "docs/04-reliability-and-lifecycle/14-power-clocks-sleep-and-wakeup.md",
    "docs/04-reliability-and-lifecycle/15-flash-persistence-and-power-loss.md",
    "docs/04-reliability-and-lifecycle/16-boot-images-update-and-rollback.md",
    "docs/05-portability-and-verification/17-devicetree-kconfig-and-device-model.md",
    "docs/05-portability-and-verification/18-debugging-tracing-and-crash-evidence.md",
    "docs/05-portability-and-verification/19-simulation-unit-integration-and-hil.md",
    "docs/05-portability-and-verification/20-upstream-contribution-and-production-boundaries.md",
    "exercises/README.md",
    *(f"exercises/{name}/README.md" for name in LABS),
    "capstone/field-sensor-node/README.md",
    "capstone/field-sensor-node/acceptance.md",
    "capstone/field-sensor-node/failure-matrix.md",
    "examples/README.md",
    "examples/interrupt-event-model/README.md",
    "examples/interrupt-event-model/model.py",
    "examples/update-state-model/README.md",
    "examples/update-state-model/model.py",
    "examples/tests/test_models.py",
    "reference/glossary.md",
    "reference/version-baseline.md",
    "reference/sources.md",
    "reference/datasheet-reading-checklist.md",
    "reference/firmware-review-checklist.md",
    "reference/cortex-m-riscv-crosswalk.md",
    "reference/evidence-template.md",
]

EXPECTED_DOC_NUMBERS = list(range(1, 21))
EXPECTED_EXERCISES = list(range(1, 7))


class ValidationError(RuntimeError):
    pass


def slugify_heading(text: str) -> str:
    text = re.sub(r"[`*_~]", "", text.strip().lower())
    text = re.sub(r"[^\w\-\s가-힣]", "", text, flags=re.UNICODE)
    return re.sub(r"\s+", "-", text)


def heading_slugs(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    counts: dict[str, int] = {}
    slugs: set[str] = set()
    for _, heading in HEADING.findall(text):
        base = slugify_heading(heading)
        count = counts.get(base, 0)
        counts[base] = count + 1
        slugs.add(base if count == 0 else f"{base}-{count}")
    return slugs


def resolve_local_link(source: Path, raw: str, root: Path) -> tuple[Path, str | None] | None:
    raw = raw.strip()
    if not raw or raw.startswith(("http://", "https://", "mailto:", "tel:", "data:")):
        return None
    if raw.startswith("#"):
        return source, unquote(raw[1:])
    target_text, separator, fragment = raw.partition("#")
    target = (source.parent / unquote(target_text)).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValidationError(f"{source.relative_to(root)}: 저장소 밖 링크 {raw}") from exc
    return target, unquote(fragment) if separator else None


def substantive_length(text: str) -> int:
    kept = []
    in_fence = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or line.lstrip().startswith("#"):
            continue
        if re.fullmatch(r"[\s|:\-]+", line):
            continue
        kept.append(line)
    return len("".join(kept).strip())


def content_files(directory: Path) -> list[Path]:
    if not directory.is_dir() or directory.is_symlink():
        return []
    return sorted(
        path for path in directory.rglob("*")
        if path.is_file() and not path.is_symlink() and path.name != ".DS_Store"
        and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )


def validate_learning_unit(root: Path, directory: Path, *, capstone: bool = False) -> list[str]:
    errors: list[str] = []
    relative = directory.relative_to(root)
    readme = directory / "README.md"
    checker = directory / "check.py"
    if not readme.is_file() or readme.is_symlink():
        errors.append(f"학습 단위 README 누락: {relative}/README.md")
    if not checker.is_file() or checker.is_symlink():
        errors.append(f"학습 checker 누락: {relative}/check.py")
    else:
        mode = checker.stat().st_mode
        if not mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) or not os.access(checker, os.X_OK):
            errors.append(f"실행 불가능한 checker: {relative}/check.py")
        if not checker.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"):
            errors.append(f"checker Python shebang 누락: {relative}/check.py")
    for name in LEARNING_PARTS:
        part = directory / name
        files = content_files(part)
        if not part.is_dir() or part.is_symlink():
            errors.append(f"학습 계약 directory 누락 또는 symlink: {relative}/{name}")
        elif not files:
            errors.append(f"빈 학습 계약 directory: {relative}/{name}")
        for path in files:
            if path.suffix == ".json":
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except (UnicodeError, json.JSONDecodeError) as exc:
                    errors.append(f"JSON 오류 {path.relative_to(root)}: {exc}")
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        headings = HEADING.findall(text)
        required_terms = ("문제", "결과물", "완료 조건") if not capstone else ("문제", "결과물", "불변식", "완료")
        minimum = 1100 if not capstone else 1800
        if (
            substantive_length(text) < minimum
            or len(headings) < (6 if not capstone else 10)
            or any(term not in text for term in required_terms)
            or any(term not in text for term in ("check.py", "starter", "reference"))
        ):
            label = "capstone" if capstone else "실습"
            errors.append(f"교육 계약이 부족한 {label}: {readme.relative_to(root)}")
    return errors


def markdown_files(root: Path) -> list[Path]:
    ignored = {".git", ".guide", "__pycache__", "workspace", "capstone-workspace", "build"}
    return sorted(path for path in root.rglob("*.md") if not ignored.intersection(path.relative_to(root).parts))


def section(text: str, heading: str) -> str | None:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    return None if match is None else match.group(1)


def validate(root: Path) -> dict[str, int]:
    root = root.resolve()
    errors: list[str] = []
    for relative in REQUIRED:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"필수 파일 누락 또는 symlink: {relative}")
        elif path.stat().st_size == 0:
            errors.append(f"빈 필수 파일: {relative}")

    docs = sorted((root / "docs").glob("[0-9][0-9]-*/*.md"))
    numbers = [int(match.group(1)) for path in docs if (match := DOC_PATTERN.match(path.name))]
    if numbers != EXPECTED_DOC_NUMBERS:
        errors.append(f"개념 문서 번호가 01..20과 다릅니다: {numbers}")

    exercise_dirs = sorted(path for path in (root / "exercises").iterdir() if path.is_dir() and re.match(r"^\d{2}-", path.name))
    exercise_numbers = [int(path.name[:2]) for path in exercise_dirs]
    if exercise_numbers != EXPECTED_EXERCISES or [path.name for path in exercise_dirs] != list(LABS):
        errors.append(f"실습 directory가 계약과 다릅니다: {[path.name for path in exercise_dirs]}")
    for name in LABS:
        errors.extend(validate_learning_unit(root, root / "exercises" / name))

    capstone = root / "capstone/field-sensor-node"
    errors.extend(validate_learning_unit(root, capstone, capstone=True))
    acceptance = capstone / "acceptance.md"
    if acceptance.is_file():
        acceptance_text = acceptance.read_text(encoding="utf-8")
        scenario_text = section(acceptance_text, "필수 시나리오")
        scenarios = [] if scenario_text is None else [int(number) for number in SCENARIO_ITEM.findall(scenario_text)]
        if substantive_length(acceptance_text) < 900:
            errors.append("교육 계약이 부족한 capstone acceptance: capstone/field-sensor-node/acceptance.md")
        if scenarios != list(range(1, 13)):
            errors.append(f"capstone acceptance 필수 시나리오가 1..12와 다릅니다: {scenarios}")
    failure_matrix = capstone / "failure-matrix.md"
    if failure_matrix.is_file():
        matrix_text = failure_matrix.read_text(encoding="utf-8")
        if substantive_length(matrix_text) < 700 or len(FAILURE_ROW.findall(matrix_text)) < 12:
            errors.append("교육 계약이 부족한 capstone failure matrix")

    example_fixtures = sorted((root / "examples").glob("*/fixtures/*.json"))
    if len(example_fixtures) < 8:
        errors.append(f"상태 모델 fixture가 부족합니다: {len(example_fixtures)}")
    for path in example_fixtures:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON 오류 {path.relative_to(root)}: {exc}")
            continue
        if not isinstance(data, dict) or not isinstance(data.get("events"), list) or not isinstance(data.get("expected"), dict):
            errors.append(f"fixture 계약 오류: {path.relative_to(root)}")

    markdown = markdown_files(root)
    slug_cache: dict[Path, set[str]] = {}
    for path in markdown:
        text = path.read_text(encoding="utf-8")
        unfinished = [
            line for line in text.splitlines()
            if any(marker in line for marker in ("TODO", "TBD", "FIXME"))
            and "starter" not in line.lower()
            and "known-wrong" not in line.lower()
        ]
        if unfinished:
            errors.append(f"미완성 표식: {path.relative_to(root)}")
        for raw in MARKDOWN_LINK.findall(text):
            try:
                resolved = resolve_local_link(path, raw, root)
            except ValidationError as exc:
                errors.append(str(exc))
                continue
            if resolved is None:
                continue
            target, fragment = resolved
            if not target.exists():
                errors.append(f"깨진 링크 {path.relative_to(root)} -> {raw}")
            elif fragment and target.is_file() and target.suffix.lower() == ".md":
                slug_cache.setdefault(target, heading_slugs(target))
                if fragment not in slug_cache[target]:
                    errors.append(f"없는 heading {path.relative_to(root)} -> {raw}")

    readme = (root / "README.md").read_text(encoding="utf-8")
    for number in EXPECTED_DOC_NUMBERS:
        if f"/{number:02d}-" not in readme:
            errors.append(f"README에서 {number:02d}번 문서 링크를 찾지 못했습니다.")
    if errors:
        raise ValidationError("\n".join(errors))
    return {
        "markdown": len(markdown),
        "documents": len(docs),
        "exercises": len(exercise_dirs),
        "fixtures": len(example_fixtures),
        "learning_units": len(LABS) + 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        counts = validate(args.root.resolve())
    except (OSError, UnicodeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("DOCS OK " + " ".join(f"{key}={value}" for key, value in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
