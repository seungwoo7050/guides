#!/usr/bin/env python3
"""프로세서 모델의 미완성·기준 구현과 명령행 동작을 검사합니다."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable
COMMAND_TIMEOUT_SECONDS = 30


def run(*args: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            list(args),
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        print(f"명령 시간 초과({COMMAND_TIMEOUT_SECONDS}초): {' '.join(args)}", file=sys.stderr)
        raise SystemExit(1) from exc
    if completed.returncode != expect:
        print(f"명령 실패: {' '.join(args)}", file=sys.stderr)
        print(completed.stdout, file=sys.stderr)
        print(completed.stderr, file=sys.stderr)
        raise SystemExit(1)
    return completed


def json_command(*args: str) -> dict:
    completed = run(PYTHON, "reference/processor-model.py", *args)
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        print(completed.stdout, file=sys.stderr)
        raise SystemExit(f"JSON 출력을 읽지 못했습니다: {exc}") from exc


def require_exact(label: str, actual: object, expected: object) -> None:
    if actual != expected:
        print(f"{label} 결과가 고정 fixture와 다릅니다.", file=sys.stderr)
        print(json.dumps({"expected": expected, "actual": actual}, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)


def check_skeleton() -> int:
    run(PYTHON, "-m", "compileall", "-q", "skeleton")
    run(PYTHON, "skeleton/processor-model.py", "--help")
    incomplete = run(
        PYTHON,
        "skeleton/processor-model.py",
        "bits",
        "int",
        "-1",
        "--width",
        "8",
        expect=2,
    )
    expected = "processor-model: TODO: represent_integer"
    if expected not in incomplete.stderr:
        print(incomplete.stdout, file=sys.stderr)
        print(incomplete.stderr, file=sys.stderr)
        raise SystemExit(
            "미완성 구현이 지정하지 않은 이유로 실패했습니다"
        )
    print("processor-model: represent_integer의 예상 미구현 실패를 확인했습니다")
    return 0


def check_reference() -> int:
    run(PYTHON, "-m", "compileall", "-q", "skeleton", "reference", "tests")
    run(
        "env",
        "EXERCISE_IMPL=reference",
        PYTHON,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-v",
    )

    integer = json_command("bits", "int", "-1", "--width", "8")
    require_exact(
        "bits",
        integer,
        {
            "input": -1,
            "width": 8,
            "unsigned": 255,
            "signed": -1,
            "binary": "11111111",
            "hex": "0xff",
            "big_endian_bytes": ["0xff"],
            "little_endian_bytes": ["0xff"],
            "truncated": False,
        },
    )

    program = json_command("isa", "fixtures/programs/sum.asm", "--max-steps", "100")
    require_exact(
        "sum.asm",
        program,
        {
            "halted": True,
            "steps": 20,
            "pc": 8,
            "registers": {"r0": 0, "r1": 0, "r2": 15, "r3": 15, "r4": 0, "r5": 0, "r6": 0, "r7": 0},
            "nonzero_memory_words": {"0": 15},
        },
    )
    overflow = json_command("isa", "fixtures/programs/overflow.asm", "--max-steps", "100")
    require_exact(
        "overflow.asm",
        overflow,
        {
            "halted": True,
            "steps": 4,
            "pc": 4,
            "registers": {"r0": 0, "r1": -2147483648, "r2": 0, "r3": 0, "r4": 0, "r5": 0, "r6": 0, "r7": 0},
            "nonzero_memory_words": {},
        },
    )

    pipe = json_command(
        "pipeline",
        "fixtures/traces/pipeline-load-use.trace",
        "--forwarding",
        "full",
        "--json",
    )
    require_exact(
        "pipeline-load-use.trace summary",
        {key: value for key, value in pipe.items() if key != "timeline"},
        {"cycles": 9, "retired": 3, "data_stalls": 1, "control_stalls": 0, "flushes": 0, "cpi": 3.0},
    )
    require_exact(
        "pipeline-load-use.trace instructions",
        [entry["instruction"] for entry in pipe["timeline"]],
        ["I0: lw r1, 0(r0)", "I1: add r2, r1, r3", "I2: sub r4, r2, r5"],
    )
    branch_pipe = json_command(
        "pipeline",
        "fixtures/traces/pipeline-branch.trace",
        "--forwarding",
        "full",
        "--json",
    )
    require_exact(
        "pipeline-branch.trace summary",
        {key: value for key, value in branch_pipe.items() if key != "timeline"},
        {"cycles": 12, "retired": 3, "data_stalls": 0, "control_stalls": 2, "flushes": 2, "cpi": 4.0},
    )
    require_exact(
        "pipeline-branch.trace flushed stages",
        [(entry["instruction"], entry.get("5")) for entry in branch_pipe["timeline"]],
        [
            ("I0: li r1, 1", "MEM"),
            ("I1: beq r1, r1, target", "EX"),
            ("I2: addi r4, r0, 99", "ID*"),
            ("I3: addi r5, r0, 88", "IF*"),
            ("I4: addi r4, r0, 7", "."),
        ],
    )

    cache = json_command(
        "cache",
        "fixtures/traces/cache.trace",
        "--size",
        "16",
        "--block",
        "4",
        "--ways",
        "1",
    )
    require_exact(
        "cache.trace summary",
        {key: value for key, value in cache.items() if key != "events"},
        {
            "configuration": {
                "size_bytes": 16,
                "block_size": 4,
                "associativity": 1,
                "sets": 4,
                "lines": 4,
                "write_allocate": True,
                "replacement": "LRU",
                "write_policy": "write-back",
            },
            "accesses": 10,
            "reads": 9,
            "writes": 1,
            "hits": 1,
            "misses": 9,
            "hit_rate": 0.1,
            "miss_rate": 0.9,
            "compulsory_misses": 5,
            "conflict_misses": 2,
            "capacity_misses": 2,
            "writebacks": 1,
            "memory_writes": 1,
        },
    )

    translated = json_command("vm", "fixtures/vm/config.json", "fixtures/vm/trace.txt")
    require_exact(
        "vm trace summary",
        {key: value for key, value in translated.items() if key != "events"},
        {
            "configuration": {"page_size": 4096, "tlb_entries": 2, "tlb_replacement": "LRU"},
            "translations": 7,
            "tlb_hits": 1,
            "tlb_misses": 6,
            "tlb_hit_rate": 1 / 7,
            "page_table_walks": 6,
            "page_faults": 2,
            "protection_faults": 1,
            "tlb_invalidations": 2,
        },
    )

    coherent = json_command(
        "coherence",
        "fixtures/traces/coherence-false-sharing.trace",
        "--cores",
        "2",
        "--line-size",
        "64",
    )
    require_exact(
        "coherence trace summary",
        {key: value for key, value in coherent.items() if key != "events"},
        {
            "configuration": {"cores": 2, "line_size": 64},
            "accesses": 4,
            "hits": 0,
            "misses": 4,
            "hit_rate": 0.0,
            "bus_reads": 1,
            "bus_read_exclusive": 3,
            "bus_upgrades": 0,
            "invalidations": 2,
            "writebacks": 3,
            "final_states": {"0": ["S", "S"]},
        },
    )

    print("processor-model: 기준 구현의 단위 검사와 CLI 검사를 통과했습니다")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--skeleton", action="store_true")
    mode.add_argument("--reference", action="store_true")
    args = parser.parse_args()
    if args.skeleton:
        return check_skeleton()
    return check_reference()


if __name__ == "__main__":
    raise SystemExit(main())
