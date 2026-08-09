#!/usr/bin/env python3
"""Validate the embedded-systems guide layout and local Markdown links."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
DOC_PATTERN = re.compile(r"^(\d{2})-[a-z0-9-]+\.md$")

REQUIRED = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE.md",
    "LICENSES/MIT.txt",
    "Makefile",
    "prepare.sh",
    "verify.sh",
    "scripts/check_docs.py",
    "scripts/source_fingerprint.py",
    "scripts/test_verifier.py",
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
    "exercises/01-image-and-memory-audit/README.md",
    "exercises/02-interrupt-event-path/README.md",
    "exercises/03-sensor-driver-state-machine/README.md",
    "exercises/04-deadline-and-priority-review/README.md",
    "exercises/05-power-loss-persistence/README.md",
    "exercises/06-update-rollback-model/README.md",
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
    # Good enough for local guide anchors; GitHub's full algorithm is broader.
    text = re.sub(r"[`*_~]", "", text.strip().lower())
    text = re.sub(r"[^\w\-\s가-힣]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "-", text)
    return text


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
    target_text = unquote(target_text)
    target = (source.parent / target_text).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValidationError(f"{source.relative_to(root)}: 저장소 밖 링크 {raw}") from exc
    return target, unquote(fragment) if separator else None


def validate(root: Path) -> dict[str, int]:
    root = root.resolve()
    errors: list[str] = []
    for relative in REQUIRED:
        path = root / relative
        if not path.is_file():
            errors.append(f"필수 파일 누락: {relative}")
        elif path.stat().st_size == 0:
            errors.append(f"빈 필수 파일: {relative}")

    docs = sorted((root / "docs").glob("[0-9][0-9]-*/*.md"))
    numbers: list[int] = []
    for path in docs:
        match = DOC_PATTERN.match(path.name)
        if match:
            numbers.append(int(match.group(1)))
    if numbers != EXPECTED_DOC_NUMBERS:
        errors.append(f"개념 문서 번호가 01..20과 다릅니다: {numbers}")

    exercise_dirs = sorted(p for p in (root / "exercises").iterdir() if p.is_dir())
    exercise_numbers: list[int] = []
    for path in exercise_dirs:
        match = re.match(r"^(\d{2})-", path.name)
        if match:
            exercise_numbers.append(int(match.group(1)))
    if exercise_numbers != EXPECTED_EXERCISES:
        errors.append(f"실습 번호가 01..06과 다릅니다: {exercise_numbers}")
    for directory in exercise_dirs:
        readme = directory / "README.md"
        if not readme.is_file():
            continue
        text = readme.read_text(encoding="utf-8")
        headings = HEADING.findall(text)
        required_terms = ("문제", "결과물", "완료 조건")
        failure_term = any(term in text for term in ("실패", "잘못된 완료", "failure"))
        if len(text) < 1200 or len(headings) < 6 or not failure_term or any(term not in text for term in required_terms):
            errors.append(f"교육 계약이 부족한 실습: {readme.relative_to(root)}")

    capstone_files = [
        root / "capstone/field-sensor-node/README.md",
        root / "capstone/field-sensor-node/acceptance.md",
        root / "capstone/field-sensor-node/failure-matrix.md",
    ]
    for path in capstone_files:
        if path.is_file() and len(path.read_text(encoding="utf-8")) < 1000:
            errors.append(f"교육 계약이 부족한 capstone 문서: {path.relative_to(root)}")

    fixtures = sorted((root / "examples").glob("*/fixtures/*.json"))
    if len(fixtures) < 8:
        errors.append(f"상태 모델 fixture가 부족합니다: {len(fixtures)}")
    for path in fixtures:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"JSON 오류 {path.relative_to(root)}: {exc}")
            continue
        if not isinstance(data, dict) or not isinstance(data.get("events"), list) or not isinstance(data.get("expected"), dict):
            errors.append(f"fixture 계약 오류: {path.relative_to(root)}")

    markdown_files = sorted(root.rglob("*.md"))
    slug_cache: dict[Path, set[str]] = {}
    for path in markdown_files:
        text = path.read_text(encoding="utf-8")
        if "TODO" in text or "TBD" in text or "FIXME" in text:
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
                continue
            if fragment and target.is_file() and target.suffix.lower() == ".md":
                if target not in slug_cache:
                    slug_cache[target] = heading_slugs(target)
                if fragment not in slug_cache[target]:
                    errors.append(f"없는 heading {path.relative_to(root)} -> {raw}")

    readme = (root / "README.md").read_text(encoding="utf-8")
    for number in EXPECTED_DOC_NUMBERS:
        expected = f"/{number:02d}-"
        if expected not in readme:
            errors.append(f"README에서 {number:02d}번 문서 링크를 찾지 못했습니다.")

    if errors:
        raise ValidationError("\n".join(errors))
    return {
        "markdown": len(markdown_files),
        "documents": len(docs),
        "exercises": len(exercise_dirs),
        "fixtures": len(fixtures),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        counts = validate(root)
    except (OSError, UnicodeError, ValidationError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "DOCS OK "
        f"markdown={counts['markdown']} documents={counts['documents']} "
        f"exercises={counts['exercises']} fixtures={counts['fixtures']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
