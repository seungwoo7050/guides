# 애플리케이션 경계 실패

이 장은 웹 기초나 공격 payload를 다시 가르치지 않습니다. 애플리케이션 취약점을 **어떤 신뢰 가정이 틀렸고, 어떤 보안 속성이 깨지며, 무엇을 회귀 검사해야 하는가**로 분석합니다.

HTTP·browser·애플리케이션 구현 기초는 `web-app`, path·process·동시성 원리는 `unix-systems`와 `operating-systems`, DNS·연결과 공개 서비스의 egress 운영은 `computer-networks`와 `web-infra`가 소유합니다. 여러 팀에 공통 실행 경로와 정책을 제공하는 일은 `platform-engineering`의 범위입니다. 이 장은 그 정본을 반복하지 않고, 해당 기능의 가정이 공격 경로에서 깨질 때의 불변식·최소 증명·회귀 근거만 다룹니다.

## 1. 입력 검증만으로 설명하지 않기

많은 취약점은 “입력을 검증하지 않았다”는 문장보다 구체적인 경계 실패입니다.

```text
데이터가 어느 interpreter 문맥으로 들어갔는가?
누가 resource access decision을 소유하는가?
caller가 제공한 identity·URL·path·type을 왜 신뢰했는가?
상태가 check와 use 사이에서 바뀔 수 있는가?
업무 순서와 수량 제한은 어디에서 강제되는가?
```

## 2. 데이터와 interpreter 경계

SQL, shell, template, expression, regular expression과 query language는 입력을 단순 문자열이 아니라 명령 구조로 해석할 수 있습니다.

보안 속성:

```text
사용자 data는 명령 구조를 바꾸지 않습니다.
허용된 operation과 parameter만 interpreter에 전달됩니다.
```

원인:

- 문자열 결합으로 code와 data를 섞음
- 허용 operation이 아닌 임의 표현식을 전달함
- subprocess·template·query API의 안전한 parameter 경계를 사용하지 않음
- escape를 여러 layer에서 잘못 적용함

검증:

- parameterization이 실제 호출 API까지 유지되는지 확인
- 정상 값과 구조를 바꾸려는 값의 결과 비교
- error·timing 차이가 민감한 구조를 드러내는지 확인
- 같은 root cause를 사용하는 모든 call site 조사

수정:

- 구조와 값을 타입·API 수준에서 분리
- operation allowlist
- interpreter 호출 자체를 더 제한된 abstraction으로 이동
- 실패를 일정한 방식으로 거절하고 audit event 생성

## 3. output context와 browser 해석

출력은 HTML body, attribute, URL, JavaScript, CSS, JSON처럼 서로 다른 문맥에 들어갑니다.

불변식:

```text
untrusted data는 출력 문맥을 벗어나 실행 가능한 구조가 되지 않습니다.
```

단순한 “특수문자 제거”가 아니라 framework의 context-aware encoding, 안전한 DOM API와 정책을 사용합니다. 저장 시점의 sanitize 하나로 모든 출력 문맥을 해결하려 하지 않습니다.

회귀 검사는 다음을 포함합니다.

- 각 출력 문맥별 synthetic marker
- server-rendered와 client-rendered 경로
- preview·export·email·admin UI 같은 2차 출력 경로
- content security policy가 차단을 보완하지만 root cause를 대신하지 않는지

## 4. object authorization

authentication과 route-level role check가 있어도 object ownership이 빠질 수 있습니다.

불변식:

```text
모든 resource action은 subject·action·resource·context를 같은 policy로 평가합니다.
```

위험한 가정:

- identifier를 모르면 접근할 수 없다고 가정
- list endpoint에서 걸렀으므로 detail endpoint도 안전하다고 가정
- gateway가 검사했으므로 internal service는 검사하지 않음
- cache key에 tenant·permission context가 빠짐
- background worker가 caller scope를 잃고 자신의 broad identity로 실행

검증 matrix:

| subject | resource | action | 기대 결과 |
|---|---|---|---|
| owner | own | read | 허용 |
| owner | own | update | policy에 따라 허용 |
| other user | foreign | read | 거절 |
| same role, other tenant | foreign tenant | read | 거절 |
| revoked user | former own | read | 거절 |
| service | task-scoped resource | read | 허용 |
| service | unrelated resource | read | 거절 |

## 5. server-side request boundary

애플리케이션이 사용자가 제공한 URL·host·redirect를 따라 server-side request를 보내면 public input이 internal reachability로 바뀔 수 있습니다.

불변식:

```text
server-side fetch는 승인된 목적지·protocol·address class·redirect policy 안에서만 동작합니다.
각 연결은 검사한 목적지와 실제 connected peer가 같은 정책 결정을 만족합니다.
```

검토할 경계:

- parser가 해석한 scheme·hostname·port
- DNS resolution이 반환한 모든 address와 resolution 시점
- 연결 직전에 허용한 address와 실제 connected peer
- redirect마다 새 URL·DNS 결과·connected peer를 다시 검증하는지
- IPv4·IPv6·alternative notation
- proxy와 service mesh가 추가하는 reachability
- cloud metadata·control plane·localhost
- response size·time·content type
- egress policy와 audit

URL string allowlist와 연결 전에 한 번 수행한 DNS 검사만으로 끝내지 않습니다. 공격자가 DNS 답을 바꾸거나 redirect가 새 목적지를 선택하면 **검사한 host와 실제 연결 대상**이 달라질 수 있습니다. 모든 resolved address를 정책으로 평가하고, 검증한 address로 연결을 묶은 뒤 실제 peer와 TLS hostname·certificate를 확인하거나, 이 결정을 신뢰할 수 있는 egress proxy에 맡깁니다. proxy를 사용해 애플리케이션이 proxy peer만 볼 수 있다면 proxy가 원래 목적지·각 redirect·최종 address를 검사하고 그 결정을 보호된 audit evidence로 남기는 enforcement owner여야 합니다.

network egress와 service identity에서도 같은 제한을 적용합니다. 로그에는 정규화한 원래 목적지, redirect hop, resolution 결과, 최종 peer와 거절 이유를 연결하되 URL 안의 credential이나 민감한 query는 그대로 남기지 않습니다. 이 근거는 관측한 fetch 경로를 설명하지만, 별도 resolver·proxy·library가 만드는 모든 outbound path가 같은 정책을 사용한다는 사실까지 자동으로 보장하지 않습니다.

## 6. file·path·upload 경계

위험한 가정:

- filename이 storage path로 안전함
- extension이 content type을 증명함
- archive 안의 path가 대상 directory 안에 남음
- upload 처리와 serving이 같은 trust level이어도 됨
- symlink·hard link·race가 없음

불변식:

```text
caller가 제공한 이름은 storage identity가 아닙니다.
쓰기 대상은 지정 root 밖으로 벗어나지 않습니다.
처리 전·후 content와 ownership이 검증됩니다.
```

검증:

- canonicalized path와 root 관계를 1차 조건으로 확인
- 신뢰한 directory descriptor를 기준으로 한 relative open과 `no-follow`·원자적·exclusive 생성
- open 뒤 descriptor의 object type·owner·inode를 확인하고 검사한 객체를 그대로 사용
- symlink·hard link·archive entry와 rename·교체 race 처리
- content sniffing과 parsing sandbox
- upload와 public serving 분리
- quota·size·count·decompression budget
- cleanup 실패와 orphan object

`canonicalize → root 안인지 검사 → path로 다시 open` 순서는 검사와 사용 사이에 symlink·rename으로 대상이 바뀌는 TOCTOU를 남깁니다. 지원되는 descriptor-relative API나 격리된 storage service로 **검사한 객체와 사용하는 객체를 결합**하고, 임시 객체를 완전히 검증한 뒤 원자적으로 publish합니다. path 문자열 검사 통과만으로 filesystem race가 사라졌다고 결론 내리지 않습니다.

## 7. deserialization과 polymorphic data

untrusted data가 runtime type, constructor, hook 또는 object graph를 선택하게 하면 data가 behavior를 결정합니다.

안전한 방향:

- 단순 data schema 사용
- 허용 type과 field를 명시
- parser resource limit
- signature는 출처를 확인할 뿐 unsafe object graph 자체를 안전하게 만들지 않음을 인식
- version·migration·unknown field policy

## 8. state transition과 business logic

기술적으로 유효한 request라도 업무 순서와 자원 불변식을 깰 수 있습니다.

예:

- 승인 전에 지급
- 같은 coupon·refund·reservation을 반복 사용
- 한도 검사를 여러 병렬 request로 우회
- step 1의 결과를 다른 subject가 step 2에서 사용
- client가 가격·role·completion 상태를 직접 지정

검증은 endpoint별이 아니라 상태 기계로 수행합니다.

```text
현재 상태
+ actor
+ command
+ precondition
→ 허용된 다음 상태 또는 거절
```

## 9. concurrency와 TOCTOU

check와 use가 분리되면 그 사이 상태가 바뀔 수 있습니다.

- quota 확인 뒤 차감
- path 검증 뒤 open
- permission 확인 뒤 resource owner 변경
- one-time token 확인 뒤 소비
- inventory 확인 뒤 reservation

수정은 lock을 무조건 추가하는 것이 아니라 atomic database operation, unique constraint, compare-and-set, transaction, idempotency key와 state version처럼 **정본에서 전이를 원자적으로 강제**하는 방식이어야 합니다.

## 10. error와 side channel

보안 속성은 응답 body만이 아니라 status, size, timing, retry와 log에서도 새어 나갈 수 있습니다.

- account·resource 존재 여부
- permission decision 차이
- secret 비교 timing
- parser error에 포함된 내부 path·query
- retryable·non-retryable 구분

모든 응답을 똑같이 만들 필요는 없지만 공격자가 민감한 상태를 추론할 수 있는지 검토합니다. 운영자가 문제를 진단할 수 있는 내부 evidence는 별도 보호된 channel에 남깁니다.

## 11. ASVS와 WSTG를 사용하는 방법

OWASP ASVS는 testable security requirement를 고르는 기준으로, WSTG는 web security test scenario를 설계하는 참고로 사용합니다. checklist를 채우는 것보다 다음 mapping이 중요합니다.

```text
threat
→ ASVS requirement
→ implementation owner
→ automated test
→ manual test
→ runtime evidence
→ residual risk
```

판본과 requirement ID를 함께 기록합니다.

## 12. 이 장의 산출물

애플리케이션 기능 하나를 선택해 다음을 만듭니다.

1. subject·action·resource·context matrix
2. input이 들어가는 interpreter·path·URL·state boundary 목록
3. 보안 불변식 6개
4. 정상·경계·실패 test case
5. server-side·background path에서 identity가 어떻게 전달되는지
6. error·log가 노출할 수 있는 상태
7. root cause 수준의 remediation
8. ASVS 또는 WSTG mapping
9. 각 검증 근거가 보장하는 경로와 아직 보지 못한 call site·runtime
10. 인접 브랜치에 맡긴 구현·운영 전제

## 13. 완료 질문

- 입력 검증이라는 말보다 interpreter context를 특정해야 하는 이유는 무엇입니까?
- route role check와 object authorization은 어떻게 다릅니까?
- URL allowlist만으로 server-side request를 제한하기 어려운 이유는 무엇입니까?
- transaction이 있어도 business logic race가 남을 수 있는 경우는 무엇입니까?
- framework security feature가 실제 application invariant로 이어졌음을 어떻게 검증합니까?
