# Unix 텍스트 도구를 이용한 CLI 검증

명령행 프로그램은 stdout, stderr와 종료 상태라는 안정된 외부 경계를 가집니다. POSIX shell과 `cmp`, `diff`, `grep`, `sed`, `awk`를 사용하면 외부 테스트 프레임워크 없이도 유용한 system test를 만들 수 있습니다.

목표는 도구 문법을 많이 외우는 것이 아니라, **어떤 종류의 결과를 어떤 관찰 채널과 도구로 검사해야 하는지 구분하는 것**입니다.

## 세 개의 관찰 채널

```text
stdout       정상 데이터
stderr       진단과 오류
exit status  성공·실패 또는 분류
```

각 채널을 분리합니다.

```sh
./program >actual.out 2>actual.err
status=$?
```

오류 메시지가 맞아도 상태가 0이면 자동화는 성공으로 오해할 수 있습니다. 정상 출력이 맞아도 상태가 실패면 전체 계약은 실패입니다. 스트림을 합치면 어느 채널의 데이터인지와 실제 순서를 잃을 수 있으므로 진단 편의가 필요할 때만 `2>&1`을 사용합니다.

## shell script의 최소 골격

```sh
#!/bin/sh
set -eu

fail()
{
    printf '실패: %s\n' "$*" >&2
    exit 1
}

actual=$(./program input) || fail "프로그램이 실패 상태로 끝났습니다"
[ "$actual" = "expected" ] || fail "예상과 다른 출력입니다"

printf '검사 통과\n'
```

- `set -e`는 확인하지 않은 명령 실패에서 중단하게 합니다.
- `set -u`는 정의하지 않은 변수를 오류로 처리합니다.

`set -e`만으로 모든 실패를 안전하게 처리할 수 있다고 가정하지 않습니다. 조건식, `if`, `!`, pipeline과 command substitution 안에서는 동작이 달라질 수 있습니다. 중요한 명령의 상태는 직접 저장하고 검사합니다.

`pipefail`은 여러 shell에 있지만 POSIX 표준 기능은 아닙니다. `/bin/sh` 호환성이 필요하면 pipeline 각 단계를 임시 파일과 별도 명령으로 나누거나 Python helper를 사용합니다.

## 예상 실패의 상태를 안전하게 받기

```sh
set +e
./program bad-input >"$tmp/out" 2>"$tmp/err"
status=$?
set -e

[ "$status" -eq 2 ] || fail "문법 오류 상태가 2가 아닙니다"
```

또는 `if` 문맥을 사용합니다.

```sh
if ./program bad-input >"$tmp/out" 2>"$tmp/err"
then
    fail "실패해야 하는 입력이 성공했습니다"
else
    status=$?
fi
```

명령 바로 뒤에서 `$?`를 저장합니다. 다른 `printf`, `test` 또는 cleanup 명령을 실행하면 그 상태로 덮어씌워집니다.

## 임시 디렉터리와 정리

고정된 파일명을 현재 디렉터리나 `/tmp/result`에 만들면 반복·병렬 실행과 다른 사용자 작업이 충돌할 수 있습니다.

```sh
tmp=$(mktemp -d) || exit 1
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
```

모든 생성 파일을 해당 디렉터리 아래에 둡니다.

```text
$tmp/stdout
$tmp/stderr
$tmp/expected
$tmp/work/
```

`trap` 문자열에 사용자 입력이나 검증 대상 경로를 코드처럼 삽입하지 않습니다. 임시 디렉터리를 변수에 저장하고 quoting을 유지합니다.

## 정확한 바이트 비교: `cmp`

두 파일이 바이트 단위로 같은지만 필요하면 `cmp`가 적합합니다.

```sh
cmp -s "$tmp/expected.bin" "$tmp/actual.bin" \
    || fail "바이트열이 다릅니다"
```

다음 조건에서는 텍스트처럼 보여도 `cmp`가 안전합니다.

- 마지막 newline 유무가 계약에 포함됩니다.
- 포함된 NUL 가능성이 있습니다.
- 공백과 tab을 정확히 구분해야 합니다.
- 사람이 읽는 diff보다 자동 성공·실패 판정이 우선입니다.

명령 치환은 끝의 newline을 제거하므로 정확한 바이트 검증에는 파일 redirection을 사용합니다.

```sh
actual=$(printf 'a\n\n')  # 끝 newline들이 제거됨
```

shell 변수 자체도 NUL 바이트를 안전하게 보존하지 못합니다.

## 사람이 읽는 차이: `diff`

텍스트 줄 차이를 보여 주려면 `diff`를 사용합니다.

```sh
if ! diff -u "$tmp/expected.txt" "$tmp/actual.txt"
then
    fail "텍스트 출력이 다릅니다"
fi
```

기대 파일은 heredoc으로 만들 수 있습니다.

```sh
cat >"$tmp/expected.txt" <<'EXPECTED'
count=3
minimum=-1
maximum=7
EXPECTED
```

quoted delimiter를 사용하면 shell 변수와 command substitution이 기대값 안에서 확장되지 않습니다.

출력 순서가 계약이 아니라면 비교 전에 정렬할 수 있지만, 이는 원래 순서 오류를 숨깁니다. “집합만 중요함”이 실제 계약일 때만 정규화합니다.

## 특정 존재·부재 검사: `grep`

```sh
grep -q '^ready$' "$tmp/actual" \
    || fail "ready 행이 없습니다"

if grep -q 'fatal' "$tmp/actual"
then
    fail "예상하지 않은 fatal 문구가 있습니다"
fi
```

`grep`은 특정 pattern 존재를 확인하는 데 적합합니다. 전체 출력이 정확히 같은지 검증하는 도구는 아닙니다. 예상한 한 줄을 찾았더라도 뒤에 잘못된 출력이 더 있을 수 있습니다.

고정 문자열을 찾을 때는 `grep -F`를 사용해 정규식 metacharacter 해석을 피합니다.

```sh
grep -Fq 'a+b' "$tmp/actual"
```

pattern이 `-`로 시작할 수 있다면 `--`를 지원하는 구현인지 확인하거나 안전한 고정 pattern을 사용합니다.

## 단순 변환과 줄 선택: `sed`

```sh
sed 's/[[:space:]]*$//' "$tmp/actual" >"$tmp/normalized"
```

비결정적인 PID나 절대 임시 경로를 지운 뒤 구조를 비교할 수 있습니다. 그러나 정상화가 지나치면 실제 결함을 숨깁니다.

```text
허용된 비결정성만 제거
의미 있는 field, 개수와 순서는 그대로 검사
```

예를 들어 모든 숫자를 `<number>`로 바꾸면 PID 차이뿐 아니라 잘못된 count와 상태도 놓칩니다.

## AWK의 레코드·필드 모델

AWK는 기본적으로 한 줄을 record로 읽고 공백을 기준으로 field를 나눕니다.

```awk
pattern { action }
```

주요 자동 변수:

| 이름 | 의미 |
|---|---|
| `$0` | 현재 줄 전체 |
| `$1`, `$2`, ... | 각 field |
| `NF` | 현재 field 수 |
| `NR` | 지금까지 읽은 record 수 |
| `FS` | 입력 field separator |
| `OFS` | 출력 field separator |

```sh
awk '$3 == "done" { count++ } END { print count + 0 }' log.txt
```

AWK는 field 검사, 집계와 작은 상태 머신에 적합합니다.

## 형식 전체를 검사합니다

모든 줄이 다음 형식이라고 가정합니다.

```text
<timestamp> <worker-id> <state>
```

```sh
awk '
    /^[0-9]+ [1-9][0-9]* (start|work|done)$/ { next }
    {
        printf "%d번째 줄 형식 오류: %s\n", NR, $0 > "/dev/stderr"
        bad = 1
    }
    END { exit bad }
' "$tmp/log"
```

올바른 줄은 `next`로 통과시키고 나머지를 실패 처리합니다. 정규식의 `^`와 `$`를 빼면 일부만 맞는 줄이나 뒤에 쓰레기 문자가 붙은 줄도 통과할 수 있습니다.

빈 파일도 허용되는지 별도로 검사합니다. 위 script는 입력이 0줄이면 성공하므로 최소 한 줄이 필요하다면 `END { if (NR == 0) bad = 1; exit bad }`를 추가합니다.

## 연관 배열로 상태 불변식을 검사합니다

```awk
$3 == "done" {
    if (finished[$2]) {
        printf "%d번째 줄: %s의 done이 중복됨\n", NR, $2 > "/dev/stderr"
        bad = 1
    }
    finished[$2] = 1
}
END { exit bad }
```

동시성 로그에서 다음을 검사할 수 있습니다.

- worker ID 범위
- 허용된 상태 이름만 출력
- `start` 전에 `work` 금지
- `done` 뒤 추가 작업 금지
- ID별 작업 횟수
- 전체 시작·종료 수 일치
- 전체 합계 또는 보존량
- timestamp가 정수 형식인지

scheduler에 따라 전체 줄 순서가 달라질 수 있다면 고정된 완전 순서를 기대하지 않고 실제 상태 전이와 불변식을 검사합니다.

## stdout·stderr·status를 함께 검증합니다

```sh
set +e
./program bad-input >"$tmp/out" 2>"$tmp/err"
status=$?
set -e

[ "$status" -eq 2 ] || fail "상태: 기대 2, 실제 $status"
[ ! -s "$tmp/out" ] || fail "실패 시 stdout은 비어야 합니다"
grep -Fq '오류:' "$tmp/err" || fail "진단 문구가 없습니다"
```

오류 메시지 전체가 공개 API가 아니라면 핵심 분류만 검사할 수 있습니다. 반대로 CLI 문구 자체가 자동화 계약이면 정확한 파일 비교가 필요합니다.

locale에 따라 system error 문자열이 달라질 수 있으므로 `strerror` 전체 문구를 고정 기대값으로 삼는 것은 신중해야 합니다.

## 바이너리와 포함된 NUL

shell 변수는 NUL을 보존하지 못합니다. 파일 크기, `cmp`, `od` 또는 작은 Python helper를 사용합니다.

```sh
bytes=$(wc -c <"$tmp/output")
[ "$bytes" -eq 4 ] || fail "바이트 수가 다릅니다"
cmp -s "$tmp/expected.bin" "$tmp/output" \
    || fail "binary output이 다릅니다"
```

사람이 byte를 확인할 때:

```sh
od -An -tx1 "$tmp/output"
```

`od` 출력의 공백을 테스트 계약으로 삼기보다 실제 binary file을 `cmp`하는 편이 견고합니다.

## fixture와 작은 helper

테스트가 host의 `printf`, `head`, `yes` 구현 차이에 과도하게 의존하지 않도록 목적이 하나인 C helper를 만들 수 있습니다.

- 정확한 바이트 수를 쓰는 generator
- 정확한 바이트 수를 읽고 검사하는 consumer
- 지정한 상태로 종료하는 프로그램
- signal을 자신에게 보내 종료하는 프로그램
- argv 각 항목을 길이와 함께 출력하는 프로그램
- 실행되면 marker file을 만드는 프로그램

helper도 본 코드와 같은 엄격한 warning 옵션으로 빌드합니다. helper 자체가 복잡하면 테스트가 새 결함 원인이 됩니다.

## 큰 pipeline 검증

작은 문자열은 파이프 buffer에 모두 들어가 잘못된 wait 순서도 통과할 수 있습니다. generator와 consumer helper로 수 MiB를 전송합니다.

```text
emit-bytes 4194304 | expect-bytes 4194304
```

검사해야 할 것은 단순 최종 status만이 아닙니다.

- 정확한 바이트 수가 도착했습니다.
- timeout 안에 끝났습니다.
- generator와 consumer 모두 회수됐습니다.
- 예상하지 않은 stderr가 없습니다.
- 반복 실행해도 FD가 증가하지 않습니다.

## timeout과 process group 정리

프로세스·파이프·스레드 검사는 결함이 있으면 영원히 기다릴 수 있습니다. GNU `timeout`은 편리하지만 POSIX 표준 명령은 아닙니다.

```sh
timeout 5 ./program
```

이식성이 필요하면 Python을 사용할 수 있습니다.

```python
subprocess.run(command, timeout=5, check=True)
```

자식이 다시 자식을 만드는 프로그램은 부모 PID만 죽여도 grandchild가 남을 수 있습니다. 새 session/process group으로 시작하고 timeout 뒤 전체 group을 종료한 다음 `wait`로 회수합니다.

```python
process = subprocess.Popen(command, start_new_session=True)
os.killpg(process.pid, signal.SIGKILL)
process.wait()
```

정상 실행 시간보다 충분히 넓은 timeout을 둬 느린 CI의 거짓 실패를 줄입니다. timeout 통과는 성능 보장이 아니라 무한 대기하지 않았다는 관찰입니다.

## race를 sleep으로 만들지 않습니다

```sh
sleep 0.1
kill -USR1 "$pid"
```

이 방식은 프로그램이 ready 상태가 됐다는 보장이 없습니다. 느린 환경에서는 handler 설치 전에 시그널을 보낼 수 있습니다.

더 좋은 방식:

```text
프로그램이 "ready pid=..." 출력
→ 테스트가 해당 줄을 timeout 안에 읽음
→ 그 뒤 signal 전송
```

스레드 테스트도 `sleep` 대신 barrier, condition variable 또는 pipe handshake로 동시 시작을 조정합니다.

## 부분 순서와 비결정성

모든 출력 순서가 고정되지 않아도 일부 관계는 반드시 지켜질 수 있습니다.

```text
ready는 event보다 먼저
start(id)는 done(id)보다 먼저
종료 message 뒤 추가 업무 log 없음
```

AWK 상태 머신이나 Python test로 이러한 partial order를 검사합니다. 전체 출력 정렬은 순서 위반을 숨길 수 있습니다.

## 재실행과 독립성

같은 프로그램을 한 번만 실행하면 전역 상태, 임시 파일과 FD 누수를 놓칠 수 있습니다.

- 같은 process 안에서 API를 반복 호출합니다.
- 실행 파일을 여러 번 시작합니다.
- 동일 입력을 순서만 바꾸어 실행합니다.
- 성공 뒤 실패, 실패 뒤 성공을 이어서 검사합니다.
- 임시 디렉터리가 매번 비어 있는지 확인합니다.

테스트 사이 상태가 공유되어야 하는 경우가 아니라면 fixture를 매 사례 새로 만듭니다.

## failure injection

오류 경로는 실제 메모리 부족이나 드문 system failure를 기다리지 않고 주입 가능한 경계로 만듭니다.

- allocator callback이 N번째 호출에 실패
- helper가 지정 상태로 종료
- 유효하지 않은 FD
- 닫힌 pipe reader
- 잘못된 parser 입력
- 목적지 overflow 직전 값

주입 후에는 반환값뿐 아니라 출력 매개변수, 기존 객체 불변식과 정리 가능성을 검사합니다.

## known-bad 구현으로 테스트 품질을 확인합니다

reference가 통과하는 것만으로 테스트가 충분하다는 뜻은 아닙니다. 알려진 결함을 넣은 구현이 실패하는지 확인합니다.

```text
문자열 NUL 한 바이트 누락
realloc 결과 직접 대입
파이프 write end를 parent에서 열어 둠
문법 오류 뒤 왼쪽 command 실행
두 mutex 잠금 순서 반전
```

모든 mutation framework가 필요한 것은 아닙니다. 핵심 실패 조건마다 skeleton 또는 작은 broken fixture가 테스트에 걸리는지 확인할 수 있습니다.

## 실패 메시지는 재현 정보를 줍니다

검사 실패는 최소한 다음을 보여 줍니다.

- 사례 이름
- 실행 명령 또는 입력
- 기대 상태와 실제 상태
- stdout·stderr 경로 또는 짧은 내용
- timeout 여부
- 임시 결과를 보존할 선택지

`test failed` 한 줄만 출력하면 원인을 찾기 위해 테스트 코드를 다시 읽어야 합니다.

C test macro도 파일, 줄과 식을 출력합니다.

```c
#define CHECK(expression) do {                                      \
    if (!(expression))                                              \
    {                                                               \
        fprintf(stderr, "%s:%d: 실패: %s\n",                    \
                __FILE__, __LINE__, #expression);                   \
        return 1;                                                   \
    }                                                               \
} while (0)
```

## 도구 선택 기준

| 질문 | 적합한 도구 |
|---|---|
| 바이트가 완전히 같은가? | `cmp` |
| 텍스트 차이를 사람이 보고 싶은가? | `diff` |
| 특정 문자열이 존재하거나 없어야 하는가? | `grep` |
| 허용된 비결정성만 정규화해야 하는가? | `sed` |
| field 검사·집계·상태 추적이 필요한가? | `awk` |
| 명령 조립·redirection·상태 관리가 필요한가? | POSIX shell |
| timeout·signal·process group 제어가 필요한가? | Python helper |
| 메모리·UB·data race를 관찰해야 하는가? | sanitizer |

한 도구로 모든 검증을 처리하지 않습니다.

## 테스트의 한계

CLI test는 공개 동작을 잘 확인하지만 다음을 직접 증명하지 않습니다.

- 내부 메모리 누수가 없음
- data race가 없음
- 모든 interleaving이 안전함
- 지원하지 않은 입력까지 안전함
- 성능 상한을 항상 만족함

unit test, integration test, code review, sanitizer와 debugger를 함께 사용합니다. sanitizer 통과도 실행한 입력 경로에 대한 근거입니다.

## 기존 예제와 연결

`examples/text-checks`는 다음 방식을 보여 줍니다.

- `cmp`: 정확한 도움말·바이트 결과
- `diff`: 사람이 읽는 정상 출력
- `grep`: 오류 메시지 존재와 stdout 부재
- `awk`: 로그 형식, ID별 상태와 줄 수
- 임시 디렉터리와 `trap`
- 실패 시 non-zero 상태

```sh
make -C examples/text-checks check
```

## 점검 질문

1. stdout, stderr와 exit status를 각각 검사해야 하는 이유는 무엇입니까?
2. command substitution이 정확한 바이트 비교에 부적합한 경우는 언제입니까?
3. `cmp`, `diff`, `grep`은 어떤 목적이 다릅니까?
4. 정규화가 실제 오류를 숨기지 않게 하려면 무엇을 제한해야 합니까?
5. AWK 연관 배열로 어떤 상태 불변식을 검사할 수 있습니까?
6. 멈출 수 있는 테스트에 timeout과 process group 정리가 필요한 이유는 무엇입니까?
7. ready handshake가 임의 `sleep`보다 안정적인 이유는 무엇입니까?
8. failure injection 뒤 반환값 외에 어떤 상태를 검사해야 합니까?
9. reference 통과만으로 테스트 품질이 충분하지 않은 이유는 무엇입니까?
10. sanitizer와 CLI test가 서로 대체할 수 없는 이유는 무엇입니까?
