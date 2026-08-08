"""프로세스 수집과 독립된 결과 비교 규칙입니다."""

from __future__ import annotations

from .model import Case


def compare_observation(
    case: Case,
    *,
    returncode: int | None,
    stdout: str,
    stderr: str,
    timed_out: bool = False,
    exceeded_stream: str | None = None,
) -> tuple[str, ...]:
    failures: list[str] = []

    if timed_out:
        failures.append(f"제한 시간: {case.timeout:g}초를 초과했습니다.")
        return tuple(failures)

    if exceeded_stream is not None:
        stream_name = "표준 출력" if exceeded_stream == "stdout" else "표준 오류"
        failures.append(
            f"출력 상한: {stream_name}이 {case.output_limit}바이트를 넘었습니다."
        )
        return tuple(failures)

    if returncode != case.returncode:
        failures.append(f"종료 상태: 예상 {case.returncode}, 실제 {returncode}")
    if stdout != case.stdout:
        failures.append(f"표준 출력: 예상 {case.stdout!r}, 실제 {stdout!r}")
    if stderr != case.stderr:
        failures.append(f"표준 오류: 예상 {case.stderr!r}, 실제 {stderr!r}")
    return tuple(failures)
