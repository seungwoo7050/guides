#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]


STAGES = {
    "01-transform-trace": ("identity-triangle", "software"),
    "02-sampling-and-color": ("corner-marker", "software"),
    "03-triangle-coverage": ("shared-edge-rectangle", "software"),
    "04-perspective-depth-blend": ("perspective-checker", "software"),
    "05-textured-lit-scene": ("textured-lit-scene", "software"),
    "06-gpu-first-frame": ("shared-textured-triangle-v1", "lifecycle-sim"),
    "07-frame-debugging": ("lifecycle-and-workloads", "lifecycle-sim"),
    "08-renderer-capstone": ("shared-textured-triangle-v1", "lifecycle-sim"),
}


def invoke_workspace_script(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script)], cwd=script.parents[1], text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, timeout=20,
    )


def invoke_renderer(
    executable: Path,
    stage: str,
    scene: str,
    backend: str,
    output: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(executable),
            "--stage", stage,
            "--scene", scene,
            "--backend", backend,
            "--out", str(output),
            "--frames", "3",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=30,
    )


def directory_snapshot(root: Path) -> dict[str, str]:
    if not root.exists() and not root.is_symlink():
        return {}
    result: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = f"link:{path.readlink()}"
        elif path.is_dir():
            result[relative] = "directory"
        elif path.is_file():
            result[relative] = f"file:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        else:
            result[relative] = "special"
    return result


def repository_source_snapshot() -> dict[str, str]:
    ignored_names = {
        ".git", ".guide", "build", "out", "workspace", "__pycache__",
    }
    result: dict[str, str] = {}
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if (
            any(part in ignored_names or part.startswith(".workspace.") for part in relative.parts)
            or (relative.parts and relative.parts[0].startswith("build-"))
            or path.suffix in {".pyc", ".log", ".spv", ".dxil", ".metallib"}
        ):
            continue
        key = relative.as_posix()
        if path.is_symlink():
            result[key] = f"link:{path.readlink()}"
        elif path.is_dir():
            result[key] = "directory"
        elif path.is_file():
            result[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def assert_rejected(
    result: subprocess.CompletedProcess[str],
    expected: set[int],
    label: str,
) -> None:
    if result.returncode not in expected:
        raise AssertionError(
            f"{label}: expected exit {sorted(expected)}, got {result.returncode}\n{result.stdout}"
        )


def test_workspace_creation() -> None:
    with tempfile.TemporaryDirectory(prefix="cg-workspace-tools-") as raw:
        root = Path(raw).resolve() / "repository"
        script = root / "scripts/new-workspace.sh"
        starter = root / "exercises/08-renderer-capstone/project/starter"
        script.parent.mkdir(parents=True)
        starter.parent.mkdir(parents=True)
        shutil.copy2(ROOT / "scripts/new-workspace.sh", script)
        shutil.copytree(ROOT / "exercises/08-renderer-capstone/project/starter", starter)
        script.chmod(0o755)

        first = invoke_workspace_script(script)
        workspace = starter.parent / "workspace"
        if first.returncode != 0 or not workspace.is_dir():
            raise AssertionError(f"workspace creation failed:\n{first.stdout}")
        sentinel = workspace / "learner-sentinel.txt"
        sentinel.write_text("preserve me\n", encoding="utf-8")

        second = invoke_workspace_script(script)
        if second.returncode == 0 or sentinel.read_text(encoding="utf-8") != "preserve me\n":
            raise AssertionError("existing learner workspace was overwritten")

        shutil.rmtree(workspace)
        outside = Path(raw) / "outside"
        outside.mkdir()
        workspace.symlink_to(outside, target_is_directory=True)
        linked = invoke_workspace_script(script)
        if linked.returncode == 0 or any(outside.iterdir()):
            raise AssertionError("workspace symlink was followed or accepted")


def test_renderer_output_safety(reference: Path, starter: Path) -> None:
    source_before = repository_source_snapshot()
    with tempfile.TemporaryDirectory(prefix="cg-renderer-safety-") as raw:
        root = Path(raw).resolve()

        existing = root / "pre-existing-output"
        existing.mkdir()
        sentinel = existing / "learner-sentinel.txt"
        sentinel.write_text("preserve exact output\n", encoding="utf-8")
        existing_before = directory_snapshot(existing)
        result = invoke_renderer(
            reference,
            "01-transform-trace",
            STAGES["01-transform-trace"][0],
            STAGES["01-transform-trace"][1],
            existing,
        )
        assert_rejected(result, {2}, "pre-existing exact output")
        if directory_snapshot(existing) != existing_before:
            raise AssertionError("renderer changed a pre-existing exact output directory")

        outside = root / "outside-target"
        outside.mkdir()
        outside_sentinel = outside / "outside-sentinel.txt"
        outside_sentinel.write_text("preserve symlink target\n", encoding="utf-8")
        outside_before = directory_snapshot(outside)
        linked_parent = root / "linked-parent"
        linked_parent.symlink_to(outside, target_is_directory=True)
        escaped_output = linked_parent / "new-output"
        result = invoke_renderer(
            reference,
            "01-transform-trace",
            STAGES["01-transform-trace"][0],
            STAGES["01-transform-trace"][1],
            escaped_output,
        )
        assert_rejected(result, {2}, "symbolic-link output ancestor")
        if escaped_output.exists() or escaped_output.is_symlink() or directory_snapshot(outside) != outside_before:
            raise AssertionError("renderer followed a symbolic-link output ancestor")

        unknown_root = root / "unknown-scenes"
        unknown_root.mkdir()
        for stage, (_, backend) in STAGES.items():
            output = unknown_root / stage
            result = invoke_renderer(reference, stage, "unknown-scene", backend, output)
            assert_rejected(result, {2}, f"{stage} unknown scene")
            if output.exists() or output.is_symlink():
                raise AssertionError(f"{stage}: unknown scene created an output path")

        starter_root = root / "starter-not-implemented"
        starter_root.mkdir()
        for stage, (scene, backend) in STAGES.items():
            output = starter_root / stage
            result = invoke_renderer(starter, stage, scene, backend, output)
            assert_rejected(result, {3}, f"{stage} starter not-implemented")
            if output.exists() or output.is_symlink():
                raise AssertionError(f"{stage}: starter created an output path")

    source_after = repository_source_snapshot()
    if source_after != source_before:
        changed = sorted(set(source_before) ^ set(source_after))
        changed.extend(
            key for key in source_before.keys() & source_after.keys()
            if source_before[key] != source_after[key]
        )
        raise AssertionError(f"renderer safety tests changed repository source: {sorted(set(changed))}")


def executable_path(value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file() or path.is_symlink():
        raise AssertionError(f"{label} renderer is missing or linked: {path}")
    return path.resolve(strict=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exercise workspace preservation and renderer output-boundary contracts."
    )
    parser.add_argument("--reference", required=True)
    parser.add_argument("--starter", required=True)
    args = parser.parse_args()

    reference = executable_path(args.reference, "reference")
    starter = executable_path(args.starter, "starter")
    test_workspace_creation()
    test_renderer_output_safety(reference, starter)

    print("WORKSPACE_TOOLS_TEST_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
