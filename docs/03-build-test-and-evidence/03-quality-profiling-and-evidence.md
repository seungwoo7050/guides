# 품질 검사·프로파일링과 근거

“테스트가 통과했습니다”라는 문장만으로는 무엇을 확인했는지 알 수 없습니다. 실행한 소스 버전, 명령, 환경, 포함된 검사와 실행하지 못한 범위를 함께 남겨야 다른 사람이 같은 결과를 재현할 수 있습니다.

## 루트 명령의 계약

| 명령 | 담당하는 일 |
|---|---|
| `./prepare.sh` | source를 바꾸지 않고 도구 검사, Maven Wrapper와 의존성 준비 |
| `make check` | 문서·정확한 tree·validator mutant·셸 문법과 `javac` 기본 컴파일 |
| `VERIFY_LOG=/tmp/guide-java-verify.log ./verify.sh` | working tree의 격리 복사본을 오프라인으로 검증 |
| `make clean` | 저장소 안의 생성물과 검증 workspace 정리 |

`prepare.sh`는 테스트 결과를 판정하지 않습니다. `verify.sh`는 필수 검사가 실행되지 못하면 성공을 반환하지 않습니다.

## 전체 검증 단계

`verify.sh`는 다음 순서로 진행합니다.

1. JDK, Maven Wrapper와 준비된 dependency cache를 확인합니다.
2. 최종 디렉터리 구조와 이전 경로의 부재를 검사합니다.
3. 모든 Markdown 내부 링크와 POM XML을 검사합니다.
4. 셸 스크립트 문법과 Java 주 소스를 빠르게 컴파일합니다.
5. root reactor의 reference 모듈과 품질 플러그인을 실행합니다.
6. 각 skeleton이 의도한 테스트 실패에 도달하는지 확인합니다.
7. 격리된 Maven 저장소의 설치 전 실패·설치 후 성공을 확인합니다.
8. 실행기 reference를 JFR로 기록하고 이벤트를 읽습니다.
9. 임시 파일을 정리하고 원본의 bytes·mode·symlink·Git index가 같은지 확인합니다.

한 단계의 성공을 더 넓은 범위로 확대하지 않습니다. 예를 들어 `javac` 성공은 JUnit이나 Spotless 성공을 뜻하지 않습니다.

## 형식과 정적 검사

Spotless는 Google Java Format과 import 정리를 검사합니다. Checkstyle은 이 저장소에서 합의한 탭, star import, 사용하지 않는 import와 한 줄 다중 문장을 검사합니다.

자동 수정이 필요하면 다음을 실행하고 diff를 검토합니다.

```sh
./mvnw spotless:apply
git diff --check
./verify.sh
```

포매터 성공은 동작의 정확성을 증명하지 않고 정적 검사도 테스트를 대신하지 않습니다. 서로 다른 오류 종류를 줄이는 보완 관계입니다.

## debugger와 스택 관찰

실행 중 상태를 확인할 때 무작정 로그를 추가하기 전에 debugger와 JDK 도구를 사용합니다.

- breakpoint로 문제가 생기기 전 상태를 멈춥니다.
- step over와 step into를 구분합니다.
- 변수와 호출 스택을 확인합니다.
- `jstack <pid>`로 스레드와 잠금 대기를 확인합니다.
- `jcmd <pid> VM.command_line` 등으로 실제 JVM 실행 옵션을 확인합니다.

동시성 문제에서 한 번의 thread dump만으로 결론을 내리지 않습니다. 같은 시점의 여러 dump와 업무 상태를 함께 봅니다.

## JFR

JDK Flight Recorder는 CPU sample, allocation, thread, lock과 I/O 이벤트를 낮은 오버헤드로 기록할 수 있습니다.

```sh
jcmd <pid> JFR.start \
  name=guide \
  settings=profile \
  duration=60s \
  filename=guide.jfr
```

이 저장소의 `scripts/record-executor-jfr.sh`는 임시 recording을 만들고 실행기 관련 이벤트를 읽은 뒤 삭제합니다. 실행 시간 자체를 합격 기준으로 사용하지 않습니다.

프로파일링 순서는 다음과 같습니다.

```text
정확성 검증
→ 병목 가설
→ 같은 조건의 기준 측정
→ 한 변수 변경
→ 같은 조건 재측정
→ 정확성 재검증
```

잘못된 결과를 더 빨리 만드는 변경은 최적화가 아닙니다.

## 성능 수치에 필요한 조건

성능 결과에는 최소한 다음을 기록합니다.

- source commit과 JDK
- 운영체제와 CPU·메모리
- JVM 옵션과 heap 제한
- 준비 실행 여부
- 입력 크기와 데이터 분포
- 동시 작업 수와 큐 크기
- 반복 횟수와 오류 수
- p50, p95, p99 같은 분포

평균 하나만으로 긴 꼬리 지연을 숨기지 않습니다. 테스트 환경의 숫자를 공개 운영의 용량으로 바로 확대하지 않습니다.

## Java 코드 검토 질문

### 타입과 소유권

- 원시 값 조합이 단위와 의미를 잃고 있지 않습니까?
- record 생성자가 불변식을 검사합니까?
- 가변 컬렉션을 그대로 보관하거나 반환하지 않습니까?
- 값 객체의 동등성과 엔터티의 식별성을 구분합니까?
- 인터페이스가 실제 경계를 표현합니까?

### 컬렉션과 숫자

- 결과 순서가 우연한 구현에 기대지 않습니까?
- 금액 단위, scale과 반올림을 명시합니까?
- `Math.*Exact`가 필요한 연산을 조용히 넘기지 않습니까?
- Stream 안에 외부 효과를 숨기지 않습니까?

### 오류, 시간과 동시성

- 입력 오류, 상태 거절과 환경 실패를 구분합니까?
- `Clock`으로 시간 경계를 재현합니까?
- 읽기·판단·쓰기 전체가 필요한 원자성을 가집니까?
- 잠금 안에서 외부 I/O를 수행하지 않습니까?
- 작업 예외, 취소와 종료를 모두 관찰합니까?

### 빌드와 검증

- 정본 명령이 `./verify.sh`입니까?
- 준비된 의존성으로 오프라인 검증이 가능합니까?
- 오래된 local SNAPSHOT이 성공을 만들지 않습니까?
- 실행하지 못한 검사를 `PASS`로 기록하지 않습니까?

## 검증 기록

결과는 적어도 다음 세 상태를 구분합니다.

```text
PASS        실행했고 계약을 만족했습니다.
FAIL        실행했고 계약을 위반했습니다.
UNVERIFIED  필요한 환경이나 근거가 없어 실행하지 못했습니다.
```

필수 검사에 `UNVERIFIED`가 있으면 전체 완료가 아닙니다. 원시 보고서를 모두 커밋하기보다 다시 만드는 명령, 입력과 버전을 정본으로 남깁니다.

다음은 [누적 프로젝트 설계](../04-capstone.md)입니다.
