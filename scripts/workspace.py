#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class TargetSpec:
    slug: str
    source_dir: str
    checker: str


TARGETS: dict[str, TargetSpec] = {
    "exercises/01-service-classification": TargetSpec(
        "01-service-classification", "template", "artifact"
    ),
    "exercises/02-iaas-failure-domains": TargetSpec(
        "02-iaas-failure-domains", "template", "artifact"
    ),
    "exercises/03-managed-service-contract": TargetSpec(
        "03-managed-service-contract", "template", "artifact"
    ),
    "exercises/04-faas-event-lifecycle": TargetSpec(
        "04-faas-event-lifecycle", "template", "artifact"
    ),
    "exercises/05-saas-tenant-isolation": TargetSpec(
        "05-saas-tenant-isolation", "template", "artifact"
    ),
    "exercises/06-cost-and-exit": TargetSpec(
        "06-cost-and-exit", "template", "artifact"
    ),
    "exercises/07-local-cloud-model": TargetSpec(
        "07-local-cloud-model", "skeleton", "cloud-model"
    ),
    "projects/multitenant-document-processing-saas": TargetSpec(
        "multitenant-document-processing-saas", "template", "artifact"
    ),
}


class WorkspaceError(RuntimeError):
    pass


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _assert_within(root: Path, candidate: Path, label: str) -> None:
    root_absolute = _absolute(root)
    candidate_absolute = _absolute(candidate)
    try:
        candidate_absolute.relative_to(root_absolute)
    except ValueError as exc:
        raise WorkspaceError(f"{label} 경로가 저장소 밖입니다: {candidate}") from exc

    try:
        resolved_root = root_absolute.resolve(strict=True)
        resolved_candidate = candidate_absolute.resolve(strict=False)
        resolved_candidate.relative_to(resolved_root)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise WorkspaceError(f"{label} 경로가 저장소 밖이거나 안전하지 않습니다: {candidate}") from exc


def _assert_no_symlink_chain(root: Path, candidate: Path, label: str) -> None:
    root_absolute = _absolute(root)
    candidate_absolute = _absolute(candidate)
    _assert_within(root_absolute, candidate_absolute, label)

    try:
        relative = candidate_absolute.relative_to(root_absolute)
    except ValueError as exc:
        raise WorkspaceError(f"{label} 경로가 저장소 밖입니다: {candidate}") from exc

    current = root_absolute
    paths = [current]
    for part in relative.parts:
        current = current / part
        paths.append(current)

    for path in paths:
        if path.is_symlink():
            raise WorkspaceError(f"{label} 경로에 symbolic link가 있습니다: {path}")
        if not path.exists():
            break


def _assert_regular_tree(root: Path, tree: Path, label: str) -> None:
    _assert_no_symlink_chain(root, tree, label)
    if not tree.is_dir():
        raise WorkspaceError(f"{label} 디렉터리가 없습니다: {tree}")

    for current_root, directory_names, file_names in os.walk(tree, followlinks=False):
        current = Path(current_root)
        _assert_within(root, current, label)
        for name in [*directory_names, *file_names]:
            entry = current / name
            try:
                mode = entry.lstat().st_mode
            except FileNotFoundError as exc:
                raise WorkspaceError(f"{label}에 dangling entry가 있습니다: {entry}") from exc
            if stat.S_ISLNK(mode):
                raise WorkspaceError(f"{label}에 symbolic link가 있습니다: {entry}")
            if not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise WorkspaceError(f"{label}에 지원하지 않는 파일 형식이 있습니다: {entry}")


def _spec_for(target: str) -> TargetSpec:
    if Path(target).is_absolute():
        raise WorkspaceError(f"절대 경로는 허용되지 않습니다: {target}")
    if ".." in Path(target).parts:
        raise WorkspaceError(f"상위 경로 이동은 허용되지 않습니다: {target}")
    spec = TARGETS.get(target)
    if spec is None:
        allowed = ", ".join(TARGETS)
        raise WorkspaceError(f"허용되지 않은 대상입니다: {target}\n허용 대상: {allowed}")
    return spec


def _paths(root: Path, target: str) -> tuple[TargetSpec, Path, Path, Path]:
    spec = _spec_for(target)
    root = _absolute(root)
    target_root = root / target
    source = target_root / spec.source_dir
    destination_parent = root / ".workspace"
    destination = destination_parent / spec.slug

    for path, label in (
        (target_root, "대상"),
        (source, "source"),
        (destination_parent, "workspace 상위"),
        (destination, "workspace destination"),
    ):
        _assert_no_symlink_chain(root, path, label)
    return spec, target_root, source, destination


def _remove_partial_destination(root: Path, destination: Path) -> None:
    """Remove only a regular partial workspace created by this invocation."""
    if not destination.exists() and not destination.is_symlink():
        return
    _assert_regular_tree(root, destination, "partial workspace")
    shutil.rmtree(destination)


def new_workspace(root: Path, target: str) -> Path:
    spec, _target_root, source, destination = _paths(root, target)
    root = _absolute(root)
    _assert_regular_tree(root, source, "source")

    if destination.exists() or destination.is_symlink():
        raise WorkspaceError(f"workspace가 이미 있습니다: {destination}")

    destination_parent = destination.parent
    if not destination_parent.exists():
        destination_parent.mkdir(mode=0o755)
    _assert_no_symlink_chain(root, destination_parent, "workspace 상위")

    try:
        shutil.copytree(source, destination, copy_function=shutil.copy2)
    except FileExistsError as exc:
        raise WorkspaceError(f"workspace가 이미 있습니다: {destination}") from exc
    except OSError as exc:
        try:
            _remove_partial_destination(root, destination)
        except (OSError, WorkspaceError) as cleanup_error:
            raise WorkspaceError(
                "workspace 복사에 실패했고 안전한 부분 정리도 완료하지 못했습니다: "
                f"{cleanup_error}"
            ) from exc
        raise WorkspaceError(f"workspace를 만들 수 없습니다: {exc}") from exc

    _assert_regular_tree(root, destination, "workspace destination")
    expected_name = "cloud_model.py" if spec.checker == "cloud-model" else None
    if expected_name is not None and not (destination / expected_name).is_file():
        raise WorkspaceError(f"local cloud model starter가 없습니다: {destination / expected_name}")
    return destination


def check_workspace(root: Path, target: str) -> int:
    spec, target_root, _source, destination = _paths(root, target)
    root = _absolute(root)
    _assert_regular_tree(root, destination, "workspace destination")

    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    if spec.checker == "artifact":
        contract = target_root / "contract.json"
        checker = root / "scripts" / "check_artifact.py"
        _assert_no_symlink_chain(root, contract, "contract")
        _assert_no_symlink_chain(root, checker, "artifact checker")
        if not contract.is_file():
            raise WorkspaceError(f"contract가 없습니다: {contract}")
        if not checker.is_file():
            raise WorkspaceError(f"artifact checker가 없습니다: {checker}")
        command = [sys.executable, str(checker), str(destination), str(contract)]
    else:
        implementation = destination / "cloud_model.py"
        checker = root / "scripts" / "verify_cloud_model.py"
        _assert_no_symlink_chain(root, implementation, "learner implementation")
        _assert_no_symlink_chain(root, checker, "cloud model checker")
        if not implementation.is_file():
            raise WorkspaceError(f"learner implementation이 없습니다: {implementation}")
        if not checker.is_file():
            raise WorkspaceError(f"cloud model checker가 없습니다: {checker}")
        command = [
            sys.executable,
            str(checker),
            "--implementation",
            str(implementation),
        ]

    completed = subprocess.run(command, cwd=root, env=environment, check=False)
    return completed.returncode


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="안전하게 guide learner workspace를 생성하거나 검사합니다."
    )
    parser.add_argument("action", choices=("new", "check"))
    parser.add_argument("target")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).parent.parent
    try:
        if args.action == "new":
            print(new_workspace(root, args.target))
            return 0
        return check_workspace(root, args.target)
    except WorkspaceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
