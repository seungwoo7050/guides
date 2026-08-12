#!/usr/bin/env python3
"""구조 validator가 대표 결함을 실제로 거부하는지 검사합니다."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[1]


def copy_source(destination: Path) -> None:
    shutil.copytree(
        SOURCE,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            ".git", ".guide", "workspace", "build", "__pycache__", "*.pyc"
        ),
    )


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["GUIDE_ROOT"] = str(root)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        ["python3", str(root / "scripts/validate_docs.py")],
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )


def require_rejection(name: str, mutate, needle: str) -> None:
    with tempfile.TemporaryDirectory(prefix="guide-architecture-validator-") as temporary:
        root = Path(temporary) / "repo"
        copy_source(root)
        mutate(root)
        completed = validate(root)
        output = completed.stdout + completed.stderr
        if completed.returncode == 0 or needle not in output:
            raise AssertionError(
                f"{name} mutant를 지정된 계약에서 거부하지 못했습니다.\n{output}"
            )
        print(f"[PASS] validator rejects {name}")


def replace(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise AssertionError(f"mutant 기준 문자열이 없습니다: {path} -> {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def copy_section(root: Path, source_relative: str, target_relative: str, heading: str) -> None:
    marker = f"## {heading}\n"

    def body(text: str) -> tuple[int, int]:
        start = text.index(marker) + len(marker)
        end = text.find("\n## ", start)
        return start, len(text) if end < 0 else end + 1

    source = (root / source_relative).read_text(encoding="utf-8")
    target_path = root / target_relative
    target = target_path.read_text(encoding="utf-8")
    source_start, source_end = body(source)
    target_start, target_end = body(target)
    target_path.write_text(
        target[:target_start] + source[source_start:source_end] + target[target_end:],
        encoding="utf-8",
    )


def main() -> int:
    baseline = validate(SOURCE)
    if baseline.returncode != 0:
        raise AssertionError("validator 기준본이 실패했습니다.\n" + baseline.stdout + baseline.stderr)

    require_rejection(
        "missing-document",
        lambda root: (root / "docs/00-roadmap.md").unlink(),
        "필수 파일을 찾을 수 없습니다",
    )
    require_rejection(
        "unexpected-path",
        lambda root: (root / "unexpected-guide.txt").write_text("unexpected\n", encoding="utf-8"),
        "예상 밖 최상위 경로",
    )
    require_rejection(
        "broken-link",
        lambda root: replace(
            root / "docs/01-representation-and-isa/01-data-representation-and-arithmetic.md",
            "../../exercises/processor-model/README.md",
            "../../exercises/missing/README.md",
        ),
        "대상이 없는 링크",
    )
    require_rejection(
        "broken-inline-code-label-link",
        lambda root: replace(
            root / "docs/02-in-order-execution/04-datapath-and-control.md",
            "../../exercises/processor-model/README.md",
            "../../exercises/missing/README.md",
        ),
        "대상이 없는 링크",
    )
    require_rejection(
        "ordered-mapping-document-drift",
        lambda root: replace(
            root / "README.md",
            "| 01 | [데이터 표현과 산술](docs/01-representation-and-isa/01-data-representation-and-arithmetic.md) | — |",
            "| 01 | [데이터 표현과 산술](docs/01-representation-and-isa/02-isa-assembly-and-program-execution.md) | — |",
        ),
        "README 학습 순서의 문서 대응",
    )
    require_rejection(
        "ordered-mapping-example-drift",
        lambda root: replace(
            root / "README.md",
            "| 03 | [성능식과 측정](docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md) | [데이터 배치](examples/layout-benchmark/README.md) |",
            "| 03 | [성능식과 측정](docs/01-representation-and-isa/03-performance-cpi-and-amdahl.md) | [분기 벤치마크](examples/branch-benchmark/README.md) |",
        ),
        "README 학습 순서의 관찰 예제 대응",
    )
    require_rejection(
        "ordered-mapping-non-example-observation",
        lambda root: replace(
            root / "README.md",
            "| 01 | [데이터 표현과 산술](docs/01-representation-and-isa/01-data-representation-and-arithmetic.md) | — |",
            "| 01 | [데이터 표현과 산술](docs/01-representation-and-isa/01-data-representation-and-arithmetic.md) | [빠른 참조](reference/formulas-and-checklist.md) |",
        ),
        "README 학습 순서의 관찰 예제 대응",
    )
    require_rejection(
        "ordered-mapping-exercise-column-drift",
        lambda root: replace(
            root / "README.md",
            "[`processor-model` Stage 01](exercises/processor-model/README.md) 고정 폭 산술 | `exercises/processor-model/workspace/processor_model/bits.py`",
            "고정 폭 산술 | `exercises/processor-model/workspace/processor_model/bits.py`",
        ),
        "직접 수행에 processor-model 연결이 없습니다",
    )
    require_rejection(
        "ordered-mapping-stage-file-drift",
        lambda root: replace(
            root / "README.md",
            "`exercises/processor-model/workspace/processor_model/bits.py`",
            "`exercises/processor-model/workspace/processor_model/coherence.py`",
        ),
        "수정 위치가 canonical workspace가 아닙니다",
    )
    require_rejection(
        "ordered-mapping-separator-drift",
        lambda root: replace(
            root / "README.md",
            "|---:|---|---|---|---|---|---|",
            "이 줄은 Markdown table separator가 아닙니다.",
        ),
        "separator가 올바르지 않습니다",
    )
    require_rejection(
        "roadmap-mapping-example-drift",
        lambda root: replace(
            root / "docs/00-roadmap.md",
            "| 03 | [성능식](01-representation-and-isa/03-performance-cpi-and-amdahl.md) | [데이터 배치](../examples/layout-benchmark/README.md) |",
            "| 03 | [성능식](01-representation-and-isa/03-performance-cpi-and-amdahl.md) | [분기 벤치마크](../examples/branch-benchmark/README.md) |",
        ),
        "roadmap 학습 순서의 관찰 예제 대응",
    )
    require_rejection(
        "roadmap-mapping-command-drift",
        lambda root: replace(
            root / "docs/00-roadmap.md",
            "`make stage-01 EXERCISE_IMPL=workspace`",
            "`make stage-10 EXERCISE_IMPL=workspace`",
        ),
        "roadmap 학습 순서의 Stage 01 검증 명령이 다릅니다",
    )
    require_rejection(
        "learner-command-targets-skeleton",
        lambda root: replace(
            root / "docs/01-representation-and-isa/01-data-representation-and-arithmetic.md",
            "make stage-01 EXERCISE_IMPL=workspace",
            "make stage-01 EXERCISE_IMPL=skeleton",
        ),
        "repository-owned skeleton",
    )
    require_rejection(
        "root-command-targets-skeleton",
        lambda root: (root / "README.md").write_text(
            (root / "README.md").read_text(encoding="utf-8")
            + "\n```sh\nmake stage-01 EXERCISE_IMPL=skeleton\n```\n",
            encoding="utf-8",
        ),
        "repository-owned skeleton",
    )
    require_rejection(
        "quoted-command-targets-skeleton",
        lambda root: (root / "README.md").write_text(
            (root / "README.md").read_text(encoding="utf-8")
            + "\n```sh\nmake stage-01 EXERCISE_IMPL = \"skeleton\"\n```\n",
            encoding="utf-8",
        ),
        "repository-owned skeleton",
    )
    require_rejection(
        "skeleton-entrypoint-command",
        lambda root: (root / "exercises/processor-model/README.md").write_text(
            (root / "exercises/processor-model/README.md").read_text(encoding="utf-8")
            + "\n```sh\npython3 skeleton/processor-model.py bits int 1 --width 8\n```\n",
            encoding="utf-8",
        ),
        "repository-owned skeleton",
    )

    def append_annotation(root: Path, relative: str, identifier: str, syntax: str = "python") -> None:
        path = root / relative
        marker = "[" + f"Implementation {identifier}]"
        if syntax == "c":
            line = f"/* {marker} validator mutant용 한글 설명입니다. */\n"
        else:
            line = f"# {marker} validator mutant용 한글 설명입니다.\n"
        path.write_text(path.read_text(encoding="utf-8") + "\n" + line, encoding="utf-8")

    require_rejection(
        "annotation-in-skeleton",
        lambda root: append_annotation(
            root,
            "exercises/processor-model/skeleton/processor_model/bits.py",
            "1",
        ),
        "허용되지 않은 Implementation annotation 위치",
    )
    require_rejection(
        "duplicate-annotation",
        lambda root: append_annotation(
            root,
            "examples/layout-benchmark/layout_benchmark.c",
            "1",
            "c",
        ),
        "중복된 Implementation annotation",
    )
    require_rejection(
        "annotation-numbering-gap",
        lambda root: replace(
            root / "examples/layout-benchmark/layout_benchmark.c",
            "[" + "Implementation 1]",
            "[" + "Implementation 99]",
        ),
        "Implementation top-level 번호가 연속하지 않습니다",
    )
    require_rejection(
        "annotation-index-target-drift",
        lambda root: replace(
            root / "exercises/processor-model/README.md",
            "`bits.py::_validate_width`",
            "`isa.py::_validate_width`",
        ),
        "README index 위치와 source anchor가 다릅니다",
    )
    require_rejection(
        "annotation-index-lookalike-file",
        lambda root: replace(
            root / "exercises/processor-model/README.md",
            "`bits.py::_validate_width`",
            "`wrong-bits.py::_validate_width`",
        ),
        "README index 위치와 source anchor가 다릅니다",
    )
    require_rejection(
        "annotation-index-lookalike-symbol",
        lambda root: replace(
            root / "exercises/processor-model/README.md",
            "`bits.py::_validate_width`",
            "`bits.py::validate_width`",
        ),
        "README index 위치와 source anchor가 다릅니다",
    )
    require_rejection(
        "annotation-index-wrong-class",
        lambda root: replace(
            root / "exercises/processor-model/README.md",
            "`cache.py::CacheSimulator.access`",
            "`cache.py::Line.access`",
        ),
        "README index 위치와 source anchor가 다릅니다",
    )
    require_rejection(
        "annotation-index-c-call-lookalike",
        lambda root: replace(
            root / "examples/false-sharing/README.md",
            "`false_sharing.c::run_worker`",
            "`false_sharing.c::gate_wait`",
        ),
        "README index 위치와 source anchor가 다릅니다",
    )
    require_rejection(
        "annotation-index-later-make-target",
        lambda root: replace(
            root / "examples/vectorization-report/README.md",
            "`Makefile::$(TARGET)`",
            "`Makefile::check`",
        ),
        "README index 위치와 source anchor가 다릅니다",
    )
    require_rejection(
        "annotation-index-python-file-only",
        lambda root: replace(
            root / "exercises/processor-model/README.md",
            "`bits.py::_validate_width`",
            "`bits.py`",
        ),
        "README index 위치와 source anchor가 다릅니다",
    )
    require_rejection(
        "annotation-index-c-file-only",
        lambda root: replace(
            root / "examples/layout-benchmark/README.md",
            "`layout_benchmark.c::sum_row_major`",
            "`layout_benchmark.c`",
        ),
        "README index 위치와 source anchor가 다릅니다",
    )
    require_rejection(
        "annotation-index-separator-drift",
        lambda root: replace(
            root / "examples/branch-benchmark/README.md",
            "|---|---|---|",
            "권장 순서 표 separator가 아닙니다.",
        ),
        "권장 구현 순서 표 separator가 올바르지 않습니다",
    )
    require_rejection(
        "annotation-index-missing-responsibility",
        lambda root: replace(
            root / "examples/branch-benchmark/README.md",
            "| 1 | `branch_benchmark.c::count_selected` | 두 입력에 동일하게 적용할 selection workload |",
            "| 1 | `branch_benchmark.c::count_selected` |",
        ),
        "권장 구현 순서 행은 비어 있지 않은 3개 field여야 합니다",
    )
    require_rejection(
        "copied-concept-rubric",
        lambda root: copy_section(
            root,
            "docs/01-representation-and-isa/01-data-representation-and-arithmetic.md",
            "docs/01-representation-and-isa/02-isa-assembly-and-program-execution.md",
            "완료 기준",
        ),
        "완료 기준을 복사",
    )
    require_rejection(
        "non-executable-script",
        lambda root: (root / "prepare.sh").chmod(
            (root / "prepare.sh").stat().st_mode & ~stat.S_IXUSR
        ),
        "실행 권한이 없습니다",
    )
    require_rejection(
        "unfinished-reference",
        lambda root: (root / "exercises/processor-model/reference/processor_model/bits.py").write_text(
            (root / "exercises/processor-model/reference/processor_model/bits.py").read_text(encoding="utf-8")
            + "\n# TODO: mutant\n",
            encoding="utf-8",
        ),
        "reference에 미완성 표시",
    )
    require_rejection(
        "runtime-version-drift",
        lambda root: replace(
            root / "reference/version-baseline.md", "Python >= 3.12", "Python >= 3.11"
        ),
        "실행·판본 계약이 없습니다",
    )

    def add_symlink(root: Path) -> None:
        (root / "unexpected-symlink").symlink_to("README.md")

    require_rejection("source-symlink", add_symlink, "source tree에 symlink")
    require_rejection(
        "missing-roadmap-outcome",
        lambda root: replace(
            root / "docs/00-roadmap.md",
            "## 완료 후 할 수 있어야 하는 일",
            "## 과정 참고",
        ),
        "로드맵 학습 계약",
    )
    print("validator mutant suite: PASS (35/35)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
