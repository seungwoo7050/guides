#!/usr/bin/env python3
"""Small dependency-free PPM comparator for deterministic guide fixtures.

Supports 8-bit P3 and P6 PPM files. This is intentionally not a perceptual
metric or an HDR image tool. It reports exact channel/pixel differences for
small educational artifacts.
"""
from __future__ import annotations

import argparse
import json
import math
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class PPMImage:
    width: int
    height: int
    maxval: int
    pixels: bytes  # RGB interleaved, one byte per channel


def _skip_space_and_comments(data: bytes, index: int) -> int:
    n = len(data)
    while index < n:
        if data[index] in b" \t\r\n\f\v":
            index += 1
            continue
        if data[index] == ord("#"):
            newline = data.find(b"\n", index)
            if newline < 0:
                return n
            index = newline + 1
            continue
        return index
    return index


def _read_token(data: bytes, index: int) -> tuple[bytes, int]:
    index = _skip_space_and_comments(data, index)
    start = index
    while index < len(data) and data[index] not in b" \t\r\n\f\v#":
        index += 1
    if start == index:
        raise ValueError("PPM header token is missing")
    return data[start:index], index


def read_ppm(path: Path) -> PPMImage:
    data = path.read_bytes()
    index = 0
    magic, index = _read_token(data, index)
    if magic not in (b"P3", b"P6"):
        raise ValueError(f"{path}: unsupported PPM magic {magic!r}; expected P3 or P6")
    width_b, index = _read_token(data, index)
    height_b, index = _read_token(data, index)
    maxval_b, index = _read_token(data, index)
    try:
        width = int(width_b)
        height = int(height_b)
        maxval = int(maxval_b)
    except ValueError as exc:
        raise ValueError(f"{path}: non-integer PPM header") from exc
    if width <= 0 or height <= 0:
        raise ValueError(f"{path}: width and height must be positive")
    if not 1 <= maxval <= 255:
        raise ValueError(f"{path}: only 8-bit PPM maxval 1..255 is supported")
    expected = width * height * 3

    if magic == b"P3":
        values: list[int] = []
        while len(values) < expected:
            token, index = _read_token(data, index)
            try:
                value = int(token)
            except ValueError as exc:
                raise ValueError(f"{path}: invalid P3 channel {token!r}") from exc
            if not 0 <= value <= maxval:
                raise ValueError(f"{path}: channel {value} outside 0..{maxval}")
            values.append(round(value * 255 / maxval))
        if _skip_space_and_comments(data, index) != len(data):
            raise ValueError(f"{path}: extra P3 data after expected pixels")
        return PPMImage(width, height, 255, bytes(values))

    # P6 has one whitespace separator after maxval. Treat CRLF as one newline.
    if index >= len(data) or data[index] not in b" \t\r\n\f\v":
        raise ValueError(f"{path}: missing whitespace before P6 raster")
    if data[index:index + 2] == b"\r\n":
        index += 2
    else:
        index += 1
    raster = data[index:]
    if len(raster) != expected:
        raise ValueError(f"{path}: expected {expected} raster bytes, got {len(raster)}")
    if maxval == 255:
        pixels = raster
    else:
        pixels = bytes(round(v * 255 / maxval) for v in raster)
    return PPMImage(width, height, 255, pixels)


def write_p6(path: Path, width: int, height: int, pixels: bytes) -> None:
    if len(pixels) != width * height * 3:
        raise ValueError("pixel byte count does not match extent")
    path.write_bytes(f"P6\n{width} {height}\n255\n".encode("ascii") + pixels)


def compare(reference: PPMImage, actual: PPMImage) -> dict[str, object]:
    if (reference.width, reference.height) != (actual.width, actual.height):
        return {
            "comparable": False,
            "reason": "extent_mismatch",
            "reference_extent": [reference.width, reference.height],
            "actual_extent": [actual.width, actual.height],
        }
    channel_diffs = [abs(a - b) for a, b in zip(reference.pixels, actual.pixels)]
    pixel_diffs = [max(channel_diffs[i:i + 3]) for i in range(0, len(channel_diffs), 3)]
    changed = [i for i, value in enumerate(pixel_diffs) if value != 0]
    worst = sorted(changed, key=lambda i: pixel_diffs[i], reverse=True)[:10]
    width = reference.width
    return {
        "comparable": True,
        "extent": [reference.width, reference.height],
        "channel_count": len(channel_diffs),
        "pixel_count": len(pixel_diffs),
        "max_abs_channel": max(channel_diffs, default=0),
        "mean_abs_channel": (sum(channel_diffs) / len(channel_diffs)) if channel_diffs else 0.0,
        "changed_pixels": len(changed),
        "changed_fraction": (len(changed) / len(pixel_diffs)) if pixel_diffs else 0.0,
        "worst_pixels": [
            {
                "x": i % width,
                "y": i // width,
                "max_abs_channel": pixel_diffs[i],
                "reference_rgb": list(reference.pixels[i * 3:i * 3 + 3]),
                "actual_rgb": list(actual.pixels[i * 3:i * 3 + 3]),
            }
            for i in worst
        ],
    }


def evaluate(report: dict[str, object], max_abs: int, max_changed_pixels: int) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not report.get("comparable"):
        reasons.append(str(report.get("reason", "not_comparable")))
        return False, reasons
    if int(report["max_abs_channel"]) > max_abs:
        reasons.append(f"max_abs_channel={report['max_abs_channel']} > {max_abs}")
    if int(report["changed_pixels"]) > max_changed_pixels:
        reasons.append(f"changed_pixels={report['changed_pixels']} > {max_changed_pixels}")
    return not reasons, reasons


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="cg-ppm-diff-") as raw:
        directory = Path(raw)
        base = bytes([
            255, 0, 0,   0, 255, 0,
            0, 0, 255,   255, 255, 255,
        ])
        changed = bytearray(base)
        changed[0] = 253
        p_ref = directory / "ref.ppm"
        p_same = directory / "same.ppm"
        p_changed = directory / "changed.ppm"
        write_p6(p_ref, 2, 2, base)
        write_p6(p_same, 2, 2, base)
        write_p6(p_changed, 2, 2, bytes(changed))

        exact = compare(read_ppm(p_ref), read_ppm(p_same))
        ok, reasons = evaluate(exact, 0, 0)
        if not ok:
            raise AssertionError(f"equal image failed: {reasons}")

        mutation = compare(read_ppm(p_ref), read_ppm(p_changed))
        ok, _ = evaluate(mutation, 0, 0)
        if ok:
            raise AssertionError("one-channel mutation was not rejected")
        ok, reasons = evaluate(mutation, 2, 1)
        if not ok:
            raise AssertionError(f"documented tolerance did not pass: {reasons}")

        # P3 parser and comments.
        p3 = directory / "ascii.ppm"
        p3.write_text("P3\n# marker\n2 1\n255\n255 0 0  0 255 0\n", encoding="ascii")
        image = read_ppm(p3)
        if image.pixels != bytes([255, 0, 0, 0, 255, 0]):
            raise AssertionError("P3 parser produced wrong pixels")
    print("PPM_DIFF_SELF_TEST_OK")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", nargs="?", type=Path)
    parser.add_argument("actual", nargs="?", type=Path)
    parser.add_argument("--max-abs", type=int, default=0, help="maximum absolute 8-bit channel difference")
    parser.add_argument("--max-changed-pixels", type=int, default=0)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--self-test", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.reference is None or args.actual is None:
        raise SystemExit("reference and actual PPM paths are required unless --self-test is used")
    if args.max_abs < 0 or args.max_changed_pixels < 0:
        raise SystemExit("thresholds must be non-negative")
    try:
        result = compare(read_ppm(args.reference), read_ppm(args.actual))
    except (OSError, ValueError) as exc:
        print(json.dumps({"pass": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    passed, reasons = evaluate(result, args.max_abs, args.max_changed_pixels)
    output = {
        "reference": str(args.reference),
        "actual": str(args.actual),
        "thresholds": {"max_abs": args.max_abs, "max_changed_pixels": args.max_changed_pixels},
        "pass": passed,
        "failure_reasons": reasons,
        "metrics": result,
    }
    encoded = json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    print(encoded, end="")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
