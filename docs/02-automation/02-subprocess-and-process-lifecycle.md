# 외부 프로세스와 수명 관리

## 학습 목표

자동화 프로그램은 다른 프로그램을 실행하는 순간 운영체제 자원과 비결정적인 실패를 다룹니다. 이 장은 [`command-checker` 5단계와 7단계](../../exercises/command-checker/README.md#5단계-외부-프로세스-한-건-실행)에 연결됩니다.

## 선행 개념

- CLI 네 채널과 context manager·timeout의 자원 수명 영향

## 명령은 인자 목록으로 전달합니다

```python
import subprocess

result = subprocess.run(
    ["git", "status", "--short"],
    text=True,
    capture_output=True,
    check=False,
)
```

다음 방식은 신뢰할 수 없는 입력을 셸 코드로 다시 해석할 수 있습니다.

```python
subprocess.run(f"grep {user_input} application.log", shell=True)
```

셸의 확장과 파이프가 실제 요구사항이 아니라면 `shell=False`와 인자 목록을 사용합니다.

```python
subprocess.run(["grep", user_input, "application.log"], check=False)
```

목록 원소 하나는 명령 인자 하나입니다. 공백이 있는 문자열도 다시 나뉘지 않습니다.

## 결과 채널을 분리합니다

```python
result = subprocess.run(
    [sys.executable, "tool.py"],
    input="3 1 2\n",
    text=True,
    capture_output=True,
    check=False,
)
```

검사할 값:

```text
result.returncode
result.stdout
result.stderr
```

오류 종료 자체를 검사할 때 `check=True`를 사용하면 예외로 변환되어 비교 정책이 흐려집니다. 검사기에서는 `check=False`가 자연스럽습니다.

## 현재 Python을 재사용합니다

```python
import sys

command = [sys.executable, "-m", "sample"]
```

가상환경과 Python 버전을 보존합니다.

## 작업 디렉터리와 환경

```python
import os

custom_env = os.environ.copy()
custom_env.update(case_environment)

subprocess.run(
    command,
    cwd=working_directory,
    env=custom_env,
    check=False,
)
```

환경을 새 dict 하나로 완전히 바꾸면 `PATH`와 locale 같은 값이 사라질 수 있습니다. 반대로 테스트가 부모 환경을 무조건 상속하면 외부 상태에 따라 결과가 달라질 수 있습니다. 유지할 값과 덮어쓸 값을 명시합니다.

## timeout은 결과가 아니라 수명 계약입니다

```python
try:
    subprocess.run(command, timeout=2.0, check=False)
except subprocess.TimeoutExpired:
    ...
```

제한 시간이 없으면 무한 루프 하나가 전체 검사를 멈출 수 있습니다. 하지만 부모 프로세스 하나를 종료하는 것만으로 충분하지 않을 수 있습니다.

```text
검사기
└─ 검사 대상 부모
   └─ 검사 대상의 자식
```

자식이 계속 실행하거나 stdout 파이프를 보유하면 부모가 끝난 뒤에도 검사가 멈출 수 있습니다.

## POSIX 프로세스 그룹

macOS와 Linux에서는 검사 대상을 새 세션으로 시작할 수 있습니다.

```python
process = subprocess.Popen(
    command,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    start_new_session=True,
)
```

timeout이나 출력 초과 시 그룹 전체에 정상 종료 신호를 보냅니다.

```python
os.killpg(process.pid, signal.SIGTERM)
```

짧은 유예 뒤에도 남으면 `SIGKILL`을 사용합니다. 처음부터 강제 종료하지 않는 이유는 대상이 임시 파일과 하위 자원을 정리할 기회를 주기 위해서입니다.

Windows 네이티브 환경의 프로세스 트리 정리는 다른 API가 필요하며 이 실습의 지원 범위 밖입니다.

## stdin, stdout과 stderr를 함께 진행합니다

검사기가 stdin 전체를 먼저 쓰고 나서 stdout을 읽으면 파이프 교착이 생길 수 있습니다.

```text
검사기: 큰 stdin을 쓰는 중
대상: stdout 파이프가 가득 차 쓰기 대기
대상: stdin을 더 읽지 못함
검사기: stdin 쓰기를 끝내지 못함
```

`selectors.DefaultSelector`와 non-blocking FD를 사용하면 한 반복에서 다음을 함께 처리할 수 있습니다.

```text
stdin에 쓸 수 있음
stdout에서 읽을 수 있음
stderr에서 읽을 수 있음
프로세스 종료
deadline 만료
```

상태는 값으로 드러냅니다.

```text
input offset
stdout bytes
stderr bytes
deadline
timed out
exceeded stream
```

EOF를 확인한 스트림은 selector에서 해제하고 닫습니다.

## 출력량도 제한합니다

시간 안에 끝나더라도 무한 출력을 쓰는 프로그램은 검사기를 메모리 부족으로 만들 수 있습니다.

```text
stdout ≤ case.output_limit
stderr ≤ case.output_limit
```

상한을 넘긴 순간 더 쌓지 않고 프로세스 그룹 정리 절차로 들어갑니다. 전체 출력을 메모리에 받은 뒤 크기를 확인하면 이미 제한의 목적을 잃습니다.

## spawn 실패와 결과 불일치를 구분합니다

- 실행 파일을 찾지 못함, 권한 없음: 검사를 시작할 수 없는 오류 → 종료 상태 2
- 프로그램이 예상과 다른 종료 상태를 반환함: 정상적으로 관찰한 불일치 → 종료 상태 1

프로세스 API 예외를 모두 “테스트 실패”로 바꾸지 않습니다.

## 정리 경로

성공, timeout, 출력 초과와 예외에서 다음 자원이 정리되어야 합니다.

- selector 등록
- stdin/stdout/stderr 파이프
- 부모 프로세스
- 자식 프로세스 그룹
- 임시 상태

정리 실패가 원래 실패를 가리지 않도록 진단 순서도 고려합니다.

## 연결 실습

- [command-checker 5·7단계](../../exercises/command-checker/README.md)에서 child, pipe, timeout과 output limit 정리를 검증합니다.

## 완료 기준

- 명령과 인자 경계를 목록으로 보존합니다.
- returncode, stdout과 stderr를 별도로 비교합니다.
- 현재 인터프리터와 필요한 환경만 전달합니다.
- timeout 뒤 자식 프로세스까지 정리합니다.
- 입력과 두 출력 스트림을 동시에 진행시킵니다.
- 출력 상한을 초과하기 전에 수집을 중단합니다.

다음은 [동시성, 취소와 자원 한계](03-concurrency-and-cancellation.md)입니다.
