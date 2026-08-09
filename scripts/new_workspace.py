#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXERCISES = {
    "01-scope-and-evidence": "template",
    "02-threat-model": "template",
    "03-vulnerability-validation": "template",
    "04-security-requirements": "template",
    "05-detection-engineering": "template",
    "06-incident-timeline": "template",
    "07-isolated-attack-path": "skeleton",
}
CAPSTONE = ROOT / "projects/synthetic-service-security-review"


def relative_label(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def refuse_symlink_chain(path: Path) -> None:
    try:
        relative = path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"저장소 밖 경로입니다: {path}") from exc
    current = ROOT
    if current.is_symlink():
        raise ValueError(f"symlink 경로는 사용할 수 없습니다: {current}")
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink 경로는 사용할 수 없습니다: {relative_label(current)}")


def validate_source_tree(source: Path) -> None:
    refuse_symlink_chain(source)
    if not source.is_dir():
        raise ValueError(f"workspace source가 없습니다: {relative_label(source)}")
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError(f"workspace source에 symlink가 있습니다: {relative_label(path)}")


def publish(source: Path, destination: Path) -> None:
    validate_source_tree(source)
    refuse_symlink_chain(destination.parent)
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"기존 workspace를 덮어쓰지 않습니다: {relative_label(destination)}")

    # mkdir(exist_ok=False)가 목적지를 원자적으로 예약하므로 동시에 실행해도
    # 기존 learner work를 대체하지 않는다. 실패할 때는 이 호출이 만든 경로만 지운다.
    destination.mkdir(mode=0o700)
    try:
        for child in source.iterdir():
            target = destination / child.name
            if child.is_dir():
                shutil.copytree(child, target, symlinks=False)
            else:
                shutil.copy2(child, target, follow_symlinks=False)
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def exercise_workspace(exercise_id: str) -> Path:
    source_name = EXERCISES.get(exercise_id)
    if source_name is None:
        raise ValueError(f"알 수 없는 exercise ID: {exercise_id}")
    root = ROOT / "exercises" / exercise_id
    source = root / source_name
    destination = root / "work"
    publish(source, destination)
    return destination


def capstone_workspace() -> Path:
    templates = CAPSTONE / "templates"
    lab_skeleton = ROOT / "exercises/07-isolated-attack-path/skeleton/ledgerlab_policy.py"
    destination = CAPSTONE / "work"
    if not templates.is_dir() or not lab_skeleton.is_file() or lab_skeleton.is_symlink():
        raise ValueError("Capstone template 또는 behavior lab skeleton이 없습니다")
    validate_source_tree(templates)
    refuse_symlink_chain(destination.parent)
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"기존 workspace를 덮어쓰지 않습니다: {relative_label(destination)}")
    destination.mkdir(mode=0o700)
    try:
        for child in templates.iterdir():
            target = destination / child.name
            if child.is_dir():
                shutil.copytree(child, target, symlinks=False)
            else:
                shutil.copy2(child, target, follow_symlinks=False)
        lab = destination / "behavior-lab"
        lab.mkdir()
        shutil.copy2(lab_skeleton, lab / "ledgerlab_policy.py", follow_symlinks=False)
    except BaseException:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="학습자 작업 디렉터리를 비파괴적으로 만듭니다.")
    subparsers = parser.add_subparsers(dest="kind", required=True)
    exercise = subparsers.add_parser("exercise")
    exercise.add_argument("exercise_id", choices=sorted(EXERCISES))
    subparsers.add_parser("capstone")
    args = parser.parse_args()

    try:
        destination = exercise_workspace(args.exercise_id) if args.kind == "exercise" else capstone_workspace()
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"WORKSPACE READY {destination.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
