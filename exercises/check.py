#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import struct
import subprocess
import sys
import time
import uuid


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "exercises/08-renderer-capstone/project"
EXPECTED = PROJECT / "reference/expected"
FIXTURES = PROJECT / "fixtures"
sys.path.insert(0, str(ROOT / "tools"))
from ppm_diff import read_ppm as parse_ppm  # noqa: E402
STAGES = [
    "01-transform-trace",
    "02-sampling-and-color",
    "03-triangle-coverage",
    "04-perspective-depth-blend",
    "05-textured-lit-scene",
    "06-gpu-first-frame",
    "07-frame-debugging",
    "08-renderer-capstone",
]
SCENES = {
    "01-transform-trace": "identity-triangle",
    "02-sampling-and-color": "corner-marker",
    "03-triangle-coverage": "shared-edge-rectangle",
    "04-perspective-depth-blend": "perspective-checker",
    "05-textured-lit-scene": "textured-lit-scene",
    "06-gpu-first-frame": "shared-textured-triangle-v1",
    "07-frame-debugging": "lifecycle-and-workloads",
    "08-renderer-capstone": "shared-textured-triangle-v1",
}
GPU_STAGES = {"06-gpu-first-frame", "08-renderer-capstone"}
DIAGNOSTIC_CASES = (
    "mismatch_depth_clear_compare",
    "mismatch_vertex_layout",
    "overwrite_frame_slot",
    "readback_before_completion",
    "swap_srgb_and_data_format",
    "use_stale_resize_attachment",
)
VALIDATION_CAUGHT_CASES = {"mismatch_depth_clear_compare", "mismatch_vertex_layout"}
SEMANTIC_DIAGNOSTIC_CASES = set(DIAGNOSTIC_CASES) - VALIDATION_CAUGHT_CASES
CAPSTONE_SCENE_DIRECTORY = "shared-textured-triangle-v1"
LIFECYCLE_VIOLATIONS = {
    "overwrite_frame_slot": "write-before-slot-completion",
    "overwrite_uniform_slot_in_flight": "write-before-slot-completion",
    "use_stale_resize_attachment": "stale-resize-generation",
    "reuse_old_extent_after_resize": "stale-resize-generation",
    "readback_before_completion": "map-before-submission-completion",
}
EXPECTED_ACTUAL_LIFECYCLE_EVENTS = [
    "create-generation-1-64x64",
    "submit-1-slot-0-generation-1",
    "submit-2-slot-1-generation-1",
    "skip-zero-extent-no-target",
    "complete-1-before-slot-0-reuse",
    "create-generation-2-96x72",
    "submit-3-slot-0-generation-2",
    "complete-2-generation-1-last-use",
    "retire-generation-1-after-completion-2",
    "complete-3-generation-2",
    "map-generation-2-readback-after-completion-3",
    "retire-generation-2-after-completion-3",
]
CAPSTONE_MUTATION_METADATA = {
    "swap_matrix_order": ("structure", "software_and_gpu_consume_same_scene_contract"),
    "skip_clipping": ("coverage", "comparison_starts_with_structure_and_coverage"),
    "break_top_left_rule": ("coverage", "comparison_starts_with_structure_and_coverage"),
    "use_affine_uv": ("attribute", "comparison_starts_with_structure_and_coverage"),
    "skip_srgb_decode": ("linear-color", "comparison_starts_with_structure_and_coverage"),
    "reverse_depth_convention": ("depth", "comparison_starts_with_structure_and_coverage"),
    "mismatch_alpha_blend": ("linear-color", "comparison_starts_with_structure_and_coverage"),
    "mismatch_vertex_layout": ("structure", "software_and_gpu_consume_same_scene_contract"),
    "overwrite_frame_slot": ("lifecycle", "resource_reuse_is_completion_safe"),
    "use_stale_resize_attachment": ("lifecycle", "resize_and_reload_use_generations"),
}
EXPECTED_MANIFEST_FILES = {
    "bilinear-linear.ppm",
    "gpu-edge-policy.json",
    "lit-scene-final.ppm",
    "shared-edge-primitive-id.ppm",
    "transform-trace.json",
}

# Each contract artifact identifier is closed over concrete, parseable evidence.
# Existing stage-specific validators apply the semantic checks after this layer.
REQUIRED_ARTIFACT_SPECS: dict[
    str, dict[str, tuple[tuple[str, str, tuple[int, int] | None], ...]]
] = {
    "01-transform-trace": {
        name: ((name, "json", None),)
        for name in (
            "conventions.json", "case-identity.json", "case-nonuniform.json",
            "case-hierarchy.json", "case-near-clip.json", "rejected.json",
        )
    },
    "02-sampling-and-color": {
        "samples.json": (("samples.json", "json", None),),
        "address-grid.ppm": (("address-grid.ppm", "ppm", (6, 3)),),
        "bilinear-linear.ppm": (("bilinear-linear.ppm", "ppm", (1, 1)),),
        "bilinear-wrong-srgb.ppm": (("bilinear-wrong-srgb.ppm", "ppm", (1, 1)),),
        "alpha-straight.ppm": (("alpha-straight.ppm", "ppm", (1, 1)),),
        "alpha-premultiplied.ppm": (("alpha-premultiplied.ppm", "ppm", (1, 1)),),
        "report.json": (("report.json", "json", None),),
    },
    "03-triangle-coverage": {
        "coverage_images": (("case-rectangle.ppm", "ppm", (8, 8)),),
        "primitive_id_maps": (
            ("case-rectangle-primitive-id.json", "json", None),
            ("primitive-id.ppm", "ppm", (8, 8)),
        ),
        "setup-trace.json": (("setup-trace.json", "json", None),),
        "coverage-counts.json": (("coverage-counts.json", "json", None),),
        "mutation-report.json": (("mutation-report.json", "json", None),),
    },
    "04-perspective-depth-blend": {
        "perspective-correct.ppm": (("perspective-correct.ppm", "ppm", (8, 8)),),
        "affine-mutation.ppm": (("affine-mutation.ppm", "ppm", (8, 8)),),
        "depth-artifact": (("depth.json", "json", None),),
        "primitive-id.ppm": (("primitive-id.ppm", "ppm", (8, 8)),),
        "transparent-order-a.ppm": (("transparent-order-a.ppm", "ppm", (4, 4)),),
        "transparent-order-b.ppm": (("transparent-order-b.ppm", "ppm", (4, 4)),),
        "pixel-traces": (("pixel-traces/sample-3-3.json", "json", None),),
        "report.json": (("report.json", "json", None),),
    },
    "05-textured-lit-scene": {
        "final.ppm": (("final.ppm", "ppm", (16, 16)),),
        "base-color.ppm": (("base-color.ppm", "ppm", (16, 16)),),
        "normal-world.ppm": (("normal-world.ppm", "ppm", (16, 16)),),
        "ndotl.ppm": (("ndotl.ppm", "ppm", (16, 16)),),
        "mip-level.ppm": (("mip-level.ppm", "ppm", (16, 16)),),
        "object-id.ppm": (("object-id.ppm", "ppm", (16, 16)),),
        "asset-validation.json": (
            ("asset-validation.json", "json", None),
            ("seam-probe.ppm", "ppm", (2, 1)),
        ),
        "culling-lod.json": (("culling-lod.json", "json", None),),
        "frame.json": (
            ("frame.json", "json", None),
            ("depth.json", "json", None),
            ("statistics.json", "json", None),
            ("trace.json", "json", None),
            ("mutation-report.json", "json", None),
            ("primitive-id.ppm", "ppm", (16, 16)),
        ),
    },
    "06-gpu-first-frame": {
        "environment.json": (("environment.json", "json", None),),
        "shader-manifests": (("shader-manifests/triangle.json", "json", None),),
        "resources.json": (("resources.json", "json", None),),
        "pipelines.json": (("pipelines.json", "json", None),),
        "frame-trace.json": (("frame-trace.json", "json", None),),
        "screenshot": (("screenshot.ppm", "ppm", (64, 64)),),
        "resize-trace.json": (
            ("resize-trace.json", "json", None),
            ("resize-generation-2.ppm", "ppm", (96, 72)),
        ),
        "validation.log": (("validation.log", "kvlog", None),),
    },
    "07-frame-debugging": {
        "six_case_reports": tuple((f"{case}/report.md", "text", None) for case in DIAGNOSTIC_CASES),
        "environment_manifests": (
            (("environment.json", "json", None),)
            + tuple((f"{case}/environment.json", "json", None) for case in DIAGNOSTIC_CASES)
        ),
        "frame_traces": tuple((f"{case}/frame-trace.json", "json", None) for case in DIAGNOSTIC_CASES),
        "validation_logs": (
            (("validation.log", "kvlog", None),)
            + tuple((f"{case}/validation.log", "kvlog", None) for case in DIAGNOSTIC_CASES)
        ),
        "capture_metadata": tuple((f"{case}/capture-reference.txt", "text", None) for case in DIAGNOSTIC_CASES),
        "before_after_images": tuple(
            spec
            for case in DIAGNOSTIC_CASES
            for spec in (
                (f"{case}/before.ppm", "ppm", (64, 64)),
                (f"{case}/after.ppm", "ppm", (64, 64)),
            )
        ),
        "diff_reports": tuple((f"{case}/diff.json", "json", None) for case in DIAGNOSTIC_CASES),
        "timing_report": (("timing-report.json", "json", None),),
    },
    "08-renderer-capstone": {
        "conventions.json": (("conventions.json", "json", None),),
        "scene_fixtures": (("scene_fixtures/manifest.json", "json", None),),
        "software_artifacts": tuple(
            (f"software_artifacts/{CAPSTONE_SCENE_DIRECTORY}/{name}", kind, extent)
            for name, kind, extent in (
                ("environment.json", "json", None),
                ("depth.json", "json", None),
                ("primitive-id.json", "json", None),
                ("trace.json", "json", None),
                ("statistics.json", "json", None),
                ("color-linear.ppm", "ppm", (64, 64)),
                ("color-srgb.ppm", "ppm", (64, 64)),
                ("primitive-id.ppm", "ppm", (64, 64)),
            )
        ),
        "gpu_artifacts": tuple(
            (f"gpu_artifacts/{CAPSTONE_SCENE_DIRECTORY}/{name}", kind, extent)
            for name, kind, extent in (
                ("environment.json", "json", None),
                ("depth.json", "json", None),
                ("primitive-id.json", "json", None),
                ("trace.json", "json", None),
                ("statistics.json", "json", None),
                ("lifecycle.json", "json", None),
                ("timing-report.json", "json", None),
                ("shader-manifest.json", "json", None),
                ("pipeline.json", "json", None),
                ("resources.json", "json", None),
                ("frame-trace.json", "json", None),
                ("validation.log", "kvlog", None),
                ("color-linear.ppm", "ppm", (64, 64)),
                ("color-srgb.ppm", "ppm", (64, 64)),
                ("primitive-id.ppm", "ppm", (64, 64)),
                ("resize-generation-2.ppm", "ppm", (96, 72)),
            )
        ),
        "comparison_reports": tuple(
            (f"comparison_reports/{name}", kind, extent)
            for name, kind, extent in (
                ("01-structure.json", "json", None),
                ("02-coverage.json", "json", None),
                ("03-depth.json", "json", None),
                ("04-attribute.json", "json", None),
                ("05-linear-color.json", "json", None),
                ("06-srgb.json", "json", None),
                ("edge-mask.json", "json", None),
                ("edge-mask.ppm", "ppm", (64, 64)),
                ("known-bad-mask-probe.json", "json", None),
                ("known-bad-interior.ppm", "ppm", (64, 64)),
                ("summary.json", "json", None),
            )
        ),
        "correctness.md": (("correctness.md", "text", None),),
        "debugging.md": (("debugging.md", "text", None),),
        "performance.md": (("performance.md", "text", None),),
    },
}


class CheckFailure(RuntimeError):
    pass


def read_ppm(path: Path):
    if not path.is_file() or path.is_symlink():
        raise CheckFailure(f"required PPM evidence is missing or linked: {path}")
    return parse_ppm(path)


class CommandFailure(CheckFailure):
    def __init__(self, result: subprocess.CompletedProcess[str], command: list[str], expected: set[int]):
        self.returncode = result.returncode
        self.output = result.stdout
        super().__init__(
            f"command exit={result.returncode}, expected={sorted(expected)}\n"
            f"$ {' '.join(command)}\n{result.stdout}"
        )


def reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise CheckFailure(f"duplicate JSON key: {key}")
        payload[key] = value
    return payload


def reject_nonfinite_json_constant(value: str) -> object:
    raise CheckFailure(f"non-finite JSON constant: {value}")


def load_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise CheckFailure(f"required evidence is missing: {path.name}")
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
        parse_constant=reject_nonfinite_json_constant,
    )
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise CheckFailure(f"invalid evidence schema: {path.name}")
    return payload


def fixture_scene_hash() -> str:
    """Rebuild the public SceneSnapshot hash from JSON, independently of C++."""
    scene = load_json(FIXTURES / "scene-v1.json")
    vertices = scene.get("vertices")
    indices = scene.get("indices")
    provenance = scene.get("provenance")
    if (
        scene.get("id") != "shared-textured-triangle-v1"
        or not isinstance(vertices, list)
        or len(vertices) != 3
        or not isinstance(indices, list)
        or indices != [0, 1, 2]
        or not isinstance(provenance, dict)
        or provenance.get("external_asset") is not False
        or provenance.get("license") != "MIT"
    ):
        raise CheckFailure("scene-v1 fixture identity, topology, or provenance is invalid")
    parts = [f"{scene['schema_version']}:{scene['id']}:"]
    for vertex in vertices:
        if not isinstance(vertex, dict):
            raise CheckFailure("scene-v1 vertex must be an object")
        values: list[object] = []
        for field, count in (("position", 3), ("color_linear", 4), ("uv", 2), ("normal", 3)):
            item = vertex.get(field)
            if not isinstance(item, list) or len(item) != count:
                raise CheckFailure(f"scene-v1 vertex {field} has the wrong shape")
            values.extend(item)
        for value in values:
            bits = struct.unpack("<I", struct.pack("<f", float(value)))[0]
            parts.append(f"{bits:08x}:")
    parts.extend(f"{int(index)}:" for index in indices)
    return fnv1a64("".join(parts).encode("ascii"))


def capstone_edge_mask() -> tuple[bytes, dict[str, object]]:
    """Construct the reviewed mask from fixture geometry without C++ helpers."""
    policy = load_json(EXPECTED / "gpu-edge-policy.json")
    scene = load_json(FIXTURES / "scene-v1.json")
    extent = policy.get("extent")
    vertices = scene.get("vertices")
    if extent != [64, 64] or not isinstance(vertices, list) or len(vertices) != 3:
        raise CheckFailure("GPU edge policy extent or scene vertices are invalid")
    width, height = (int(value) for value in extent)
    radius = float(policy.get("radius_pixels", -1.0))

    def f32(value: object) -> float:
        return struct.unpack("<f", struct.pack("<f", float(value)))[0]

    screen: list[tuple[float, float]] = []
    for vertex in vertices:
        position = vertex.get("position") if isinstance(vertex, dict) else None
        if not isinstance(position, list) or len(position) != 3:
            raise CheckFailure("GPU edge policy scene position is invalid")
        screen.append(((f32(position[0]) * 0.5 + 0.5) * width,
                       (-f32(position[1]) * 0.5 + 0.5) * height))

    def segment_distance(x: float, y: float, start: tuple[float, float], end: tuple[float, float]) -> float:
        sx, sy = start
        dx, dy = end[0] - sx, end[1] - sy
        length_squared = dx * dx + dy * dy
        projection = 0.0 if length_squared == 0.0 else max(
            0.0, min(1.0, ((x - sx) * dx + (y - sy) * dy) / length_squared)
        )
        return math.hypot(x - (sx + projection * dx), y - (sy + projection * dy))

    mask = bytes(
        int(min(
            segment_distance(x + 0.5, y + 0.5, screen[0], screen[1]),
            segment_distance(x + 0.5, y + 0.5, screen[1], screen[2]),
            segment_distance(x + 0.5, y + 0.5, screen[2], screen[0]),
        ) <= radius)
        for y in range(height)
        for x in range(width)
    )
    if (
        sum(mask) != policy.get("population")
        or fnv1a64(mask) != policy.get("mask_hash_fnv1a64")
        or sum(mask) / len(mask) > float(policy.get("maximum_fraction", 0.0))
    ):
        raise CheckFailure("reviewed GPU edge policy does not match independent geometry")
    return mask, policy


def validate_expected_manifest() -> None:
    manifest = load_json(EXPECTED / "manifest.json")
    required_manifest_fields = {
        "schema_version", "provenance", "license", "review_policy", "files",
        "gpu_comparison_policy",
    }
    if set(manifest) != required_manifest_fields:
        raise CheckFailure(
            "reference expected manifest fields are not closed: "
            f"{sorted(set(manifest) ^ required_manifest_fields)}"
        )
    if (
        manifest.get("provenance") != "repository-generated-reference"
        or manifest.get("license") != "MIT"
        or manifest.get("review_policy")
        != "Update only with the first changed pipeline stage and mutation-regression evidence."
        or manifest.get("gpu_comparison_policy") != {
            "golden_kind": "CPU-derived expected behavior",
            "backend_output_tracked": False,
            "tolerance_may_widen_after_failure": False,
        }
    ):
        raise CheckFailure("reference expected manifest provenance, license, or review policy is invalid")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != EXPECTED_MANIFEST_FILES:
        raise CheckFailure(
            "reference expected manifest file set mismatch: "
            f"declared={sorted(files) if isinstance(files, dict) else files} "
            f"required={sorted(EXPECTED_MANIFEST_FILES)}"
        )
    allowed_directory_entries = EXPECTED_MANIFEST_FILES | {"manifest.json", "README.md"}
    actual_directory_entries = {path.name for path in EXPECTED.iterdir()}
    if actual_directory_entries != allowed_directory_entries:
        raise CheckFailure(
            "reference expected directory is not closed: "
            f"extra={sorted(actual_directory_entries - allowed_directory_entries)} "
            f"missing={sorted(allowed_directory_entries - actual_directory_entries)}"
        )
    for name, expected_hash in files.items():
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(character not in "0123456789abcdef" for character in expected_hash)
        ):
            raise CheckFailure("reference expected manifest entry is invalid")
        path = EXPECTED / name
        if (
            not path.is_file()
            or path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash
        ):
            raise CheckFailure(f"tracked reference artifact hash mismatch: {name}")
    for name in ("manifest.json", "README.md"):
        if (EXPECTED / name).is_symlink() or not (EXPECTED / name).is_file():
            raise CheckFailure(f"reference expected metadata is missing or linked: {name}")
    for name in ("scene-v1.json", "marker-texture.json", "invalid-assets.json", "resource-events.json"):
        fixture = load_json(FIXTURES / name)
        provenance = fixture.get("provenance")
        if not isinstance(provenance, dict) or provenance != {
            "kind": "repository-generated-fixture",
            "external_asset": False,
            "license": "MIT",
        }:
            raise CheckFailure(f"fixture provenance is missing or inconsistent: {name}")
    capstone_edge_mask()


def close_sequence(actual: object, expected: list[float], *, tolerance: float = 1.0e-8) -> bool:
    return (
        isinstance(actual, list)
        and len(actual) == len(expected)
        and all(
            type(value) in (int, float)
            and math.isfinite(float(value))
            and math.isclose(float(value), target, rel_tol=0.0, abs_tol=tolerance)
            for value, target in zip(actual, expected, strict=True)
        )
    )


def exact_ppm_matches(expected: Path, actual: Path) -> bool:
    reference = read_ppm(expected)
    candidate = read_ppm(actual)
    return (
        reference.width == candidate.width
        and reference.height == candidate.height
        and reference.pixels == candidate.pixels
    )


def load_key_value_log(path: Path) -> dict[str, str]:
    if not path.is_file() or path.is_symlink():
        raise CheckFailure(f"required key-value log is missing or linked: {path}")
    values: dict[str, str] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or "=" not in line:
            raise CheckFailure(f"{path.name}:{line_number}: expected non-empty key=value record")
        key, value = line.split("=", 1)
        if not key or not value or key in values:
            raise CheckFailure(f"{path.name}:{line_number}: empty or duplicate key-value record")
        values[key] = value
    if not values:
        raise CheckFailure(f"required key-value log is empty: {path}")
    return values


def validate_required_artifacts(stage: str, output: Path) -> None:
    if not output.is_dir() or output.is_symlink():
        raise CheckFailure(f"{stage}: artifact root is missing or is a symbolic link")
    payload = contract(stage)
    declared = payload.get("required_artifacts")
    specs = REQUIRED_ARTIFACT_SPECS.get(stage)
    if not isinstance(declared, list) or any(not isinstance(item, str) for item in declared):
        raise CheckFailure(f"{stage}: required_artifacts must be a string array")
    if specs is None or tuple(declared) != tuple(specs):
        mapped = tuple(specs) if specs is not None else ()
        raise CheckFailure(
            f"{stage}: required artifact mapping mismatch declared={tuple(declared)} mapped={mapped}"
        )

    root = output.resolve(strict=True)
    checked_paths: set[str] = set()
    for artifact_id, entries in specs.items():
        if not entries:
            raise CheckFailure(f"{stage}/{artifact_id}: artifact mapping is empty")
        for relative, kind, expected_extent in entries:
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts or relative in checked_paths:
                raise CheckFailure(f"{stage}/{artifact_id}: unsafe or duplicate artifact path {relative}")
            checked_paths.add(relative)
            path = output / relative_path
            current = path
            while current != output:
                if current.is_symlink():
                    raise CheckFailure(f"{stage}/{artifact_id}: symbolic-link artifact {relative}")
                current = current.parent
            try:
                path.resolve(strict=True).relative_to(root)
            except (FileNotFoundError, ValueError) as error:
                raise CheckFailure(f"{stage}/{artifact_id}: missing or escaped artifact {relative}") from error
            if not path.is_file():
                raise CheckFailure(f"{stage}/{artifact_id}: artifact is not a regular file {relative}")
            if kind == "json":
                load_json(path)
            elif kind == "ppm":
                image = read_ppm(path)
                if expected_extent is None or (image.width, image.height) != expected_extent:
                    raise CheckFailure(
                        f"{stage}/{artifact_id}: {relative} extent "
                        f"{(image.width, image.height)} != {expected_extent}"
                    )
            elif kind == "text":
                text = path.read_text(encoding="utf-8").strip()
                if len(text) < 16:
                    raise CheckFailure(f"{stage}/{artifact_id}: text artifact is empty or shallow {relative}")
            elif kind == "kvlog":
                load_key_value_log(path)
            else:
                raise CheckFailure(f"{stage}/{artifact_id}: unknown artifact parser {kind}")


def validate_transform_evidence(output: Path) -> None:
    conventions = load_json(output / "conventions.json")
    identity = load_json(output / "case-identity.json")
    nonuniform = load_json(output / "case-nonuniform.json")
    hierarchy = load_json(output / "case-hierarchy.json")
    clipping = load_json(output / "case-near-clip.json")
    rejected = load_json(output / "rejected.json")
    golden = load_json(EXPECTED / "transform-trace.json")
    tolerance = float(golden.get("absolute_tolerance", 1.0e-8))
    composition = identity.get("composition_probe")
    camera = identity.get("camera")
    camera_valid = False
    if isinstance(camera, dict):
        eye = camera.get("eye")
        target = camera.get("target")
        up_input = camera.get("up_input")
        if all(
            isinstance(value, list) and len(value) == 3
            and all(type(component) in (int, float) and math.isfinite(float(component)) for component in value)
            for value in (eye, target, up_input)
        ):
            eye_f = [float(value) for value in eye]
            target_f = [float(value) for value in target]
            up_f = [float(value) for value in up_input]

            def subtract(left: list[float], right: list[float]) -> list[float]:
                return [a - b for a, b in zip(left, right, strict=True)]

            def dot(left: list[float], right: list[float]) -> float:
                return sum(a * b for a, b in zip(left, right, strict=True))

            def cross(left: list[float], right: list[float]) -> list[float]:
                return [
                    left[1] * right[2] - left[2] * right[1],
                    left[2] * right[0] - left[0] * right[2],
                    left[0] * right[1] - left[1] * right[0],
                ]

            def normalize(value: list[float]) -> list[float] | None:
                length = math.sqrt(dot(value, value))
                return None if not math.isfinite(length) or length <= 1.0e-12 else [item / length for item in value]

            forward = normalize(subtract(target_f, eye_f))
            right = normalize(cross(up_f, forward)) if forward is not None else None
            camera_up = cross(forward, right) if forward is not None and right is not None else None
            distance = math.dist(eye_f, target_f)
            camera_valid = (
                forward is not None and right is not None and camera_up is not None
                and any(abs(value) > 1.0e-6 for value in eye_f)
                and distance > 1.0
                and close_sequence(camera.get("forward"), forward, tolerance=tolerance)
                and close_sequence(camera.get("right"), right, tolerance=tolerance)
                and close_sequence(camera.get("camera_up"), camera_up, tolerance=tolerance)
                and close_sequence(camera.get("target_view"), [0.0, 0.0, distance, 1.0], tolerance=1.0e-8)
                and all(math.isclose(dot(axis, axis), 1.0, abs_tol=1.0e-8) for axis in (forward, right, camera_up))
                and all(math.isclose(dot(left, right_axis), 0.0, abs_tol=1.0e-8) for left, right_axis in (
                    (forward, right), (forward, camera_up), (right, camera_up)
                ))
            )
    plane_ids = ["left:x+w", "right:w-x", "bottom:y+w", "top:w-y", "near:z", "far:w-z"]
    clip_vertices = clipping.get("output_clip_vertices")
    clip_attributes = clipping.get("output_attributes")
    clip_values_valid = (
        isinstance(clip_vertices, list)
        and len(clip_vertices) == 4
        and all(
            isinstance(vertex, list) and len(vertex) == 4
            and all(type(value) in (int, float) and math.isfinite(float(value)) for value in vertex)
            and float(vertex[3]) > 0.0
            and -float(vertex[3]) - tolerance <= float(vertex[0]) <= float(vertex[3]) + tolerance
            and -float(vertex[3]) - tolerance <= float(vertex[1]) <= float(vertex[3]) + tolerance
            and -tolerance <= float(vertex[2]) <= float(vertex[3]) + tolerance
            for vertex in clip_vertices
        )
        and isinstance(clip_attributes, list)
        and len(clip_attributes) == len(clip_vertices)
        and all(
            isinstance(item, dict) and set(item) == {"uv", "color"}
            and isinstance(item["uv"], list) and len(item["uv"]) == 2
            and isinstance(item["color"], list) and len(item["color"]) == 3
            and all(
                type(value) in (int, float) and math.isfinite(float(value))
                for value in item["uv"] + item["color"]
            )
            for item in clip_attributes
        )
    )
    checks = {
        "tracked conventions": conventions.get("composition") == golden["conventions"]["composition"]
        and conventions.get("handedness") == golden["conventions"]["handedness"]
        and conventions.get("ndc_depth") == golden["conventions"]["ndc_depth"]
        and conventions.get("viewport_origin") == golden["conventions"]["viewport_origin"],
        "identity world position": close_sequence(
            identity.get("world"), golden["world"], tolerance=tolerance
        ),
        "P*V*M clip coordinate": close_sequence(
            identity.get("clip"), golden["clip"], tolerance=tolerance
        ),
        "perspective divide": close_sequence(
            identity.get("ndc"), golden["ndc"], tolerance=tolerance
        ),
        "top-left viewport mapping": close_sequence(
            identity.get("viewport"), golden["viewport"], tolerance=tolerance
        ),
        "direction w=0": close_sequence(identity.get("translated_direction"), [1.0, 2.0, 3.0, 0.0]),
        "nontrivial left-handed camera": camera_valid,
        "composition countercheck": isinstance(composition, dict)
        and close_sequence(composition.get("actual_clip"), [1.5, 0.0, 2.25, 3.0])
        and composition.get("actual_clip") == composition.get("expected_clip"),
        "normal inverse-transpose": nonuniform.get("normal_transform") == "inverse-transpose"
        and isinstance(nonuniform.get("tangent_normal_dot"), (int, float))
        and abs(float(nonuniform["tangent_normal_dot"])) <= 1.0e-8,
        "parent-child order": close_sequence(hierarchy.get("world"), [10.0, 3.0, 0.0, 1.0])
        and close_sequence(hierarchy.get("reversed_order_counterexample"), [12.0, 1.0, 0.0, 1.0]),
        "homogeneous near clipping": clipping.get("output_vertex_count")
        == golden["near_clip"]["output_vertex_count"]
        and clipping.get("generated_intersection_count")
        == golden["near_clip"]["generated_intersection_count"]
        and clipping.get("all_output_vertices_inside") is True,
        "six-plane clipping and varying preservation": clip_values_valid
        and clipping.get("planes_applied") == plane_ids
        and clipping.get("plane_vertex_counts") == {
            "left:x+w": 3, "right:w-x": 3, "bottom:y+w": 3,
            "top:w-y": 3, "near:z": 4, "far:w-z": 4,
        }
        and clipping.get("six_plane_probe_output_counts") == {identifier: 4 for identifier in plane_ids}
        and clipping.get("all_attributes_finite") is True,
        "invalid transform rejection": {
            item.get("id")
            for item in rejected.get("rejections", [])
            if isinstance(item, dict) and item.get("rejected") is True
        }
        == {"camera-up-parallel-forward", "zero-scale-normal-matrix"},
    }
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        raise CheckFailure(f"01-transform-trace: independent evidence checks failed: {failed}")


def validate_sampling_evidence(output: Path) -> None:
    samples = load_json(output / "samples.json")
    report = load_json(output / "report.json")
    address_image = read_ppm(output / "address-grid.ppm")
    bilinear_image = read_ppm(output / "bilinear-linear.ppm")
    wrong_bilinear_image = read_ppm(output / "bilinear-wrong-srgb.ppm")
    alpha_straight_image = read_ppm(output / "alpha-straight.ppm")
    alpha_premultiplied_image = read_ppm(output / "alpha-premultiplied.ppm")
    cases = samples.get("nearest_cases")
    case_map = {
        (tuple(item.get("uv", [])), item.get("mode")): item.get("index")
        for item in cases if isinstance(item, dict)
    } if isinstance(cases, list) else {}
    bilinear = samples.get("bilinear_midpoint")
    encoding = samples.get("same_byte_color_vs_data")
    checks = {
        "clamp at upper boundary": case_map.get(((1.0, 1.0), "clamp")) == [1, 1],
        "negative repeat": case_map.get(((-0.25, 0.25), "repeat")) == [1, 0],
        "upper repeat": case_map.get(((1.25, 0.25), "repeat")) == [0, 0],
        "bilinear in linear space": isinstance(bilinear, dict)
        and math.isclose(float(bilinear.get("linear", -1.0)), 0.5, rel_tol=0.0, abs_tol=1.0e-9)
        and math.isclose(float(bilinear.get("encoded", -1.0)), 0.735356983052, rel_tol=0.0, abs_tol=1.0e-9),
        "color/data encoding split": isinstance(encoding, dict)
        and math.isclose(float(encoding.get("color_linear", -1.0)), 0.214041140482, rel_tol=0.0, abs_tol=1.0e-9)
        and math.isclose(float(encoding.get("data_linear", -1.0)), 0.5, rel_tol=0.0, abs_tol=1.0e-9),
        "encoded average distinction": report.get("linear_average_srgb_byte") == 188
        and report.get("encoded_byte_average") == 128,
        "alpha equations": close_sequence(report.get("straight_result"), [0.5, 0.0, 0.5, 1.0])
        and report.get("straight_result") == report.get("premultiplied_result"),
        "odd mip chain": report.get("mip_extents") == [[3, 5], [2, 3], [1, 2], [1, 1]],
        "address image is observable": len({
            address_image.pixels[index:index + 3]
            for index in range(0, len(address_image.pixels), 3)
        }) >= 2,
        "wrong encoded interpolation differs": bilinear_image.pixels != wrong_bilinear_image.pixels,
        "alpha representations produce the same image":
        alpha_straight_image.pixels == alpha_premultiplied_image.pixels,
        "tracked bilinear golden": exact_ppm_matches(
            EXPECTED / "bilinear-linear.ppm", output / "bilinear-linear.ppm"
        ),
    }
    required_ppm = {
        "address-grid.ppm", "bilinear-linear.ppm", "bilinear-wrong-srgb.ppm",
        "alpha-straight.ppm", "alpha-premultiplied.ppm",
        "mip-level-0.ppm", "mip-level-1.ppm", "mip-level-2.ppm", "mip-level-3.ppm",
    }
    missing_ppm = sorted(name for name in required_ppm if not (output / name).is_file())
    failed = [label for label, passed in checks.items() if not passed]
    if failed or missing_ppm:
        raise CheckFailure(
            f"02-sampling-and-color: independent evidence checks failed={failed} missing_ppm={missing_ppm}"
        )


def validate_coverage_evidence(output: Path) -> None:
    counts = load_json(output / "coverage-counts.json")
    ownership = load_json(output / "case-rectangle-primitive-id.json")
    mutation_report = load_json(output / "mutation-report.json")
    trace = load_json(output / "setup-trace.json")
    coverage_image = read_ppm(output / "case-rectangle.ppm")
    offscreen = counts.get("offscreen_boundary")
    reversed_coverage = counts.get("reversed_coverage")
    degenerate_setup = counts.get("degenerate_setup")
    clipped_primitive = counts.get("clipped_primitive")
    trace_clipped = trace.get("clipped_primitive")
    owners = ownership.get("owners")
    flat_owners = [value for row in owners for value in row] if (
        isinstance(owners, list)
        and len(owners) == 8
        and all(isinstance(row, list) and len(row) == 8 for row in owners)
    ) else []
    checks = {
        "8x8 ownership extent": len(flat_owners) == 64
        and ownership.get("width") == 8 and ownership.get("height") == 8,
        "exclusive shared edge": flat_owners.count(1) == 21
        and flat_owners.count(2) == 15 and flat_owners.count(0) == 28,
        "coverage accounting": counts.get("rectangle_expected_samples") == 36
        and counts.get("primitive_1_samples") == 21
        and counts.get("primitive_2_samples") == 15
        and counts.get("gap_samples") == 0 and counts.get("overlap_samples") == 0,
        "degenerate rejection": counts.get("degenerate_writes") == 0,
        "offscreen bound calculation": isinstance(offscreen, dict)
        and offscreen == {
            "tested_samples": 0, "written_samples": 0, "expected_tested_samples": 0,
        },
        "winding-normalized coverage": isinstance(reversed_coverage, dict)
        and type(reversed_coverage.get("forward_samples")) is int
        and reversed_coverage.get("forward_samples") == reversed_coverage.get("reversed_samples")
        and reversed_coverage["forward_samples"] > 0
        and reversed_coverage.get("winding_rejections") == 0,
        "finite degenerate setup guard": degenerate_setup == {
            "guarded": True, "nonfinite_detected": False,
        },
        "clipped primitive is triangulated after clipping": isinstance(clipped_primitive, dict)
        and clipped_primitive.get("input_vertex_count") == 3
        and clipped_primitive.get("computed_output_vertex_count") == 4
        and clipped_primitive.get("selected_output_vertex_count") == 4
        and clipped_primitive.get("child_triangle_count") == 2
        and type(clipped_primitive.get("covered_samples")) is int
        and clipped_primitive["covered_samples"] > 0
        and clipped_primitive.get("selected_policy") == "six-plane"
        and clipped_primitive.get("all_inside") is True
        and isinstance(trace_clipped, dict)
        and trace_clipped == {
            "selected_policy": "six-plane",
            "computed_output_vertex_count": 4,
            "selected_output_vertex_count": 4,
        },
        "top-left owner trace": isinstance(trace.get("shared_edge"), dict)
        and trace["shared_edge"].get("rule") == "top-left"
        and trace["shared_edge"].get("owner") in {1, 2},
        "baseline mutation report": mutation_report.get("mutation") is None
        and mutation_report.get("recognized") is True
        and mutation_report.get("rejected") is False
        and mutation_report.get("first_difference") == "none"
        and trace.get("first_difference") == "none",
        "coverage image is observable": len({
            coverage_image.pixels[index:index + 3]
            for index in range(0, len(coverage_image.pixels), 3)
        }) == 3,
        "tracked primitive-id golden": exact_ppm_matches(
            EXPECTED / "shared-edge-primitive-id.ppm", output / "primitive-id.ppm"
        ),
    }
    required_images = {"case-rectangle.ppm", "primitive-id.ppm"}
    missing_images = sorted(name for name in required_images if not (output / name).is_file())
    failed = [label for label, passed in checks.items() if not passed]
    if failed or missing_images:
        raise CheckFailure(
            f"03-triangle-coverage: independent evidence checks failed={failed} missing_ppm={missing_images}"
        )


def validate_perspective_evidence(output: Path) -> None:
    report = load_json(output / "report.json")
    depth = load_json(output / "depth.json")
    pixel_trace = load_json(output / "pixel-traces" / "sample-3-3.json")
    diagonal = report.get("diagonal_uv_delta")
    order_a = depth.get("order_a")
    order_b = depth.get("order_b")
    perspective_uv = pixel_trace.get("perspective_uv")
    affine_uv = pixel_trace.get("affine_uv")
    lambdas = pixel_trace.get("lambda")
    vertex_inverse_w = pixel_trace.get("vertex_inverse_w")
    expected_denominator = (
        sum(float(weight) * float(inverse_w) for weight, inverse_w in zip(
            lambdas, vertex_inverse_w, strict=True
        ))
        if isinstance(lambdas, list) and len(lambdas) == 3
        and isinstance(vertex_inverse_w, list) and len(vertex_inverse_w) == 3
        and all(type(value) in (int, float) for value in lambdas + vertex_inverse_w)
        else math.nan
    )
    expected_affine_ndc_depth = (
        sum(float(weight) * depth_value for weight, depth_value in zip(
            lambdas, [0.25, 0.50, 0.75], strict=True
        ))
        if isinstance(lambdas, list) and len(lambdas) == 3
        and all(type(value) in (int, float) for value in lambdas)
        else math.nan
    )
    perspective_image = read_ppm(output / "perspective-correct.ppm")
    affine_image = read_ppm(output / "affine-mutation.ppm")
    primitive_image = read_ppm(output / "primitive-id.ppm")
    transparent_a = read_ppm(output / "transparent-order-a.ppm")
    transparent_b = read_ppm(output / "transparent-order-b.ppm")
    checks = {
        "perspective differs from affine": isinstance(report.get("perspective_vs_affine_changed_pixels"), int)
        and report["perspective_vs_affine_changed_pixels"] > 0,
        "quad diagonal continuity": close_sequence(diagonal, [0.0, 0.0], tolerance=1.0e-6),
        "opaque order invariance": report.get("opaque_order_invariant") is True
        and isinstance(order_a, dict) and isinstance(order_b, dict)
        and order_a == order_b and order_a.get("owner") == 1,
        "zero-to-one depth": depth.get("clear") == 1.0 and depth.get("compare") == "less"
        and report.get("selected_depth_compare") == "less"
        and 0.0 <= float(order_a.get("depth", -1.0)) <= 1.0,
        "alpha representations agree": isinstance(report.get("straight_premultiplied_max_delta"), (int, float))
        and float(report["straight_premultiplied_max_delta"]) <= 1.0e-8,
        "linear blend is observable": isinstance(report.get("linear_vs_encoded_blend_delta"), (int, float))
        and float(report["linear_vs_encoded_blend_delta"]) > 0.1,
        "pixel trace explains perspective and depth": pixel_trace.get("pixel") == [3, 3]
        and close_sequence(pixel_trace.get("lambda"), [0.583333, 0.0, 0.416667], tolerance=1.0e-6)
        and isinstance(pixel_trace.get("inverse_w_denominator"), (int, float))
        and math.isfinite(float(pixel_trace["inverse_w_denominator"]))
        and close_sequence(perspective_uv, [0.263158, 0.263158], tolerance=1.0e-6)
        and close_sequence(affine_uv, [0.416667, 0.416667], tolerance=1.0e-6)
        and perspective_uv != affine_uv
        and isinstance(pixel_trace.get("incoming_depth"), (int, float))
        and 0.0 <= float(pixel_trace["incoming_depth"]) <= 1.0
        and pixel_trace.get("depth_test") is True,
        "reciprocal-w and NDC-depth oracles": close_sequence(
            vertex_inverse_w, [1.0, 0.25, 0.5], tolerance=1.0e-8
        )
        and pixel_trace.get("denominator_finite_nonzero") is True
        and pixel_trace.get("reciprocal_w_zero_rejected") is True
        and math.isfinite(expected_denominator) and abs(expected_denominator) > 1.0e-12
        and math.isclose(
            float(pixel_trace.get("inverse_w_denominator", math.nan)),
            expected_denominator,
            rel_tol=0.0,
            abs_tol=1.0e-6,
        )
        and pixel_trace.get("depth_interpolation") == "screen-affine-ndc"
        and math.isclose(
            float(pixel_trace.get("affine_ndc_depth", math.nan)),
            expected_affine_ndc_depth,
            rel_tol=0.0,
            abs_tol=1.0e-6,
        )
        and math.isclose(
            float(pixel_trace.get("incoming_depth", math.nan)),
            expected_affine_ndc_depth,
            rel_tol=0.0,
            abs_tol=1.0e-6,
        )
        and pixel_trace.get("selected_uv") == perspective_uv,
        "selected blend/depth state": report.get("transparent_depth_write") is False
        and report.get("transparent_order_a_accepted_layers") == 2
        and report.get("selected_blend_linear") is True
        and report.get("selected_alpha_representation") == "straight"
        and report.get("first_difference") == "none",
        "attachment images expose the decisions": perspective_image.pixels != affine_image.pixels
        and transparent_a.pixels != transparent_b.pixels
        and len({
            primitive_image.pixels[index:index + 3]
            for index in range(0, len(primitive_image.pixels), 3)
        }) == 3,
    }
    required_images = {
        "perspective-correct.ppm", "affine-mutation.ppm", "primitive-id.ppm",
        "transparent-order-a.ppm", "transparent-order-b.ppm",
    }
    missing_images = sorted(name for name in required_images if not (output / name).is_file())
    failed = [label for label, passed in checks.items() if not passed]
    if failed or missing_images:
        raise CheckFailure(
            f"04-perspective-depth-blend: independent evidence checks failed={failed} missing_ppm={missing_images}"
        )


def validate_lit_scene_evidence(output: Path) -> None:
    assets = load_json(output / "asset-validation.json")
    culling = load_json(output / "culling-lod.json")
    depth = load_json(output / "depth.json")
    frame = load_json(output / "frame.json")
    statistics = load_json(output / "statistics.json")
    trace = load_json(output / "trace.json")
    attachment_images = {
        name: read_ppm(output / name)
        for name in (
            "final.ppm", "base-color.ppm", "normal-world.ppm", "ndotl.ppm",
            "mip-level.ppm", "object-id.ppm", "primitive-id.ppm",
        )
    }
    seam_image = read_ppm(output / "seam-probe.ppm")
    mutation_report = load_json(output / "mutation-report.json")
    scene_fixture = load_json(FIXTURES / "scene-v1.json")
    cases = assets.get("cases")
    rejected_ids = {
        identifier
        for identifier, payload in cases.items()
        if isinstance(cases, dict) and isinstance(payload, dict) and payload.get("accepted") is False
    } if isinstance(cases, dict) else set()
    normal = assets.get("normal")
    normal_map = assets.get("normal_map")
    seam = assets.get("seam_vertices")
    frustum = culling.get("frustum")
    lod = culling.get("lod")
    render_probe = culling.get("render_probe")
    scene_trace_valid = False
    attachment_trace_valid = False
    fixture_vertices = scene_fixture.get("vertices")
    if isinstance(fixture_vertices, list) and len(fixture_vertices) == 3:
        try:
            ordered = []
            for vertex in fixture_vertices:
                if not isinstance(vertex, dict):
                    raise ValueError("fixture vertex is not an object")
                position = vertex.get("position")
                uv_value = vertex.get("uv")
                color_value = vertex.get("color_linear")
                normal_value = vertex.get("normal")
                if (
                    not isinstance(position, list) or len(position) != 3
                    or not isinstance(uv_value, list) or len(uv_value) != 2
                    or not isinstance(color_value, list) or len(color_value) != 4
                    or not isinstance(normal_value, list) or len(normal_value) != 3
                ):
                    raise ValueError("fixture vertex attribute shape is invalid")
                ordered.append({
                    "screen": [
                        (float(position[0]) * 0.5 + 0.5) * 16.0,
                        (1.0 - (float(position[1]) * 0.5 + 0.5)) * 16.0,
                    ],
                    "uv": [float(value) for value in uv_value],
                    "color": [float(value) for value in color_value[:3]],
                    "normal": [float(value) for value in normal_value],
                })

            def orient(a: list[float], b: list[float], point: list[float]) -> float:
                return (b[0] - a[0]) * (point[1] - a[1]) - (b[1] - a[1]) * (point[0] - a[0])

            if orient(ordered[0]["screen"], ordered[1]["screen"], ordered[2]["screen"]) < 0.0:
                ordered[1], ordered[2] = ordered[2], ordered[1]
            sample_point = [8.5, 8.5]
            area = orient(ordered[0]["screen"], ordered[1]["screen"], ordered[2]["screen"])
            lambdas = [
                orient(ordered[1]["screen"], ordered[2]["screen"], sample_point) / area,
                orient(ordered[2]["screen"], ordered[0]["screen"], sample_point) / area,
                orient(ordered[0]["screen"], ordered[1]["screen"], sample_point) / area,
            ]

            def interpolate(field: str, count: int) -> list[float]:
                return [
                    sum(lambdas[index] * ordered[index][field][component] for index in range(3))
                    for component in range(count)
                ]

            def normalized(value: list[float]) -> list[float]:
                length = math.sqrt(sum(component * component for component in value))
                return [component / length for component in value]

            expected_uv = interpolate("uv", 2)
            expected_color = interpolate("color", 3)
            expected_local_normal = normalized(interpolate("normal", 3))
            world_normal = trace.get("normal_world")
            light = trace.get("light_direction_to_light")
            expected_ndotl = (
                max(sum(float(a) * float(b) for a, b in zip(world_normal, light, strict=True)), 0.0)
                if isinstance(world_normal, list) and len(world_normal) == 3
                and isinstance(light, list) and len(light) == 3 else math.nan
            )
            scene_trace_valid = (
                close_sequence(trace.get("uv"), expected_uv, tolerance=1.0e-6)
                and close_sequence(trace.get("interpolated_vertex_color"), expected_color, tolerance=1.0e-6)
                and close_sequence(trace.get("snapshot_normal_interpolated"), expected_local_normal, tolerance=1.0e-6)
                and trace.get("normal_transform") == "inverse-transpose"
                and math.isfinite(expected_ndotl)
                and math.isclose(float(trace.get("ndotl", math.nan)), expected_ndotl, abs_tol=1.0e-6)
            )

            def srgb_byte(value: float) -> int:
                clamped = max(0.0, min(1.0, value))
                encoded = (
                    clamped * 12.92 if clamped <= 0.0031308
                    else 1.055 * clamped ** (1.0 / 2.4) - 0.055
                )
                return int(math.floor(encoded * 255.0 + 0.5))

            base = trace.get("base_color_linear")
            if isinstance(base, list) and len(base) == 3 and isinstance(world_normal, list):
                pixel_offset = (8 * 16 + 8) * 3
                lighting = 0.1 + 0.9 * expected_ndotl
                expected_base_pixel = bytes(srgb_byte(float(value)) for value in base)
                expected_final_pixel = bytes(srgb_byte(float(value) * lighting) for value in base)
                expected_normal_pixel = bytes(
                    srgb_byte(float(value) * 0.5 + 0.5) for value in world_normal
                )
                expected_ndotl_pixel = bytes([srgb_byte(expected_ndotl)] * 3)
                attachment_trace_valid = (
                    attachment_images["base-color.ppm"].pixels[pixel_offset:pixel_offset + 3]
                    == expected_base_pixel
                    and attachment_images["final.ppm"].pixels[pixel_offset:pixel_offset + 3]
                    == expected_final_pixel
                    and attachment_images["normal-world.ppm"].pixels[pixel_offset:pixel_offset + 3]
                    == expected_normal_pixel
                    and attachment_images["ndotl.ppm"].pixels[pixel_offset:pixel_offset + 3]
                    == expected_ndotl_pixel
                )
        except (ArithmeticError, TypeError, ValueError):
            scene_trace_valid = False
            attachment_trace_valid = False
    render_decisions = culling.get("render_decisions")
    lod_levels = lod.get("levels") if isinstance(lod, dict) else None
    lod_work_valid = (
        isinstance(lod_levels, list) and len(lod_levels) == 8
        and all(level in (0, 1) for level in lod_levels)
        and lod.get("selected_render_level") == lod_levels[2]
        and lod.get("vertex_work") == sum(3 if level == 0 else 2 for level in lod_levels)
        and lod.get("sample_budget") == sum(256 if level == 0 else 128 for level in lod_levels)
        and statistics.get("selected_render_lod") == lod.get("selected_render_level")
        and statistics.get("selected_vertex_work") == lod.get("vertex_work")
        and statistics.get("selected_sample_budget") == lod.get("sample_budget")
        and statistics.get("lod_transitions") == lod.get("transitions")
    )
    checks = {
        "shared scene contract": assets.get("scene_id") == "shared-textured-triangle-v1"
        and frame.get("scene") == "shared-textured-triangle-v1",
        "asset failures": rejected_ids == {
            "invalid_index", "attribute_count_mismatch", "cycle_hierarchy",
            "singular_normal_matrix", "degenerate_triangle",
        },
        "seam-safe vertex identity": isinstance(seam, dict)
        and seam.get("semantic_unique") == 4 and seam.get("position_only_unique") == 3
        and seam.get("selected_unique") == 4 and seam.get("selected_policy") == "position+uv"
        and close_sequence(seam.get("selected_duplicate_uv"), [0.75, 0.25], tolerance=1.0e-8)
        and type(seam.get("probe_color_delta")) in (int, float)
        and float(seam["probe_color_delta"]) > 0.1
        and seam_image.pixels[:3] != seam_image.pixels[3:6],
        "explicit out-of-range UV": isinstance(cases, dict)
        and close_sequence(cases.get("uv_negative_repeat", {}).get("wrapped"), [0.75, 0.75])
        and close_sequence(cases.get("uv_out_of_range_repeat", {}).get("wrapped"), [0.25, 0.25]),
        "inverse-transpose normal": isinstance(normal, dict)
        and abs(float(normal.get("correct_tangent_dot", 1.0))) <= 1.0e-6
        and abs(float(normal.get("mutation_tangent_dot", 0.0))) > 0.1
        and close_sequence(normal.get("snapshot_input"), [0.0, 0.0, -1.0])
        and normal.get("selected_transform") == "inverse-transpose"
        and normal.get("selected_world") == trace.get("normal_world"),
        "normal map is data": isinstance(normal_map, dict)
        and normal_map.get("encoding") == "data-linear"
        and close_sequence(normal_map.get("flat_decoded"), [0.0, 0.0, 1.0]),
        "conservative culling": isinstance(frustum, dict)
        and frustum.get("input") == 3 and frustum.get("visible") == 2
        and frustum.get("inside") == 1 and frustum.get("intersecting") == 1
        and frustum.get("outside") == 1 and culling.get("bounds_all_corners_contained") is True
        and render_decisions == [
            {"object": 0, "relation": "inside", "drawn": True},
            {"object": 1, "relation": "outside", "drawn": False},
            {"object": 2, "relation": "intersecting", "drawn": True},
        ]
        and render_probe == {"visible": True, "output_primitives": 1, "covered_samples": 60},
        "LOD hysteresis": isinstance(lod, dict) and lod.get("hysteresis", 0.0) > 0.0
        and lod.get("transitions") == 2 and len(lod.get("levels", [])) == 8
        and lod_work_valid,
        "depth and frame accounting": depth.get("extent") == [16, 16]
        and depth.get("clear") == 1.0 and depth.get("covered_samples") == 60
        and frame.get("covered_samples") == 60 and frame.get("invalid_non_finite_values") == 0,
        "statistics agree": statistics.get("input_triangles") == 1
        and statistics.get("covered_samples") == statistics.get("depth_passed_samples") == 60
        and statistics.get("invalid_fixture_count") == 5
        and statistics.get("visible_objects") == 2,
        "linear lighting trace": trace.get("mip_1x1_linear") == [0.5, 0.5, 0.5]
        and isinstance(trace.get("ndotl"), (int, float)) and 0.0 < float(trace["ndotl"]) <= 1.0
        and trace.get("normal_map_decoded") == normal_map.get("flat_decoded")
        and scene_trace_valid and attachment_trace_valid,
        "baseline mutation report": mutation_report == {
            "schema_version": 1,
            "mutation": None,
            "recognized": True,
            "first_difference": "none",
            "rejected": False,
        },
        "debug attachments mark every covered sample": all(
            sum(
                image.pixels[index:index + 3] != b"\x00\x00\x00"
                for index in range(0, len(image.pixels), 3)
            ) == 60
            for image in attachment_images.values()
        ),
        "tracked lit-scene golden": exact_ppm_matches(
            EXPECTED / "lit-scene-final.ppm", output / "final.ppm"
        ),
    }
    required_images = {
        "final.ppm", "base-color.ppm", "normal-world.ppm", "ndotl.ppm",
        "mip-level.ppm", "object-id.ppm", "primitive-id.ppm",
    }
    missing_images = sorted(name for name in required_images if not (output / name).is_file())
    failed = [label for label, passed in checks.items() if not passed]
    if failed or missing_images:
        raise CheckFailure(
            f"05-textured-lit-scene: independent evidence checks failed={failed} missing_ppm={missing_images}"
        )


def validate_cpu_mutation_evidence(stage: str, output: Path, mutation: str) -> None:
    run_payload = load_json(output / "run.json")
    invariants = run_payload.get("invariants")
    if not isinstance(invariants, dict):
        raise CheckFailure(f"{stage}/{mutation}: missing mutation invariant evidence")
    if stage == "03-triangle-coverage":
        counts = load_json(output / "coverage-counts.json")
        trace = load_json(output / "setup-trace.json")
        report = load_json(output / "mutation-report.json")
        expected = {
            "make_every_edge_inclusive": (
                "coverage-counts.overlap_samples", "shared_edge_has_no_overlap"
            ),
            "make_every_edge_exclusive": (
                "coverage-counts.gap_samples", "shared_edge_has_no_gap"
            ),
            "truncate_negative_bounding_box": (
                "coverage-counts.offscreen_boundary.tested_samples",
                "bounding_box_never_writes_outside_framebuffer",
            ),
            "keep_old_front_face_after_y_flip": (
                "coverage-counts.reversed_coverage.reversed_samples",
                "winding_normalization_preserves_coverage_set",
            ),
            "divide_by_zero_for_degenerate_area": (
                "coverage-counts.degenerate_setup.nonfinite_detected",
                "degenerate_triangle_writes_no_samples",
            ),
        }.get(mutation)
        if expected is None:
            raise CheckFailure(f"{stage}/{mutation}: mutation lacks an artifact oracle")
        offscreen = counts.get("offscreen_boundary")
        reversed_coverage = counts.get("reversed_coverage")
        degenerate = counts.get("degenerate_setup")
        observable = {
            "make_every_edge_inclusive": type(counts.get("overlap_samples")) is int
            and counts["overlap_samples"] > 0
            and not exact_ppm_matches(EXPECTED / "shared-edge-primitive-id.ppm", output / "primitive-id.ppm"),
            "make_every_edge_exclusive": type(counts.get("gap_samples")) is int
            and counts["gap_samples"] > 0
            and not exact_ppm_matches(EXPECTED / "shared-edge-primitive-id.ppm", output / "primitive-id.ppm"),
            "truncate_negative_bounding_box": isinstance(offscreen, dict)
            and type(offscreen.get("tested_samples")) is int
            and offscreen["tested_samples"] > int(offscreen.get("expected_tested_samples", 0)),
            "keep_old_front_face_after_y_flip": isinstance(reversed_coverage, dict)
            and reversed_coverage.get("reversed_samples") != reversed_coverage.get("forward_samples")
            and type(reversed_coverage.get("winding_rejections")) is int
            and reversed_coverage["winding_rejections"] > 0,
            "divide_by_zero_for_degenerate_area": degenerate == {
                "guarded": False, "nonfinite_detected": True,
            },
        }[mutation]
        checks = {
            "mutation report identity": report.get("mutation") == mutation
            and report.get("recognized") is True and report.get("rejected") is True,
            "first artifact difference": report.get("first_difference") == expected[0]
            and trace.get("first_difference") == expected[0],
            "named invariant failed": invariants.get(expected[1]) is False,
            "observable artifact changed": observable,
        }
    elif stage == "04-perspective-depth-blend":
        depth = load_json(output / "depth.json")
        trace = load_json(output / "pixel-traces" / "sample-3-3.json")
        report = load_json(output / "report.json")
        expected = {
            "use_affine_uv": (
                "pixel-traces/sample-3-3.json.selected_uv",
                "perspective_uv_is_continuous_across_quad_diagonal",
            ),
            "store_view_space_z_as_depth": (
                "depth.json.order_a.depth", "depth_is_finite_and_in_zero_one"
            ),
            "reverse_depth_compare_without_projection_change": (
                "depth.json.order_a.owner", "opaque_visibility_is_draw_order_invariant"
            ),
            "enable_depth_write_for_blended_surface": (
                "report.json.transparent_order_a_accepted_layers",
                "alpha_representation_matches_state",
            ),
            "blend_srgb_encoded_values": (
                "report.json.selected_blend_linear", "blend_occurs_in_linear_color"
            ),
            "mismatch_alpha_representation_and_factors": (
                "report.json.selected_alpha_representation", "alpha_representation_matches_state"
            ),
        }.get(mutation)
        if expected is None:
            raise CheckFailure(f"{stage}/{mutation}: mutation lacks an artifact oracle")
        order_a = depth.get("order_a")
        observable = {
            "use_affine_uv": trace.get("selected_uv") == trace.get("affine_uv")
            and trace.get("selected_uv") != trace.get("perspective_uv")
            and exact_ppm_matches(output / "affine-mutation.ppm", output / "perspective-correct.ppm"),
            "store_view_space_z_as_depth": isinstance(order_a, dict)
            and type(order_a.get("depth")) in (int, float) and float(order_a["depth"]) > 1.0,
            "reverse_depth_compare_without_projection_change": depth.get("compare") == "greater"
            and report.get("selected_depth_compare") == "greater"
            and isinstance(order_a, dict) and order_a.get("owner") != 1,
            "enable_depth_write_for_blended_surface": report.get("transparent_depth_write") is True
            and report.get("transparent_order_a_accepted_layers") == 1,
            "blend_srgb_encoded_values": report.get("selected_blend_linear") is False,
            "mismatch_alpha_representation_and_factors":
            report.get("selected_alpha_representation") == "straight-data-with-premultiplied-factors",
        }[mutation]
        checks = {
            "first artifact difference": report.get("first_difference") == expected[0],
            "named invariant failed": invariants.get(expected[1]) is False,
            "observable artifact changed": observable,
            "finite reciprocal-w guard remains active": trace.get("denominator_finite_nonzero") is True
            and trace.get("reciprocal_w_zero_rejected") is True,
        }
    elif stage == "05-textured-lit-scene":
        assets = load_json(output / "asset-validation.json")
        culling = load_json(output / "culling-lod.json")
        trace = load_json(output / "trace.json")
        statistics_payload = load_json(output / "statistics.json")
        report = load_json(output / "mutation-report.json")
        seam = assets.get("seam_vertices")
        normal = assets.get("normal")
        normal_map = assets.get("normal_map")
        cases = assets.get("cases")
        lod = culling.get("lod")
        expected = {
            "deduplicate_by_position_only": (
                "asset-validation.json.seam_vertices.selected_unique",
                "indices_and_attribute_counts_are_valid",
            ),
            "transform_normal_with_model_matrix": (
                "trace.json.normal_world", "normals_are_valid_after_nonuniform_scale"
            ),
            "mark_normal_map_as_srgb": (
                "trace.json.normal_map_decoded", "normal_maps_are_data_textures"
            ),
            "average_encoded_color_for_mips": (
                "trace.json.mip_1x1_linear", "lighting_uses_linear_rgb"
            ),
            "transform_only_aabb_min_and_max": (
                "culling-lod.json.bounds_all_corners_contained",
                "world_bounds_conservatively_contain_geometry",
            ),
            "accept_scene_cycle": (
                "asset-validation.json.cases.cycle_hierarchy.accepted",
                "scene_hierarchy_is_acyclic",
            ),
            "remove_lod_hysteresis": (
                "culling-lod.json.lod.levels[2]",
                "lod_hysteresis_prevents_boundary_oscillation",
            ),
        }.get(mutation)
        if expected is None:
            raise CheckFailure(f"{stage}/{mutation}: mutation lacks an artifact oracle")
        levels = lod.get("levels") if isinstance(lod, dict) else None
        lod_work_changed = (
            isinstance(levels, list) and len(levels) == 8 and all(level in (0, 1) for level in levels)
            and lod.get("hysteresis") == 0.0
            and lod.get("selected_render_level") == levels[2] == 1
            and lod.get("vertex_work") == sum(3 if level == 0 else 2 for level in levels)
            and lod.get("sample_budget") == sum(256 if level == 0 else 128 for level in levels)
            and statistics_payload.get("selected_render_lod") == 1
            and statistics_payload.get("selected_vertex_work") == lod.get("vertex_work")
            and statistics_payload.get("selected_sample_budget") == lod.get("sample_budget")
        )
        observable = {
            "deduplicate_by_position_only": isinstance(seam, dict)
            and seam.get("selected_unique") == seam.get("position_only_unique") == 3
            and seam.get("selected_policy") == "position-only"
            and close_sequence(seam.get("selected_duplicate_uv"), [0.0, 0.0])
            and math.isclose(float(seam.get("probe_color_delta", math.nan)), 0.0, abs_tol=1.0e-9)
            and read_ppm(output / "seam-probe.ppm").pixels[:3]
            == read_ppm(output / "seam-probe.ppm").pixels[3:6],
            "transform_normal_with_model_matrix": isinstance(normal, dict)
            and normal.get("selected_transform") == "model-3x3"
            and trace.get("normal_transform") == "model-3x3"
            and normal.get("selected_world") == trace.get("normal_world")
            and not exact_ppm_matches(EXPECTED / "lit-scene-final.ppm", output / "final.ppm"),
            "mark_normal_map_as_srgb": isinstance(normal_map, dict)
            and not close_sequence(normal_map.get("flat_decoded"), [0.0, 0.0, 1.0])
            and trace.get("normal_map_decoded") == normal_map.get("flat_decoded")
            and not exact_ppm_matches(EXPECTED / "lit-scene-final.ppm", output / "final.ppm"),
            "average_encoded_color_for_mips": not close_sequence(
                trace.get("mip_1x1_linear"), [0.5, 0.5, 0.5]
            ) and not exact_ppm_matches(EXPECTED / "lit-scene-final.ppm", output / "final.ppm"),
            "transform_only_aabb_min_and_max": culling.get("bounds_all_corners_contained") is False,
            "accept_scene_cycle": isinstance(cases, dict)
            and isinstance(cases.get("cycle_hierarchy"), dict)
            and cases["cycle_hierarchy"].get("accepted") is True,
            "remove_lod_hysteresis": lod_work_changed
            and not exact_ppm_matches(EXPECTED / "lit-scene-final.ppm", output / "final.ppm"),
        }[mutation]
        checks = {
            "mutation report identity": report.get("mutation") == mutation
            and report.get("recognized") is True and report.get("rejected") is True,
            "first artifact difference": report.get("first_difference") == expected[0],
            "named invariant failed": invariants.get(expected[1]) is False,
            "observable state or rendered artifact changed": observable,
        }
    else:
        return
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        raise CheckFailure(f"{stage}/{mutation}: CPU mutation evidence failed={failed}")


def is_hash(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 16
        and all(character in "0123456789abcdef" for character in value)
    )


def fnv1a64(data: bytes) -> str:
    value = 14695981039346656037
    for byte in data:
        value ^= byte
        value = (value * 1099511628211) & ((1 << 64) - 1)
    return f"{value:016x}"


def resize_clear_correctness_hash(path: Path) -> str:
    image = read_ppm(path)
    if (image.width, image.height) != (96, 72):
        raise CheckFailure("resize generation evidence must be exactly 96x72")
    rgba = bytearray()
    for offset in range(0, len(image.pixels), 3):
        rgba.extend(image.pixels[offset:offset + 3])
        rgba.append(255)
    depth = b"\xff\xff" * (image.width * image.height)
    canonical = (
        f"{fixture_scene_hash()}:{fnv1a64(bytes(rgba))}:{fnv1a64(depth)}".encode("ascii")
    )
    return fnv1a64(canonical)


def log_has_zero_fatal(path: Path) -> bool:
    return load_key_value_log(path).get("fatal") == "0"


def valid_stage06_lifecycle(
    resources: dict[str, object],
    resize: dict[str, object],
    evidence: dict[str, object],
    environment: dict[str, object],
) -> bool:
    slots = resources.get("slot_state")
    slots_valid, _ = valid_lifecycle_slots(resources.get("frame_slots"), slots)
    generations_valid, generations = valid_lifecycle_generations(
        resources.get("generation_lifecycle"),
        actual_gpu=True,
        required_hash_generations={1, 2},
    )
    persistent = resources.get("actual_persistent_lifecycle")
    persistent_valid = (
        isinstance(persistent, dict)
        and set(persistent) == {
            "required", "executed", "slot_count", "slot_zero_reused_after_completion",
            "generation_one_retired_after_completion", "generation_two_readback_after_completion",
            "submit_count", "driver", "device", "events",
        }
        and persistent.get("required") is True
        and persistent.get("executed") is True
        and type(persistent.get("slot_count")) is int
        and persistent["slot_count"] >= 2
        and persistent.get("submit_count") == 3
        and persistent.get("slot_zero_reused_after_completion") is True
        and persistent.get("generation_one_retired_after_completion") is True
        and persistent.get("generation_two_readback_after_completion") is True
        and persistent.get("driver") == environment.get("backend")
        and persistent.get("device") == environment.get("device")
        and persistent.get("events") == EXPECTED_ACTUAL_LIFECYCLE_EVENTS
    )
    resize_fields = {
        "schema_version", "events", "zero_extent_target_creation_attempted",
        "old_generation_retired_after_last_use", "actual_gpu_extent_transition_required",
        "actual_gpu_extent_transition_executed", "actual_gpu_events",
        "generation_2_correctness_hash_fnv1a64",
    }
    resize_valid = (
        set(resize) == resize_fields
        and resize.get("zero_extent_target_creation_attempted") is False
        and resize.get("old_generation_retired_after_last_use") is True
        and resize.get("actual_gpu_extent_transition_required") is True
        and resize.get("actual_gpu_extent_transition_executed") is True
        and resize.get("actual_gpu_events") == EXPECTED_ACTUAL_LIFECYCLE_EVENTS
        and is_hash(resize.get("generation_2_correctness_hash_fnv1a64"))
    )
    if not (slots_valid and generations_valid and persistent_valid and resize_valid):
        return False
    if (
        resources.get("model_valid") is not True
        or resources.get("retirement_rule") != "retired_at_completion >= last_use_submission"
        or generations[0].get("correctness_hash_fnv1a64")
        != evidence.get("color_depth_correctness_hash_fnv1a64")
        or generations[1].get("correctness_hash_fnv1a64")
        != resize.get("generation_2_correctness_hash_fnv1a64")
    ):
        return False
    return valid_lifecycle_events(
        resize.get("events"), slots, generations,
        {"submission": 3, "mapped_after_completion": 3, "safe": True},
    )


def validate_gpu_first_frame_evidence(output: Path) -> None:
    conventions = load_json(output / "conventions.json")
    environment = load_json(output / "environment.json")
    evidence = load_json(output / "evidence.json")
    frame_trace = load_json(output / "frame-trace.json")
    pipeline = load_json(output / "pipelines.json")
    resize = load_json(output / "resize-trace.json")
    resources = load_json(output / "resources.json")
    scene = load_json(output / "scene.json")
    shader = load_json(output / "shader-manifests" / "triangle.json")
    static_shader = load_json(PROJECT / "shaders" / "manifest.json")
    tracked_msl_hash = fnv1a64((PROJECT / "shaders" / "triangle.metal").read_bytes())
    tracked_hlsl_hash = fnv1a64((PROJECT / "shaders" / "triangle.hlsl").read_bytes())
    frame_image = read_ppm(output / "screenshot.ppm")
    resized_image_path = output / "resize-generation-2.ppm"
    pixels = [
        frame_image.pixels[index:index + 3]
        for index in range(0, len(frame_image.pixels), 3)
    ]
    clear = pixels[0] if pixels else b""
    colored = sum(pixel != clear for pixel in pixels)
    events = frame_trace.get("events")
    event_names = (
        [item.get("event") for item in events if isinstance(item, dict)]
        if isinstance(events, list) else []
    )
    timing = frame_trace.get("timing")
    resize_events = resize.get("events")
    zero_event = next((
        item for item in resize_events
        if isinstance(item, dict) and item.get("event") == "skip-zero-extent"
    ), None) if isinstance(resize_events, list) else None
    checks = {
        "shared graphics conventions": conventions.get("vector") == "column"
        and conventions.get("handedness") == "left"
        and conventions.get("ndc_depth") == "0..1"
        and conventions.get("viewport_origin") == "top-left",
        "actual supported GPU": environment.get("actual_gpu") is True
        and environment.get("backend") == "metal"
        and isinstance(environment.get("sdl_version"), str),
        "scene identity and hash": scene.get("scene_snapshot_id") == "shared-textured-triangle-v1"
        and evidence.get("scene_snapshot_id") == scene.get("scene_snapshot_id")
        and scene.get("deterministic_scene_hash_fnv1a64") == fixture_scene_hash()
        and evidence.get("scene_hash_fnv1a64") == scene.get("deterministic_scene_hash_fnv1a64")
        and scene.get("vertex_count") == 3 and scene.get("index_count") == 3
        and scene.get("primitive_count") == 1,
        "environment fingerprint": is_hash(environment.get("environment_fingerprint_fnv1a64"))
        and evidence.get("environment_fingerprint_fnv1a64")
        == environment.get("environment_fingerprint_fnv1a64"),
        "correctness evidence": evidence.get("primitive_count") == 1
        and evidence.get("sample_count") == 1
        and evidence.get("colored_pixel_count") == colored
        and 0 < colored < frame_image.width * frame_image.height
        and is_hash(evidence.get("color_hash_fnv1a64"))
        and is_hash(evidence.get("depth_hash_fnv1a64"))
        and is_hash(evidence.get("color_depth_correctness_hash_fnv1a64")),
        "offscreen extent": (frame_image.width, frame_image.height) == (64, 64),
        "shader and vertex layout": shader.get("format") == "MSL-source"
        and shader.get("entry_points") == {"vertex": "vertex_main", "fragment": "fragment_main"}
        and shader.get("vertex_layout") == ["float3-position@0", "float4-color@12"]
        and shader.get("source_hash_fnv1a64") == tracked_msl_hash
        and static_shader.get("metal_source_hash_fnv1a64") == tracked_msl_hash
        and static_shader.get("hlsl_source_hash_fnv1a64") == tracked_hlsl_hash
        and static_shader.get("sources") == {
            "metal_runtime": "triangle.metal", "portable_offline": "triangle.hlsl"
        }
        and static_shader.get("minimum_sdl3") == "3.4.10"
        and static_shader.get("generated_binaries_tracked") is False
        and pipeline.get("vertex_stride") == 28,
        "pass attachments": pipeline.get("color_format") == "R8G8B8A8_UNORM"
        and pipeline.get("depth_format") == "D16_UNORM"
        and pipeline.get("depth_compare") == "less" and pipeline.get("depth_write") is True,
        "frame slots, generations, and actual resize lifecycle": valid_stage06_lifecycle(
            resources, resize, evidence, environment
        ),
        "completion before readback": event_names == [
            "map-upload", "copy-upload", "color-depth-pass", "download-recorded",
            "fence-complete", "readback-mapped",
        ],
        "timing labels": isinstance(timing, dict)
        and timing.get("measurement_kind") == "cpu-wall-clock"
        and timing.get("is_gpu_timestamp") is False
        and all(int(timing.get(name, 0)) > 0 for name in (
            "cpu_record_ns", "cpu_submit_ns", "submit_to_fence_ns"
        )),
        "zero extent and resize generation": isinstance(zero_event, dict)
        and zero_event.get("extent") == [0, 0] and zero_event.get("target_created") is False
        and resize.get("old_generation_retired_after_last_use") is True
        and resize.get("generation_2_correctness_hash_fnv1a64")
        == resize_clear_correctness_hash(resized_image_path),
        "validation baseline": log_has_zero_fatal(output / "validation.log"),
    }
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        raise CheckFailure(f"06-gpu-first-frame: independent evidence checks failed={failed}")


def percentile95(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def sample_median(values: list[int]) -> int | float:
    return statistics.median(values)


def valid_lifecycle_slots(slot_count: object, slots: object) -> tuple[bool, list[int]]:
    expected = [
        {
            "slot": 0,
            "submissions": [1, 3],
            "last_use": 3,
            "completion_before_reuse": 1,
            "reuse_safe": True,
        },
        {
            "slot": 1,
            "submissions": [2],
            "last_use": 2,
            "completion_before_reuse": 0,
            "reuse_safe": True,
        },
        {
            "slot": 2,
            "submissions": [],
            "last_use": 0,
            "completion_before_reuse": 0,
            "reuse_safe": True,
        },
    ]
    if type(slot_count) is not int or slot_count != 3 or slots != expected:
        return False, []
    return True, [1, 2, 3]


def valid_lifecycle_generations(
    generations: object,
    *,
    actual_gpu: bool,
    required_hash_generations: set[int] | None = None,
) -> tuple[bool, list[dict[str, object]]]:
    if (
        not isinstance(generations, list)
        or len(generations) != 2
        or not all(isinstance(item, dict) for item in generations)
    ):
        return False, []
    if [item.get("generation") for item in generations] != [1, 2]:
        return False, []
    expected_extents = ([64, 64], [96, 72])
    expected_last_use = (2, 3)
    hashes = ({1, 2} if actual_gpu else set()) if required_hash_generations is None else required_hash_generations
    if not hashes.issubset({1, 2}) or (not actual_gpu and hashes):
        return False, []
    for index, item in enumerate(generations):
        generation_id = index + 1
        required_fields = {
            "generation", "extent", "last_use", "last_use_submission",
            "retired_at_completion", "retirement_safe", "actual_gpu_rendered",
        }
        if generation_id in hashes:
            required_fields.add("correctness_hash_fnv1a64")
        if (
            set(item) != required_fields
            or item.get("extent") != expected_extents[index]
            or item.get("last_use") != expected_last_use[index]
            or item.get("last_use_submission") != expected_last_use[index]
            or item.get("retired_at_completion") != expected_last_use[index]
            or item.get("retirement_safe") is not True
            or item.get("actual_gpu_rendered") is not actual_gpu
            or (generation_id in hashes and not is_hash(item.get("correctness_hash_fnv1a64")))
        ):
            return False, []
    return True, generations


def expected_lifecycle_events() -> list[dict[str, object]]:
    return [
        {"seq": 1, "event": "create-generation", "generation": 1,
         "extent": [64, 64], "target_created": True},
        {"seq": 2, "event": "submit", "slot": 0, "submission": 1, "generation": 1},
        {"seq": 3, "event": "submit", "slot": 1, "submission": 2, "generation": 1},
        {"seq": 4, "event": "skip-zero-extent", "generation": 1,
         "extent": [0, 0], "target_created": False},
        {"seq": 5, "event": "complete", "completion": 1},
        {"seq": 6, "event": "create-generation", "generation": 2,
         "extent": [96, 72], "target_created": True},
        {"seq": 7, "event": "submit", "slot": 0, "submission": 3, "generation": 2},
        {"seq": 8, "event": "complete", "completion": 2},
        {"seq": 9, "event": "retire-generation", "generation": 1, "completion": 2},
        {"seq": 10, "event": "complete", "completion": 3},
        {"seq": 11, "event": "map-readback", "submission": 3,
         "generation": 2, "completion": 3},
        {"seq": 12, "event": "shutdown-retire", "generation": 2, "completion": 3},
    ]


def valid_lifecycle_events(
    events: object,
    slots: list[dict[str, object]],
    generations: list[dict[str, object]],
    readback: dict[str, object],
) -> bool:
    return (
        events == expected_lifecycle_events()
        and slots[0].get("submissions") == [1, 3]
        and slots[1].get("submissions") == [2]
        and generations[0].get("last_use_submission") == 2
        and generations[1].get("last_use_submission") == 3
        and readback == {"submission": 3, "mapped_after_completion": 3, "safe": True}
    )


def valid_actual_lifecycle_events(events: object, *, required: bool) -> bool:
    return events == (EXPECTED_ACTUAL_LIFECYCLE_EVENTS if required else [])


def valid_actual_gpu_probe(probe: object, environment: dict[str, object]) -> bool:
    return (
        isinstance(probe, dict)
        and set(probe) == {
            "required", "executed", "extent", "same_device_submit_count", "slot_count",
            "slot_zero_reused_after_completion", "generation_one_retired_after_completion",
            "generation_two_readback_after_completion", "driver", "device", "events",
        }
        and probe.get("required") is True
        and probe.get("executed") is True
        and probe.get("extent") == [96, 72]
        and probe.get("same_device_submit_count") == 3
        and type(probe.get("slot_count")) is int
        and probe["slot_count"] >= 2
        and probe.get("slot_zero_reused_after_completion") is True
        and probe.get("generation_one_retired_after_completion") is True
        and probe.get("generation_two_readback_after_completion") is True
        and probe.get("driver") == environment.get("backend")
        and probe.get("device") == environment.get("device")
        and valid_actual_lifecycle_events(probe.get("events"), required=True)
    )


def valid_lifecycle_defect_events(events: object, mutation: str) -> bool:
    violation = LIFECYCLE_VIOLATIONS.get(mutation)
    if violation is None:
        return events == expected_lifecycle_events()
    normal = expected_lifecycle_events()
    if violation == "write-before-slot-completion":
        expected = normal[:2] + [{
            "seq": 3,
            "event": "reject",
            "slot": 0,
            "submission": 2,
            "generation": 1,
            "completion": 0,
            "target_created": False,
            "reason": violation,
        }]
    elif violation == "stale-resize-generation":
        expected = normal[:6] + [{
            "seq": 7,
            "event": "reject",
            "slot": 2,
            "submission": 3,
            "generation": 1,
            "completion": 1,
            "target_created": False,
            "reason": violation,
        }]
    else:
        expected = normal[:7] + [{
            "seq": 8,
            "event": "reject",
            "submission": 3,
            "generation": 2,
            "completion": 1,
            "target_created": False,
            "reason": violation,
        }]
    return events == expected


def validate_gpu_mutation_evidence(stage: str, output: Path, mutation: str) -> None:
    diagnostic = load_json(output / "mutation-diagnostic.json")
    lifecycle_case = mutation in LIFECYCLE_VIOLATIONS
    expected_violation = LIFECYCLE_VIOLATIONS.get(mutation)
    checks = {
        "closed diagnostic schema": set(diagnostic) == {
            "schema_version", "mutation", "executed_on_gpu", "lifecycle_transition_executed",
            "lifecycle_model_rejected", "rejection_oracle", "violation", "safe_rejection",
            "diagnostic",
        },
        "mutation identity": diagnostic.get("mutation") == mutation,
        "no unsafe GPU execution": diagnostic.get("executed_on_gpu") is False
        and diagnostic.get("safe_rejection") is True,
        "executed lifecycle oracle":
        diagnostic.get("lifecycle_transition_executed") is lifecycle_case
        and diagnostic.get("lifecycle_model_rejected") is lifecycle_case
        and diagnostic.get("violation") == expected_violation
        and diagnostic.get("rejection_oracle") == (
            "deterministic-lifecycle-state-machine"
            if lifecycle_case else "pipeline-static-preflight-contract"
        ),
        "diagnostic is explicit": isinstance(diagnostic.get("diagnostic"), str)
        and len(diagnostic["diagnostic"]) >= 60,
    }
    if stage == "07-frame-debugging":
        trace = load_json(output / mutation / "frame-trace.json")
        checks["diagnostic lifecycle trace"] = valid_lifecycle_defect_events(
            trace.get("lifecycle_events"), mutation
        )
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        raise CheckFailure(f"{stage}/{mutation}: GPU mutation evidence failed={failed}")


def valid_capstone_known_bad_suite(suite: dict[str, object]) -> bool:
    cases = suite.get("cases")
    if (
        set(suite) != {
            "schema_version", "expected_exit", "unsafe_gpu_submission_permitted", "cases",
            "registry_complete", "lifecycle_registry_complete", "edge_mask_abuse_probe_rejected",
        }
        or suite.get("expected_exit") != 4
        or suite.get("unsafe_gpu_submission_permitted") is not False
        or suite.get("registry_complete") is not True
        or suite.get("lifecycle_registry_complete") is not True
        or suite.get("edge_mask_abuse_probe_rejected") is not True
        or not isinstance(cases, list)
        or len(cases) != len(CAPSTONE_MUTATION_METADATA)
        or not all(isinstance(item, dict) for item in cases)
    ):
        return False
    seen: set[str] = set()
    for item in cases:
        if set(item) != {
            "id", "first_difference_stage", "violated_invariant", "oracle",
            "lifecycle_transition_executed", "lifecycle_model_rejected",
            "lifecycle_violation", "safely_rejected_before_gpu_submission",
        }:
            return False
        identifier = item.get("id")
        if not isinstance(identifier, str) or identifier in seen:
            return False
        seen.add(identifier)
        metadata = CAPSTONE_MUTATION_METADATA.get(identifier)
        lifecycle_case = identifier in LIFECYCLE_VIOLATIONS
        if (
            metadata is None
            or item.get("first_difference_stage") != metadata[0]
            or item.get("violated_invariant") != metadata[1]
            or item.get("oracle") != "ordered-artifact-or-lifecycle-state-machine"
            or item.get("lifecycle_transition_executed") is not lifecycle_case
            or item.get("lifecycle_model_rejected") is not lifecycle_case
            or item.get("lifecycle_violation") != LIFECYCLE_VIOLATIONS.get(identifier)
            or item.get("safely_rejected_before_gpu_submission") is not True
        ):
            return False
    return seen == set(CAPSTONE_MUTATION_METADATA)


def valid_lifecycle_model(lifecycle: dict[str, object], *, actual_gpu: bool, capstone: bool) -> bool:
    required_fields = {
        "schema_version", "slot_count", "slots", "generations", "zero_extent", "readback",
        "events", "model_valid", "violation",
    }
    if capstone:
        required_fields |= {
            "actual_gpu_extent_transition_required", "actual_gpu_extent_transition_executed",
            "actual_gpu_events",
        }
    if (
        set(lifecycle) != required_fields
        or lifecycle.get("model_valid") is not True
        or lifecycle.get("violation") is not None
    ):
        return False
    slots_valid, _ = valid_lifecycle_slots(lifecycle.get("slot_count"), lifecycle.get("slots"))
    generations_valid, generations = valid_lifecycle_generations(
        lifecycle.get("generations"), actual_gpu=actual_gpu
    )
    zero_extent = lifecycle.get("zero_extent")
    expected_zero_fields = {"target_created", "frame_skipped"} | ({"extent"} if capstone else set())
    zero_valid = (
        isinstance(zero_extent, dict)
        and set(zero_extent) == expected_zero_fields
        and (not capstone or zero_extent.get("extent") == [0, 0])
        and zero_extent.get("target_created") is False
        and zero_extent.get("frame_skipped") is True
    )
    readback = lifecycle.get("readback")
    readback_valid = (
        isinstance(readback, dict)
        and set(readback) == {"submission", "mapped_after_completion", "safe"}
        and readback.get("submission") == 3
        and readback.get("mapped_after_completion") == 3
        and readback.get("safe") is True
    )
    transition_valid = not capstone or (
        lifecycle.get("actual_gpu_extent_transition_required") is actual_gpu
        and lifecycle.get("actual_gpu_extent_transition_executed") is actual_gpu
        and valid_actual_lifecycle_events(
            lifecycle.get("actual_gpu_events"), required=actual_gpu
        )
    )
    return (
        slots_valid
        and generations_valid
        and zero_valid
        and readback_valid
        and transition_valid
        and valid_lifecycle_events(
            lifecycle.get("events"), lifecycle.get("slots", []), generations, readback
        )
    )


def validate_frame_debugging_evidence(output: Path) -> None:
    environment = load_json(output / "environment.json")
    lifecycle = load_json(output / "lifecycle.json")
    timing = load_json(output / "timing-report.json")
    lifecycle_valid = valid_lifecycle_model(lifecycle, actual_gpu=False, capstone=False)
    case_checks = []
    semantic_cases = 0
    validation_caught_cases = 0
    reference_after_pixels: bytes | None = None
    for case in DIAGNOSTIC_CASES:
        directory = output / case
        required = {
            "before.ppm", "after.ppm", "capture-reference.txt", "diff.json",
            "environment.json", "frame-trace.json", "report.md", "timing.json", "validation.log",
        }
        if not all((directory / name).is_file() for name in required):
            case_checks.append(False)
            continue
        diff = load_json(directory / "diff.json")
        trace = load_json(directory / "frame-trace.json")
        report = (directory / "report.md").read_text(encoding="utf-8")
        before = read_ppm(directory / "before.ppm")
        after = read_ppm(directory / "after.ppm")
        validation = load_key_value_log(directory / "validation.log")
        capture = load_key_value_log(directory / "capture-reference.txt")
        case_environment = load_json(directory / "environment.json")
        case_timing = load_json(directory / "timing.json")
        expected_fatal = "1" if case in VALIDATION_CAUGHT_CASES else "0"
        expected_classification = (
            "api-or-pipeline-contract"
            if case in VALIDATION_CAUGHT_CASES
            else "semantic-image-or-lifecycle-failure"
        )
        if case in SEMANTIC_DIAGNOSTIC_CASES and validation.get("fatal") == "0":
            semantic_cases += 1
        if case in VALIDATION_CAUGHT_CASES and validation.get("fatal") == "1":
            validation_caught_cases += 1
        lifecycle_case = case in LIFECYCLE_VIOLATIONS
        expected_violation = LIFECYCLE_VIOLATIONS.get(case)
        differing_channel_bytes = sum(
            left != right for left, right in zip(before.pixels, after.pixels, strict=True)
        )
        after_matches_other_cases = (
            reference_after_pixels is None or after.pixels == reference_after_pixels
        )
        if reference_after_pixels is None:
            reference_after_pixels = after.pixels
        case_checks.append(
            before.width == after.width == 64
            and before.height == after.height == 64
            and before.pixels != after.pixels
            and diff.get("case") == case
            and diff.get("oracle_rejects_before") is (not lifecycle_case)
            and diff.get("case_oracle_rejected") is True
            and diff.get("illustrative_before_differs") is True
            and diff.get("after_matches_reference") is True
            and diff.get("different_channel_bytes") == differing_channel_bytes
            and differing_channel_bytes > 0
            and diff.get("oracle_kind") == (
                "deterministic-lifecycle-state-machine"
                if lifecycle_case else "synthetic-before-artifact-diff"
            )
            and diff.get("before_artifact_kind") == "synthetic-postprocess-illustration"
            and diff.get("synthetic_before_artifact_generated") is True
            and diff.get("pipeline_mutation_executed") is False
            and diff.get("gpu_submission_executed") is False
            and diff.get("lifecycle_transition_executed") is lifecycle_case
            and diff.get("lifecycle_model_rejected") is lifecycle_case
            and diff.get("lifecycle_violation") == expected_violation
            and after_matches_other_cases
            and trace.get("case") == case
            and bool(trace.get("last_good_event")) and trace.get("first_bad_event") == case
            and trace.get("capture_label")
            == f"{capture.get('pass_label')}/{capture.get('draw_label')}"
            and valid_lifecycle_defect_events(trace.get("lifecycle_events"), case)
            and capture == {
                "capture_tool": "not_embedded",
                "pass_label": "offscreen-color-depth",
                "draw_label": "shared-triangle-indexed",
                "resource_label": "generation-2",
                "cpu_trace_event": "color-depth-pass",
            }
            and validation.get("fatal") == expected_fatal
            and validation.get("classification") == expected_classification
            and validation.get("evidence_source") == (
                "static-preflight-oracle"
                if case in VALIDATION_CAUGHT_CASES
                else "synthetic-artifact-or-lifecycle-model"
            )
            and case_environment.get("backend") == "lifecycle-sim"
            and case_environment.get("actual_gpu") is False
            and case_timing.get("measurement_kind") == "cpu-wall-clock"
            and case_timing.get("is_gpu_timestamp") is False
            and all(
                type(case_timing.get(name)) is int and int(case_timing[name]) > 0
                for name in ("cpu_record_ns", "cpu_submit_ns", "submit_to_fence_ns")
            )
            and "last good stage" in report and "first bad stage" in report
            and "minimal fix" in report and "regression oracle" in report
        )
    workload_checks = []
    workloads = timing.get("workloads")
    timing_names = ("cpu_record_ns", "cpu_submit_ns", "submit_to_fence_ns")
    for workload in workloads if isinstance(workloads, list) else []:
        samples = workload.get("samples") if isinstance(workload, dict) else None
        warmup = workload.get("warmup") if isinstance(workload, dict) else None
        summary = workload.get("statistics") if isinstance(workload, dict) else None
        valid = (
            isinstance(samples, list) and len(samples) == 30
            and isinstance(warmup, list) and len(warmup) == 5
            and isinstance(summary, dict)
            and workload.get("warmup_samples") == 5 and workload.get("timed_samples") == 30
            and workload.get("environment_fingerprint_fnv1a64")
            == timing.get("environment_fingerprint_fnv1a64")
            and workload.get("correctness_hash_fnv1a64") == timing.get("correctness_hash_fnv1a64")
        )
        if valid:
            for name in timing_names:
                values = [
                    int(sample[name]) for sample in samples
                    if isinstance(sample, dict) and name in sample
                ]
                item = summary.get(name)
                valid = valid and len(values) == 30 and isinstance(item, dict)
                valid = valid and item.get("median") == sample_median(values)
                valid = valid and item.get("p95") == percentile95(values)
            valid = valid and summary["submit_to_fence_ns"].get("is_gpu_timestamp") is False
        workload_checks.append(bool(valid))
    checks = {
        "portable lifecycle environment": environment.get("backend") == "lifecycle-sim"
        and environment.get("actual_gpu") is False
        and is_hash(environment.get("environment_fingerprint_fnv1a64")),
        "frame slots, generations, zero extent, and readback": lifecycle_valid,
        "six diagnostic cases": len(case_checks) == len(DIAGNOSTIC_CASES)
        and all(case_checks)
        and semantic_cases == len(SEMANTIC_DIAGNOSTIC_CASES)
        and validation_caught_cases == len(VALIDATION_CAUGHT_CASES),
        "three timed workloads": isinstance(workloads, list)
        and {item.get("id") for item in workloads if isinstance(item, dict)}
        == {"many-small-draws", "fragment-heavy", "state-change-heavy"}
        and len(workload_checks) == 3 and all(workload_checks),
        "timing limitations": timing.get("gpu_timestamp_available") is False
        and timing.get("absolute_time_pass_threshold_ns") is None
        and "not a GPU timestamp" in str(timing.get("warning"))
        and is_hash(timing.get("environment_fingerprint_fnv1a64"))
        and is_hash(timing.get("correctness_hash_fnv1a64")),
        "validation baseline": log_has_zero_fatal(output / "validation.log"),
    }
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        raise CheckFailure(f"07-frame-debugging: independent evidence checks failed={failed}")


def flatten_grid(value: object, width: int, height: int, label: str) -> list[int]:
    if not isinstance(value, list) or len(value) != height:
        raise CheckFailure(f"{label}: wrong row count")
    flat: list[int] = []
    for row in value:
        if not isinstance(row, list) or len(row) != width or any(type(item) is not int for item in row):
            raise CheckFailure(f"{label}: wrong row shape or value type")
        flat.extend(row)
    return flat


def frame_evidence(directory: Path, renderer: str) -> dict[str, object]:
    environment = load_json(directory / "environment.json")
    depth = load_json(directory / "depth.json")
    primitive = load_json(directory / "primitive-id.json")
    trace = load_json(directory / "trace.json")
    statistics_payload = load_json(directory / "statistics.json")
    linear = read_ppm(directory / "color-linear.ppm")
    srgb = read_ppm(directory / "color-srgb.ppm")
    primitive_image = read_ppm(directory / "primitive-id.ppm")
    if not all((image.width, image.height) == (64, 64) for image in (linear, srgb, primitive_image)):
        raise CheckFailure(f"08-renderer-capstone: {renderer} image extent is not 64x64")
    depth_values = flatten_grid(depth.get("row_major_samples"), 64, 64, f"{renderer} depth")
    primitive_ids = flatten_grid(primitive.get("row_major_ids"), 64, 64, f"{renderer} primitive ids")
    if any(value not in (0, 1) for value in primitive_ids):
        raise CheckFailure(f"08-renderer-capstone: {renderer} primitive ids are outside 0..1")
    expected_primitive_rgb = b"".join(
        bytes((255, 127, 0)) if value else bytes((0, 0, 0)) for value in primitive_ids
    )
    rgba = b"".join(linear.pixels[index:index + 3] + b"\xff" for index in range(0, len(linear.pixels), 3))
    color_hash = fnv1a64(rgba)
    depth_bytes = b"".join(value.to_bytes(2, "little", signed=False) for value in depth_values)
    depth_hash_value = fnv1a64(depth_bytes)
    primitive_hash = fnv1a64(bytes(primitive_ids))
    correctness = fnv1a64(
        f"{fixture_scene_hash()}:{color_hash}:{depth_hash_value}".encode("ascii")
    )
    expected_environment = fnv1a64(
        f"{environment.get('backend')}:{environment.get('device')}:{environment.get('sdl_version')}:"
        f"{environment.get('shader_format_flags')}:{'actual' if environment.get('actual_gpu') else 'simulated'}"
        .encode("utf-8")
    )
    checks = {
        "renderer identity": statistics_payload.get("renderer") == renderer,
        "scene identity": statistics_payload.get("scene_snapshot_id") == "shared-textured-triangle-v1"
        and statistics_payload.get("scene_hash_fnv1a64") == fixture_scene_hash(),
        "linear color hash": statistics_payload.get("linear_color_hash_fnv1a64") == color_hash,
        "sRGB color hash": statistics_payload.get("srgb_color_hash_fnv1a64") == fnv1a64(srgb.pixels),
        "depth hash": depth.get("hash_fnv1a64") == depth_hash_value
        and statistics_payload.get("depth_hash_fnv1a64") == depth_hash_value,
        "primitive id hash and image": primitive.get("hash_fnv1a64") == primitive_hash
        and statistics_payload.get("primitive_id_hash_fnv1a64") == primitive_hash
        and primitive_image.pixels == expected_primitive_rgb,
        "correctness hash": statistics_payload.get("color_depth_correctness_hash_fnv1a64") == correctness,
        "environment hash": environment.get("environment_fingerprint_fnv1a64") == expected_environment
        and statistics_payload.get("environment_fingerprint_fnv1a64") == expected_environment,
        "primitive accounting": statistics_payload.get("input_primitive_count") == 1
        and statistics_payload.get("clipped_primitive_count") == 1
        and statistics_payload.get("culled_primitive_count") == 0
        and statistics_payload.get("covered_pixel_count") == sum(primitive_ids)
        and statistics_payload.get("depth_passed_pixel_count") == sum(primitive_ids),
        "trace probes": isinstance(trace.get("probes"), list) and len(trace["probes"]) == 4,
        "timing labels": statistics_payload.get("submit_to_fence_is_gpu_timestamp") is False
        and all(int(statistics_payload.get(name, 0)) > 0 for name in (
            "cpu_record_ns", "cpu_submit_ns", "submit_to_fence_ns"
        )),
    }
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        raise CheckFailure(f"08-renderer-capstone: {renderer} frame evidence failed={failed}")
    return {
        "environment": environment,
        "statistics": statistics_payload,
        "linear": linear,
        "srgb": srgb,
        "depth": depth_values,
        "primitive_ids": primitive_ids,
        "correctness_hash": correctness,
    }


def rgb_delta_metrics(
    expected: bytes,
    actual: bytes,
    edge_mask: bytes,
    interior_tolerance: int,
    edge_tolerance: int,
) -> dict[str, int]:
    metrics = {
        "raw_mismatch_pixels": 0,
        "edge_mismatch_pixels": 0,
        "interior_mismatch_pixels": 0,
        "failing_edge_pixels": 0,
        "failing_interior_pixels": 0,
        "max_abs_edge": 0,
        "max_abs_interior": 0,
    }
    for pixel, is_edge in enumerate(edge_mask):
        delta = max(abs(expected[pixel * 3 + channel] - actual[pixel * 3 + channel]) for channel in range(3))
        if delta == 0:
            continue
        metrics["raw_mismatch_pixels"] += 1
        region = "edge" if is_edge else "interior"
        metrics[f"{region}_mismatch_pixels"] += 1
        metrics[f"max_abs_{region}"] = max(metrics[f"max_abs_{region}"], delta)
        tolerance = edge_tolerance if is_edge else interior_tolerance
        if delta > tolerance:
            metrics[f"failing_{region}_pixels"] += 1
    return metrics


def validate_capstone_timing(
    timing: dict[str, object], environment_hash: object, correctness_hash: object
) -> None:
    workloads = timing.get("workloads")
    checks = {
        "actual repeated measurement": timing.get("measurement_kind")
        == "actual-repeated-offscreen-submit-fence"
        and timing.get("actual_gpu_repeated_work") is True,
        "timing limitation": timing.get("gpu_timestamp_available") is False
        and timing.get("absolute_time_pass_threshold_ns") is None
        and "not a GPU timestamp" in str(timing.get("warning")),
        "timing identities": timing.get("environment_fingerprint_fnv1a64") == environment_hash
        and timing.get("correctness_hash_fnv1a64") == correctness_hash,
        "three workloads": isinstance(workloads, list) and len(workloads) == 3
        and {item.get("id") for item in workloads if isinstance(item, dict)}
        == {"many-small-draws", "fragment-heavy", "state-change-heavy"},
    }
    for workload in workloads if isinstance(workloads, list) else []:
        if not isinstance(workload, dict):
            checks["workload object"] = False
            continue
        warmup = workload.get("warmup")
        samples = workload.get("samples")
        summary = workload.get("statistics")
        valid = (
            isinstance(workload.get("measured_scope"), str) and len(workload["measured_scope"]) > 20
            and workload.get("warmup_samples") == 5
            and workload.get("timed_samples") == 30
            and isinstance(warmup, list) and len(warmup) == 5
            and isinstance(samples, list) and len(samples) == 30
            and isinstance(summary, dict)
            and workload.get("submission_count_per_sample") == 1
            and workload.get("environment_fingerprint_fnv1a64") == environment_hash
            and workload.get("correctness_hash_fnv1a64") == correctness_hash
        )
        for name in ("cpu_record_ns", "cpu_submit_ns", "submit_to_fence_ns"):
            values = [
                item.get(name) for item in samples
                if isinstance(item, dict) and type(item.get(name)) is int and item[name] > 0
            ] if isinstance(samples, list) else []
            item = summary.get(name) if isinstance(summary, dict) else None
            valid = valid and len(values) == 30 and isinstance(item, dict)
            valid = valid and item.get("median") == sample_median(values)
            valid = valid and item.get("p95") == percentile95(values)
        valid = valid and summary["submit_to_fence_ns"].get("is_gpu_timestamp") is False
        checks[f"workload {workload.get('id')}"] = bool(valid)
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        raise CheckFailure(f"08-renderer-capstone: performance evidence failed={failed}")


def valid_capstone_lifecycle(lifecycle: dict[str, object]) -> bool:
    return valid_lifecycle_model(lifecycle, actual_gpu=True, capstone=True)


def validate_renderer_capstone_evidence(output: Path) -> None:
    conventions = load_json(output / "conventions.json")
    fixture = load_json(output / "scene_fixtures" / "manifest.json")
    comparison_directory = output / "comparison_reports"
    scene_directory = CAPSTONE_SCENE_DIRECTORY
    software = frame_evidence(output / "software_artifacts" / scene_directory, "software")
    gpu_directory = output / "gpu_artifacts" / scene_directory
    gpu = frame_evidence(gpu_directory, "sdl-gpu")
    edge_mask, expected_policy = capstone_edge_mask()
    edge_policy = load_json(comparison_directory / "edge-mask.json")
    edge_image = read_ppm(comparison_directory / "edge-mask.ppm")
    known_bad_probe = load_json(comparison_directory / "known-bad-mask-probe.json")
    known_bad_image = read_ppm(comparison_directory / "known-bad-interior.ppm")
    summary = load_json(comparison_directory / "summary.json")
    suite = load_json(output / "known-bad-suite.json")
    lifecycle = load_json(gpu_directory / "lifecycle.json")
    lifecycle_generations = lifecycle.get("generations")
    resized_image_path = gpu_directory / "resize-generation-2.ppm"
    timing = load_json(gpu_directory / "timing-report.json")
    shader = load_json(gpu_directory / "shader-manifest.json")
    static_shader = load_json(PROJECT / "shaders" / "manifest.json")
    pipeline = load_json(gpu_directory / "pipeline.json")
    resources = load_json(gpu_directory / "resources.json")
    frame_trace = load_json(gpu_directory / "frame-trace.json")
    stages = ["structure", "coverage", "depth", "attribute", "linear-color", "srgb"]
    reports = [
        load_json(comparison_directory / f"{index:02d}-{name}.json")
        for index, name in enumerate(stages, start=1)
    ]

    runtime_policy_keys = {
        "policy_id", "declared_before_gpu_readback", "construction", "radius_pixels",
        "population", "total_pixels", "maximum_fraction", "mask_hash_fnv1a64",
        "post_failure_widening_permitted", "linear_rgba8_abs_tolerance",
        "depth_u16_abs_tolerance", "srgb_interior_abs_tolerance", "srgb_edge_abs_tolerance",
    }
    policy_agrees = all(edge_policy.get(key) == expected_policy.get(key) for key in runtime_policy_keys)
    expected_mask_pixels = b"".join(bytes((255, 255, 255)) if item else bytes((0, 0, 0)) for item in edge_mask)
    linear_metrics = rgb_delta_metrics(
        software["linear"].pixels, gpu["linear"].pixels, edge_mask,
        int(expected_policy["linear_rgba8_abs_tolerance"]),
        int(expected_policy["linear_rgba8_abs_tolerance"]),
    )
    srgb_metrics = rgb_delta_metrics(
        software["srgb"].pixels, gpu["srgb"].pixels, edge_mask,
        int(expected_policy["srgb_interior_abs_tolerance"]),
        int(expected_policy["srgb_edge_abs_tolerance"]),
    )
    software_ids = software["primitive_ids"]
    gpu_ids = gpu["primitive_ids"]
    coverage_raw = sum(left != right for left, right in zip(software_ids, gpu_ids, strict=True))
    depth_deltas = [
        abs(left - right) for left, right, software_id, gpu_id in zip(
            software["depth"], gpu["depth"], software_ids, gpu_ids, strict=True
        ) if software_id and gpu_id
    ]
    depth_failures = sum(
        delta > int(expected_policy["depth_u16_abs_tolerance"]) for delta in depth_deltas
    )
    structure, coverage, depth, attribute, linear, srgb = reports
    known_bad_pixel = known_bad_probe.get("mutated_pixel")
    known_bad_index = (
        int(known_bad_pixel[1]) * 64 + int(known_bad_pixel[0])
        if isinstance(known_bad_pixel, list) and len(known_bad_pixel) == 2 else -1
    )
    known_bad_metrics = rgb_delta_metrics(
        software["linear"].pixels, known_bad_image.pixels, edge_mask,
        int(expected_policy["linear_rgba8_abs_tolerance"]),
        int(expected_policy["linear_rgba8_abs_tolerance"]),
    )

    trace_events = frame_trace.get("events")
    event_names = [item.get("event") for item in trace_events if isinstance(item, dict)] if isinstance(trace_events, list) else []
    tracked_msl_hash = fnv1a64((PROJECT / "shaders" / "triangle.metal").read_bytes())
    tracked_hlsl_hash = fnv1a64((PROJECT / "shaders" / "triangle.hlsl").read_bytes())
    checks = {
        "conventions": conventions.get("composition") == "P * V * M"
        and conventions.get("handedness") == "left" and conventions.get("ndc_depth") == "0..1"
        and conventions.get("viewport_origin") == "top-left",
        "fixture identity": fixture.get("scene_snapshot_id") == "shared-textured-triangle-v1"
        and fixture.get("deterministic_scene_hash_fnv1a64") == fixture_scene_hash()
        and fixture.get("extent") == [64, 64] and fixture.get("sample_count") == 1
        and fixture.get("random_seed") == 0 and fixture.get("primitive_count") == 1,
        "actual Metal evidence": gpu["environment"].get("actual_gpu") is True
        and gpu["environment"].get("backend") == "metal"
        and software["environment"].get("actual_gpu") is False,
        "fixed edge policy": policy_agrees and edge_image.width == edge_image.height == 64
        and edge_image.pixels == expected_mask_pixels
        and edge_policy.get("fraction") == summary.get("edge_mask_fraction")
        and edge_policy.get("population") == summary.get("edge_mask_population"),
        "ordered reports": all(
            report.get("sequence") == index and report.get("stage") == name
            and report.get("status") == "pass"
            for index, (name, report) in enumerate(zip(stages, reports, strict=True), start=1)
        ) and summary.get("ordered_stages") == stages
        and summary.get("stage_status") == {name: True for name in stages}
        and summary.get("first_difference") == "none" and summary.get("overall_status") == "pass"
        and summary.get("post_failure_widening_permitted") is False,
        "structure": structure.get("scene_hash_fnv1a64") == fixture_scene_hash()
        and structure.get("software_extent") == structure.get("gpu_extent") == [64, 64]
        and structure.get("software_primitive_count") == structure.get("gpu_primitive_count") == 1,
        "coverage": coverage_raw == 0 and coverage.get("raw_mismatch_pixels") == coverage_raw
        and coverage.get("software_covered_pixels") == sum(software_ids)
        and coverage.get("gpu_covered_pixels") == sum(gpu_ids),
        "depth": depth.get("raw_mismatch_pixels") == sum(delta != 0 for delta in depth_deltas)
        and depth.get("maximum_absolute_delta_u16") == max(depth_deltas, default=0)
        and depth_failures == 0 and depth.get("failing_edge_pixels") == 0
        and depth.get("failing_interior_pixels") == 0,
        "attribute and linear": all(linear.get(key) == value for key, value in linear_metrics.items())
        and all(attribute.get(key) == value for key, value in linear_metrics.items())
        and "UV/normal" in str(attribute.get("scope")),
        "sRGB": all(srgb.get(key) == value for key, value in srgb_metrics.items())
        and srgb_metrics["failing_edge_pixels"] == srgb_metrics["failing_interior_pixels"] == 0,
        "mask negative control": 0 <= known_bad_index < len(edge_mask)
        and edge_mask[known_bad_index] == 0 and known_bad_probe.get("edge_mask_value") is False
        and known_bad_probe.get("oracle_rejected") is True
        and known_bad_probe.get("post_failure_mask_change") is False
        and known_bad_metrics["failing_interior_pixels"] == 1,
        "known-bad registry": valid_capstone_known_bad_suite(suite)
        and set(CAPSTONE_MUTATION_METADATA)
        == set(contract("08-renderer-capstone")["known_bad_mutations"]),
        "uniform shader contract": shader.get("source_hash_fnv1a64") == tracked_msl_hash
        and static_shader.get("metal_source_hash_fnv1a64") == tracked_msl_hash
        and static_shader.get("hlsl_source_hash_fnv1a64") == tracked_hlsl_hash
        and static_shader.get("sources") == {
            "metal_runtime": "triangle.metal", "portable_offline": "triangle.hlsl"
        }
        and shader.get("vertex_uniform_buffer_count") == pipeline.get("vertex_uniform_buffer_count") == 1
        and shader.get("uniform_bindings") == {
            "msl_vertex": "buffer(0)", "hlsl_vertex": "register(b0, space1)"
        }
        and pipeline.get("vertex_uniform_push_slot") == resources.get("uniform_push", {}).get("slot") == 0
        and pipeline.get("vertex_uniform_bytes") == resources.get("uniform_push", {}).get("bytes") == 80,
        "GPU frame trace": event_names == [
            "push-vertex-uniform", "upload-vertex-index", "color-depth-pass",
            "download-recorded", "fence-complete", "readback-mapped",
        ] and frame_trace.get("submit_to_fence_is_gpu_timestamp") is False,
        "actual GPU lifecycle probe": valid_actual_gpu_probe(
            resources.get("actual_gpu_resize_probe"), gpu["environment"]
        ),
        "lifecycle": valid_capstone_lifecycle(lifecycle)
        and isinstance(lifecycle_generations, list) and len(lifecycle_generations) == 2
        and lifecycle_generations[0].get("correctness_hash_fnv1a64") == gpu["correctness_hash"]
        and lifecycle_generations[1].get("correctness_hash_fnv1a64")
        == resize_clear_correctness_hash(resized_image_path),
        "summary identities": summary.get("scene_hash_fnv1a64") == fixture_scene_hash()
        and summary.get("software_correctness_hash_fnv1a64") == software["correctness_hash"]
        and summary.get("gpu_correctness_hash_fnv1a64") == gpu["correctness_hash"]
        and summary.get("environment_fingerprint_fnv1a64")
        == gpu["environment"].get("environment_fingerprint_fnv1a64"),
        "validation": log_has_zero_fatal(output / "validation.log")
        and log_has_zero_fatal(gpu_directory / "validation.log"),
        "human reports": all((output / name).is_file() for name in (
            "correctness.md", "debugging.md", "performance.md", "next-open-source-entry.md"
        )) and "not GPU-consumed" in (output / "correctness.md").read_text(encoding="utf-8")
        and "not a GPU timestamp" in (output / "performance.md").read_text(encoding="utf-8"),
    }
    failed = [label for label, passed in checks.items() if not passed]
    if failed:
        raise CheckFailure(f"08-renderer-capstone: independent evidence checks failed={failed}")
    validate_capstone_timing(
        timing,
        gpu["environment"].get("environment_fingerprint_fnv1a64"),
        gpu["correctness_hash"],
    )


def validate_public_evidence(stage: str, output: Path) -> None:
    validate_required_artifacts(stage, output)
    if stage == "01-transform-trace":
        validate_transform_evidence(output)
    elif stage == "02-sampling-and-color":
        validate_sampling_evidence(output)
    elif stage == "03-triangle-coverage":
        validate_coverage_evidence(output)
    elif stage == "04-perspective-depth-blend":
        validate_perspective_evidence(output)
    elif stage == "05-textured-lit-scene":
        validate_lit_scene_evidence(output)
    elif stage == "06-gpu-first-frame":
        validate_gpu_first_frame_evidence(output)
    elif stage == "07-frame-debugging":
        validate_frame_debugging_evidence(output)
    elif stage == "08-renderer-capstone":
        validate_renderer_capstone_evidence(output)


def run(command: list[str], *, timeout: int = 300, expected: set[int] = {0}) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    if result.returncode not in expected:
        raise CommandFailure(result, command, expected)
    return result


def contract(stage: str) -> dict[str, object]:
    path = ROOT / "exercises" / stage / "contract.json"
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
        parse_constant=reject_nonfinite_json_constant,
    )
    if not isinstance(payload, dict):
        raise CheckFailure(f"exercise contract root must be an object: {path}")
    if payload.get("id") != stage or payload.get("schema_version") != 1:
        raise CheckFailure(f"invalid exercise contract identity: {path}")
    return payload


def configure_and_build(implementation: str, gpu: str) -> Path:
    build = ROOT / "build" / f"check-{implementation}-{gpu}"
    command = [
        "cmake", "-S", str(PROJECT), "-B", str(build),
        f"-DCG_IMPLEMENTATION={implementation}", f"-DCG_GPU={gpu}",
        "-DCMAKE_BUILD_TYPE=Debug",
    ]
    run(command)
    run(["cmake", "--build", str(build), "--parallel", "4"])
    executable = build / "cg-render"
    if not executable.is_file():
        raise CheckFailure(f"build did not produce {executable}")
    return executable


def validate_run(stage: str, output: Path, expected: str, mutation: str | None) -> None:
    if not output.is_dir() or output.is_symlink():
        raise CheckFailure(f"{stage}: output root is missing or linked")
    try:
        output.resolve(strict=True).relative_to((ROOT / "out").resolve())
    except ValueError as error:
        raise CheckFailure(f"{stage}: output root escaped the checker artifact directory") from error
    path = output / "run.json"
    if not path.is_file() or path.is_symlink():
        raise CheckFailure(f"{stage}: run.json was not produced")
    payload = load_json(path)
    required = {"schema_version", "stage", "scene", "backend", "status", "invariants", "mutation"}
    if set(payload) != required:
        raise CheckFailure(
            f"{stage}: run.json fields are not closed: {sorted(set(payload) ^ required)}"
        )
    if payload["schema_version"] != 1 or payload["stage"] != stage:
        raise CheckFailure(f"{stage}: run identity mismatch")
    if payload["scene"] != SCENES[stage]:
        raise CheckFailure(f"{stage}: run scene mismatch: {payload['scene']!r}")
    allowed_backends = (
        {"software"} if stage.startswith(("01-", "02-", "03-", "04-", "05-"))
        else {"lifecycle-sim"} if stage == "07-frame-debugging"
        else {"sdl-gpu", "lifecycle-sim"}
    )
    if payload["backend"] not in allowed_backends:
        raise CheckFailure(f"{stage}: unexpected backend evidence: {payload['backend']!r}")
    invariants = payload["invariants"]
    if not isinstance(invariants, dict):
        raise CheckFailure(f"{stage}: invariants must be an object")
    expected_ids = set(contract(stage)["invariants"])
    if set(invariants) != expected_ids:
        raise CheckFailure(
            f"{stage}: invariant registry mismatch missing={sorted(expected_ids - set(invariants))} "
            f"extra={sorted(set(invariants) - expected_ids)}"
        )
    if any(type(value) is not bool for value in invariants.values()):
        raise CheckFailure(f"{stage}: invariant values must be booleans")
    if expected == "pass":
        if payload["status"] != "pass" or payload["mutation"] is not None or not all(invariants.values()):
            raise CheckFailure(f"{stage}: pass artifact contains failed evidence")
    elif expected == "fail":
        if payload["status"] != "fail" or payload["mutation"] != mutation or all(invariants.values()):
            raise CheckFailure(f"{stage}: mutation was not exposed by evidence")
        if mutation not in contract(stage)["known_bad_mutations"]:
            raise CheckFailure(f"{stage}: undeclared mutation evidence: {mutation!r}")
        if stage in GPU_STAGES or stage == "07-frame-debugging":
            if mutation is None:
                raise CheckFailure(f"{stage}: mutation identity is missing")
            validate_gpu_mutation_evidence(stage, output, mutation)
        elif stage in {
            "03-triangle-coverage", "04-perspective-depth-blend", "05-textured-lit-scene",
        }:
            if mutation is None:
                raise CheckFailure(f"{stage}: mutation identity is missing")
            validate_cpu_mutation_evidence(stage, output, mutation)


def backend_for(stage: str, gpu: str) -> str:
    if stage == "07-frame-debugging":
        return "lifecycle-sim"
    if stage in GPU_STAGES:
        return "sdl-gpu" if gpu != "off" else "lifecycle-sim"
    return "software"


def exercise_command(
    executable: Path,
    stage: str,
    output: Path,
    gpu: str,
    mutation: str | None,
) -> list[str]:
    command = [
        str(executable), "--stage", stage, "--scene", SCENES[stage],
        "--backend", backend_for(stage, gpu), "--out", str(output), "--frames", "3",
    ]
    if mutation:
        command += ["--mutation", mutation]
    return command


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and verify a computer-graphics exercise implementation.")
    parser.add_argument("--impl", choices=("reference", "starter", "workspace"), required=True)
    parser.add_argument("--stage", choices=(*STAGES, "all"), required=True)
    parser.add_argument("--expect", choices=("pass", "not-implemented", "fail"), required=True)
    parser.add_argument("--gpu", choices=("auto", "required", "off"), required=True)
    parser.add_argument("--mutation")
    args = parser.parse_args()
    if args.expect == "fail" and not args.mutation:
        parser.error("--expect fail requires --mutation")
    if args.expect != "fail" and args.mutation:
        parser.error("--mutation is only valid with --expect fail")
    if args.mutation and args.stage == "all":
        parser.error("a mutation check must select one stage")
    if args.impl == "workspace" and not (PROJECT / "workspace").is_dir():
        raise CheckFailure("workspace is missing; run scripts/new-workspace.sh")

    validate_expected_manifest()

    executable = configure_and_build(args.impl, args.gpu)
    selected = STAGES if args.stage == "all" else [args.stage]
    artifact_root = ROOT / "out/checker" / f"{int(time.time())}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    artifact_root.mkdir(parents=True, exist_ok=False)
    skipped_gpu: list[str] = []

    for stage in selected:
        output = artifact_root / stage
        command = exercise_command(executable, stage, output, args.gpu, args.mutation)
        if args.expect == "not-implemented":
            run(command, expected={3})
            if output.exists() or output.is_symlink():
                raise CheckFailure(f"{stage}: not-implemented starter created an output path")
            print(f"[PASS] {stage}: explicit not-implemented")
            continue
        if args.gpu == "off" and stage in GPU_STAGES and args.expect == "pass":
            skipped_gpu.append(stage)
            print(f"[GPU_NOT_EVALUATED] {stage}: --gpu off")
            continue
        allowed = {0} if args.expect == "pass" else {4}
        try:
            result = run(command, expected=allowed)
        except CommandFailure as error:
            if args.gpu == "auto" and stage in GPU_STAGES and error.returncode == 5:
                skipped_gpu.append(stage)
                print(f"[GPU_NOT_EVALUATED] {stage}: runtime unsupported")
                continue
            raise
        validate_run(stage, output, args.expect, args.mutation)
        if args.expect == "pass":
            validate_public_evidence(stage, output)
        print(f"[PASS] {stage}: behavior and artifact contract ({result.returncode})")

    if args.gpu == "required" and skipped_gpu:
        raise CheckFailure(f"required GPU stages were not evaluated: {skipped_gpu}")
    print(f"CHECK_OK impl={args.impl} stages={len(selected)} gpu={args.gpu} artifacts={artifact_root}")
    if skipped_gpu:
        print(f"GPU_EXIT_CAPABILITY_NOT_EVALUATED stages={','.join(skipped_gpu)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        CheckFailure,
        subprocess.TimeoutExpired,
        OSError,
        AttributeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        print(f"CHECK_ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
