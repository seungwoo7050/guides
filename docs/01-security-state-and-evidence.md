# 보안 상태와 증거

보안 문제를 도구나 공격 이름으로 시작하면 중요한 질문이 빠집니다.

```text
무엇이 안전해야 하는가?
어떤 상태 변화가 실패인가?
누가 그 변화를 일으킬 수 있는가?
그 사실을 무엇으로 증명하는가?
```

이 장은 이후 모든 문서가 사용하는 공통 판단 모델을 만듭니다.

## 1. 보안은 제품에 붙는 형용사가 아닙니다

“이 시스템은 안전합니다”는 검증할 수 없는 주장입니다. 보안은 특정 자산, 위협, 시간과 운영 조건에서 유지해야 하는 속성입니다.

예:

```text
인증된 사용자 A는 자신이 소유한 보고서만 읽을 수 있습니다.
```

이 문장은 다음을 드러냅니다.

- 주체: 사용자 A
- 객체: 보고서
- 관계: 소유권
- 허용 행동: 읽기
- 금지 상태: 다른 사용자의 보고서를 읽음

반면 다음 문장은 충분하지 않습니다.

> 보고서 API는 인증을 사용합니다.

인증은 주체를 식별할 뿐 객체 접근이 허용되는지 보장하지 않습니다.

## 2. 보호할 보안 속성

기밀성·무결성·가용성은 출발점이지만 실제 요구사항으로 내려와야 합니다.

| 상위 속성 | 시스템에서 물을 질문 |
|---|---|
| 기밀성 | 누가 어떤 데이터의 존재·내용·metadata를 볼 수 있습니까? |
| 무결성 | 누가 어떤 상태를 어떤 조건에서 바꿀 수 있습니까? |
| 가용성 | 어떤 사용자가 어떤 기능을 어느 시간 안에 계속 사용할 수 있어야 합니까? |
| 진위성 | 요청·artifact·event가 주장한 출처에서 왔음을 어떻게 확인합니까? |
| 책임 추적 | 누가 무엇을 했는지 나중에 재구성할 수 있습니까? |
| 격리 | 한 tenant·process·service의 실패가 어디까지 확산될 수 있습니까? |
| 복구 가능성 | 손상 뒤 어떤 정본에서 안전한 상태를 다시 만들 수 있습니까? |

하나의 통제가 모든 속성을 보장하지 않습니다. 암호화는 저장된 내용의 기밀성을 높일 수 있지만 잘못된 권한으로 정상 복호화가 허용되면 접근 통제 실패를 해결하지 못합니다.

## 3. 자산보다 상태를 더 구체적으로 적기

“데이터베이스 보호”는 너무 넓습니다. 다음처럼 상태를 나눕니다.

```text
사용자 record의 내용
schema와 migration history
backup artifact
DB credential
audit event
삭제 요청의 완료 상태
```

같은 시스템 안에서도 보호 목표가 다릅니다.

- 사용자 record는 허가된 업무 경로에서만 변경됩니다.
- migration은 승인된 release artifact에서만 실행됩니다.
- backup은 production host 손상 뒤에도 삭제되지 않습니다.
- audit event는 조사 대상 process가 임의로 수정할 수 없습니다.

### `owner`를 한 역할로 뭉치지 않기

자산 register의 `owner` 한 칸만으로는 누가 상태를 바꾸고 누가 그 결정을 승인하는지 알 수 없습니다. 다음 책임을 분리해 기록합니다. 한 사람이 여러 역할을 맡을 수는 있지만, 책임 자체를 합치지는 않습니다.

| 역할 | 소유하는 결정과 상태 | 소유하지 않는 결정 |
|---|---|---|
| 업무·위험 소유자 | 업무 영향, 복구 우선순위와 처리 기한 | 기술 통제의 실제 enforcement나 공식 위험 수용을 자동으로 승인하지 않음 |
| 상태 정본 소유자 | authoritative record, 허용된 상태 전이와 version | 모든 소비자의 cache·복제본이 실제로 같은 상태인지 단독 보장하지 않음 |
| enforcement owner | 요청 시점의 identity·resource·action·policy를 평가하고 허용·거절함 | 업무 영향과 잔여 위험을 대신 결정하지 않음 |
| evidence custodian | 증거의 수집·무결성·접근·보존·폐기 | event가 표현한 업무 판단의 정확성을 단독 보장하지 않음 |
| risk acceptance authority | 확인된 잔여 위험의 기간·조건·재검토 trigger를 공식 승인함 | 평가자나 취약점 담당자가 스스로 부여할 수 있는 역할이 아님 |

상태에는 그것을 바꾸는 사건과 입력도 함께 적습니다.

| 상태·자원 | 정본과 상태 변경 사건 | 정상·경계·대표 실패 |
|---|---|---|
| report ownership | report 정본; 생성, 명시적 소유권 이전, 삭제 완료 | owner read / 이전 중·삭제 직후 read / foreign owner read 허용 |
| job-scoped credential | credential issuer 정본; 발급, job 종료, 만료, 폐기 | 같은 job resource / 만료 시각·누락된 job context / cross-job 사용 허용 |
| release 승인 | release manifest 정본; candidate 생성, 승인, 승격, rollback·revoke | 승인 digest 실행 / 직전 version rollback / mutable tag나 미승인 digest 실행 |

정상 사례만 통과하면 불변식의 절반만 본 것입니다. 경계 사례는 owner 변경, 정확한 만료 시각, 빈 context, retry·cache처럼 해석이 갈릴 입력을 고정하고, 대표 실패 사례는 금지된 상태가 실제로 거절되며 보호 상태가 변하지 않는지 확인합니다.

## 4. 보안 불변식

불변식은 공격·장애·재시도 중에도 유지되어야 하는 조건입니다.

예:

```text
모든 object read는 authenticated subject와 object owner를 비교합니다.
service token은 발급된 작업의 resource scope 밖에서 사용할 수 없습니다.
release artifact는 승인된 source와 build identity의 provenance를 가집니다.
비밀값은 log·error response·artifact에 평문으로 남지 않습니다.
```

좋은 불변식은 다음 성질을 가집니다.

- 구체적인 주체·객체·행동을 포함합니다.
- 구현 기술 하나에 종속되지 않습니다.
- 정상 경로와 실패 경로에서 검사할 수 있습니다.
- 실패했을 때 관찰 가능한 결과가 있습니다.

## 5. 통제와 증거를 구분하기

통제(control)는 위험을 줄이는 장치입니다. 증거(evidence)는 통제가 실제 존재하고 작동했음을 뒷받침합니다.

| 보안 주장 | 통제 예 | 필요한 증거 예 |
|---|---|---|
| 다른 tenant 데이터를 읽을 수 없음 | object-level authorization | 허용·거절 통합 테스트, audit event |
| production은 승인 artifact만 실행 | digest pinning, provenance verification | release manifest, verifier 결과, 실제 실행 digest |
| 탈취 token의 영향이 제한됨 | 짧은 수명, 최소 scope | 발급 정책, token claim, 거절 event |
| 사고 뒤 복구 가능 | 외부 backup과 restore 절차 | checksum, restore drill 결과, RPO·RTO 측정 |

설정 파일에 옵션이 있다는 사실만으로 runtime에서 통제가 적용됐다고 단정하지 않습니다.

## 6. 사실, 가설과 결론

보안 조사에서 다음 세 가지를 분리합니다.

### 사실

직접 관찰하거나 신뢰할 수 있는 artifact로 확인한 상태입니다.

```text
2026-08-09T01:02:03Z에 subject=user-17이 report-82를 요청했습니다.
response status는 200이었습니다.
report-82의 owner는 user-44입니다.
```

### 가설

사실을 설명할 수 있지만 아직 확인되지 않은 원인입니다.

```text
다운로드 경로에서 object ownership 검사가 누락됐을 수 있습니다.
```

### 결론

반증 가능한 검사를 통과한 뒤 채택한 판단입니다.

```text
인증된 일반 사용자가 다른 사용자의 report ID를 알고 있으면 내용을 읽을 수 있습니다.
```

로그 한 줄, scanner 경고 또는 코드 한 조각만으로 결론을 내리지 않습니다.

## 7. 증거의 품질

증거를 다음 기준으로 평가합니다.

| 기준 | 질문 |
|---|---|
| 직접성 | 주장한 상태를 직접 보여 줍니까, 간접 추정입니까? |
| 정체성 | 어느 host·service·version·request의 결과입니까? |
| 시간 | 사건 전·중·후 어느 시점입니까? clock 차이는 있습니까? |
| 완전성 | 필요한 시작·종료·거절 event가 모두 있습니까? |
| 무결성 | 조사 대상이 증거를 수정할 수 있습니까? |
| 재현성 | 같은 초기 상태에서 반복할 수 있습니까? |
| 최소성 | 실제 데이터나 불필요한 영향 없이도 충분합니까? |

### 증거가 보장하지 않는 범위

증거는 관찰한 version·초기 상태·입력·시간 범위 안에서만 주장을 지지합니다.

| 증거 | 지지할 수 있는 주장 | 단독으로 보장하지 않는 것 |
|---|---|---|
| unit test | 선택한 함수와 입력에서 기대 결정이 나옴 | 다른 route, middleware, 실제 policy 배포와 production 상태 |
| 격리 행동 검사 | 합성 초기 상태에서 허용·거절·상태 불변성이 재현됨 | 실제 tenant data, 운영 topology와 모든 우회 경로 |
| audit event | 해당 source가 특정 decision을 기록함 | 누락 event의 부재, source 자체가 침해되지 않았음, 실제 상태가 event와 같음 |
| signature·provenance | 검증한 identity가 특정 artifact·build statement에 서명함 | source 내용의 안전성, builder 침해 부재와 runtime의 실제 digest |
| restore drill | 선택한 backup과 절차로 목표 상태를 복원함 | 다른 시점의 backup, production 부하와 공격자가 정본까지 손상하지 않았음 |

따라서 가능한 경우 요청 결과, 보호 상태 oracle, enforcement log와 독립된 정본처럼 서로 다른 실패 모드를 가진 근거를 함께 사용합니다. “로그가 없으므로 사건도 없었다”는 결론은 completeness와 독립성을 별도로 검증하지 않으면 성립하지 않습니다.

## 8. 보안 주장 형식

이 가이드에서는 다음 형식을 권장합니다.

```text
[주체]가 [전제]를 가진 상태에서
[경계]를 통해 [행동]을 시도하면
시스템은 [허용/거절/격리/기록]해야 하며
[증거]로 그 결과를 확인합니다.
```

예:

```text
일반 사용자 token을 가진 subject가
다른 tenant의 report identifier로 download를 요청하면
API는 내용을 반환하지 않고 일정한 거절 응답을 보내며
audit event에는 subject·resource·decision·reason이 남아야 합니다.
```

이 형식은 threat, requirement, test와 detection을 같은 언어로 연결합니다.

## 9. 예방·탐지·복구

예방 통제만으로 안전을 증명할 수 없습니다.

```text
예방: 잘못된 상태 전이를 거부합니다.
탐지: 시도와 통제 실패를 알아챕니다.
대응: 확산을 제한하고 신뢰를 다시 설정합니다.
복구: 정본과 검증 절차로 정상 상태를 재구성합니다.
```

예를 들어 service token을 최소 권한으로 제한해도 발급 정책이 잘못될 수 있습니다. 따라서 비정상 scope 요청을 기록하고, token을 폐기하며, 영향받은 상태를 조사하고, 올바른 credential로 재배포하는 절차가 필요합니다.

## 10. 자동화된 공격자의 의미

사람, script, bot 또는 AI agent처럼 공격자가 자동화돼도 보안 모델의 기본은 같습니다.

- 어떤 capability로 시작했는가?
- 어떤 관찰을 수행할 수 있는가?
- 실패 뒤 다른 경로를 반복할 수 있는가?
- 어떤 identity와 tool을 사용할 수 있는가?
- 어느 budget과 시간 동안 동작하는가?

자동화는 새로운 마법의 취약점을 만들기보다 **탐색 속도, 병렬성, 지속성과 경로 조합 능력**을 높입니다. 방어자는 단일 request만 보지 않고 여러 identity·service·시간에 걸친 상태 변화를 연결해야 합니다. AI 고유의 prompt·tool·memory 문제는 별도 `agentic-systems`와 AI 보안 심화 영역에서 다룹니다.

파일·권한·process 관찰 방법은 `unix-systems`, DNS·transport·TLS의 동작과 실패 계층은 `computer-networks`, 웹 session과 HTTP 기본 동작은 `web-app`이 정본입니다. 이 브랜치는 그 관찰을 보안 상태·불변식·공격 전제와 증거 한계로 해석하는 범위만 소유합니다. 공식 위험 수용, 규제·감사와 법적 증거 절차는 조직의 권한자와 별도 전문 절차에 맡깁니다.

## 11. 이 장의 산출물

하나의 시스템을 골라 다음을 작성합니다.

1. 보호할 자산 5개
2. 각 자산의 보안 상태 1개 이상
3. 시스템 전체의 보안 불변식 5개
4. 불변식마다 prevention·detection·recovery 통제
5. 통제마다 현재 확보된 evidence와 부족한 evidence
6. 가장 중요한 가설 하나와 반증 조건
7. 상태별 정본 소유자·enforcement owner·evidence custodian과 상태 변경 사건
8. 정상·경계·대표 실패 사례와 각 증거가 보장하지 않는 범위

[증거 점검표](../reference/evidence-checklist.md)를 사용합니다.

## 12. 완료 질문

- “인증을 사용한다”와 “허가된 객체만 읽는다”는 왜 다릅니까?
- 설정 파일과 runtime evidence는 왜 구분해야 합니까?
- 같은 로그가 사실과 결론 사이에서 어떤 추가 근거를 요구합니까?
- 보안 불변식을 테스트와 탐지 event로 어떻게 연결합니까?
- 자동화된 공격자가 방어 설계에 추가하는 부담은 무엇입니까?
- 같은 사람이 여러 역할을 맡아도 owner 책임을 분리해 기록해야 하는 이유는 무엇입니까?
- 격리 행동 검사가 통과해도 production의 모든 경로가 안전하다고 결론 내릴 수 없는 이유는 무엇입니까?
