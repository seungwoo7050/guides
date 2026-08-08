# JUnit·AssertJ와 테스트 대역

테스트는 코드가 예외 없이 끝났다는 사실보다 구체적인 계약을 증명해야 합니다. 입력, 반환값, 상태 변화, 외부 효과, 실패 뒤 상태와 자원 정리를 구분해서 관찰합니다.

## 테스트의 기본 구조

한 테스트는 하나의 행위를 설명하되 필요한 결과를 여러 각도에서 확인할 수 있습니다.

```text
Given  재현 가능한 시작 상태
When   하나의 공개 동작 실행
Then   반환값·상태·효과·실패 계약 확인
```

테스트 이름에는 조건과 기대 결과를 드러냅니다.

```java
@Test
void rejectsDebitWhenBalanceWouldBecomeNegative() {
  // ...
}
```

공통 setup은 반복되는 기반만 준비합니다. 판단에 필요한 핵심 값이 숨을 만큼 복잡한 fixture hierarchy를 만들지 않습니다.

## JUnit 수명 주기

JUnit Jupiter는 `@Test`, `@BeforeEach`, `@AfterEach`, parameterized test와 확장 모델을 제공합니다. 테스트 인스턴스와 자원의 수명을 이해하지 않고 static 상태를 공유하면 실행 순서에 따라 결과가 달라질 수 있습니다.

- 각 테스트는 독립적으로 실행할 수 있어야 합니다.
- 테스트 순서를 성공 조건으로 사용하지 않습니다.
- 실행기와 파일은 `@AfterEach` 또는 try-with-resources로 정리합니다.
- 병렬 실행 가능성을 막연히 가정하지 않습니다.

경계값 표가 같은 규칙을 공유할 때 parameterized test가 유용합니다. 서로 다른 실패 원인을 한 표에 억지로 합치지 않습니다.

## AssertJ로 계약 읽기

AssertJ는 실패 메시지와 검사를 읽기 쉽게 만듭니다.

```java
assertThat(result.balanceAfter()).isEqualTo(900L);

assertThatThrownBy(() -> money.subtract(tooLarge))
    .isInstanceOf(IllegalArgumentException.class)
    .hasMessageContaining("잔액");
```

객체 전체 비교가 편하다는 이유로 생성 시각, 임의 식별자와 순서가 불안정한 필드까지 무조건 묶지 않습니다. 계약에 필요한 필드를 명시하거나 제외 이유를 남깁니다.

예외 타입만 확인하고 기존 상태가 보존됐는지 놓치지 않습니다.

```java
assertThatThrownBy(() -> ledger.debit(amount))
    .isInstanceOf(IllegalStateException.class);
assertThat(ledger.balance()).isEqualTo(originalBalance);
```

## 테스트 대역

| 종류 | 역할 |
|---|---|
| fake | 실제 동작을 단순한 메모리 구현으로 제공합니다. |
| stub | 미리 정한 응답을 반환합니다. |
| spy | 호출 내용을 기록해 나중에 관찰합니다. |
| mock | 기대한 상호작용을 검증합니다. |

구현 세부 호출을 모두 mock으로 고정하면 리팩터링이 계약 변경처럼 보입니다. 외부 경계나 효과 횟수가 실제 계약일 때 상호작용을 확인하고, 순수 계산과 상태 전이는 결과 상태를 우선 검사합니다.

메모리 fake는 빠르지만 실제 데이터베이스의 transaction, constraint와 query semantics를 대신하지 않습니다. 단위 테스트와 실제 기술에 가까운 통합 테스트가 서로 다른 위험을 담당합니다.

## 상태와 효과를 함께 확인하기

같은 키의 요청이 모두 성공값을 돌려준 사실만으로 중복 처리를 막았다고 말할 수 없습니다.

```text
같은 요청을 여러 번 전달
→ 모든 호출이 같은 결과
→ 내부 상태는 한 번만 변경
→ 기록은 한 건만 추가
→ 외부 효과도 한 번만 발생
```

[상태와 효과 검증 실습](../../exercises/03-build-test-and-evidence/02-state-and-effect-testing/README.md)은 약한 반환값 검사와 강한 상태·효과 검사를 비교합니다.

## 실패와 경계 사례

정상 사례 하나 다음에 바로 다음을 확인합니다.

- 빈 값과 `null`
- 최소·최대 경계
- 잘못된 조합
- 정수 오버플로
- 중간 단계 예외
- 같은 요청 반복
- 같은 식별자와 다른 내용
- 시간 경계
- 취소와 인터럽트
- 자원 종료 뒤 호출

테스트가 실패했다는 사실만으로 exercise가 올바른 시작 상태인 것은 아닙니다. 의존성 다운로드나 컴파일 설정이 아니라 의도한 계약 assertion에서 실패하는지 확인합니다. 루트 `verify.sh`는 skeleton이 Surefire 테스트 실패에 도달했는지 검사합니다.

## 동시성 테스트

동시성 테스트는 컴퓨터 속도를 합격 조건으로 사용하지 않습니다.

- latch나 barrier로 교차 실행을 고정합니다.
- 모든 `Future`를 `get`해 작업 예외를 테스트 스레드로 전달합니다.
- 전체 테스트에 제한 시간을 둡니다.
- 성공 횟수, 합계, 최종 상태와 기록 수를 함께 확인합니다.
- 종료 뒤 실행기 스레드가 남지 않게 합니다.

`assertTimeout`만으로 작업 취소와 정리를 보장할 수는 없습니다. 테스트가 실패해도 finally나 `@AfterEach`에서 차단된 작업을 해제하고 실행기를 종료합니다.

## 테스트 품질을 검증하기

reference가 통과하는 것만으로 검사기가 충분하다고 단정하지 않습니다. 알려진 잘못된 구현인 skeleton이 예상한 테스트에서 실패해야 합니다.

```text
reference 통과
+ skeleton의 의도된 실패
= 최소한의 판별력 근거
```

더 높은 신뢰가 필요하면 mutation testing을 사용할 수 있지만, 먼저 중요한 실패 사례를 사람이 명시적으로 작성합니다.

## 완료 기준

- 한 테스트의 조건, 동작과 관찰 결과를 설명합니다.
- 반환값, 상태, 효과와 실패 뒤 상태를 구분해 검사합니다.
- fake, stub, spy와 mock을 실제 경계에 맞게 선택합니다.
- 동시성 테스트에서 우연한 sleep을 사용하지 않습니다.
- reference 성공과 skeleton의 의도된 실패를 모두 확인합니다.

다음은 [품질 검사·프로파일링과 근거](03-quality-profiling-and-evidence.md)입니다.
