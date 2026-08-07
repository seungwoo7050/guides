#!/usr/bin/env python3
from __future__ import annotations

import os
import selectors
import signal
import subprocess
import sys
import time


def read_line(process: subprocess.Popen[str], timeout: float) -> str:
    assert process.stdout is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        events = selector.select(timeout)
        if not events:
            raise AssertionError(f"{timeout}초 안에 출력이 없습니다")
        line = process.stdout.readline()
        if line == "":
            raise AssertionError(f"예상보다 일찍 EOF: status={process.poll()}")
        return line.rstrip("\n")
    finally:
        selector.close()


def terminate(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def run_once(program: str, include_burst: bool) -> None:
    process = subprocess.Popen(
        [program],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    try:
        ready = read_line(process, 4.0)
        if not ready.startswith("ready pid="):
            raise AssertionError(f"ready 형식 불일치: {ready!r}")
        announced = int(ready[len("ready pid="):])
        if announced != process.pid:
            raise AssertionError(f"PID 불일치: 출력={announced}, 실제={process.pid}")

        for _ in range(3):
            os.kill(process.pid, signal.SIGUSR1)
            line = read_line(process, 4.0)
            if line != "event=SIGUSR1":
                raise AssertionError(f"SIGUSR1 출력 불일치: {line!r}")

        if include_burst:
            for _ in range(64):
                os.kill(process.pid, signal.SIGUSR1)

            # 서로 다른 표준 시그널 사이의 전달 순서는 POSIX가 보장하지
            # 않습니다. SIGUSR1을 적어도 한 번 관찰한 뒤에 종료 신호를
            # 보내야 이 검사가 번호별 전달 순서에 의존하지 않습니다.
            usr1_count = 0
            deadline = time.monotonic() + 5.0
            while usr1_count == 0:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError("burst SIGUSR1을 관찰하지 못했습니다")
                line = read_line(process, remaining)
                if line != "event=SIGUSR1":
                    raise AssertionError(f"알 수 없는 이벤트 출력: {line!r}")
                usr1_count += 1

            os.kill(process.pid, signal.SIGTERM)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise AssertionError("burst 뒤 SIGTERM을 처리하지 못했습니다")
                line = read_line(process, remaining)
                if line == "event=SIGUSR1":
                    usr1_count += 1
                    continue
                if line == "event=SIGTERM":
                    break
                raise AssertionError(f"알 수 없는 이벤트 출력: {line!r}")
            if not 1 <= usr1_count <= 64:
                raise AssertionError(f"표준 시그널 합쳐짐 범위 위반: {usr1_count}")
        else:
            os.kill(process.pid, signal.SIGTERM)
            line = read_line(process, 4.0)
            if line != "event=SIGTERM":
                raise AssertionError(f"SIGTERM 출력 불일치: {line!r}")

        status = process.wait(timeout=4.0)
        if status != 0:
            raise AssertionError(f"정상 종료 상태가 아님: {status}")
        assert process.stdout is not None
        trailing = process.stdout.read()
        if trailing:
            raise AssertionError(f"종료 이벤트 뒤 불필요한 stdout: {trailing!r}")
        assert process.stderr is not None
        error = process.stderr.read()
        if error:
            raise AssertionError(f"예상하지 않은 stderr: {error!r}")
    finally:
        terminate(process)


def main() -> int:
    if len(sys.argv) != 2:
        print("program path required", file=sys.stderr)
        return 2
    run_once(sys.argv[1], include_burst=False)
    run_once(sys.argv[1], include_burst=True)
    print("signal-loop 검사 통과")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
