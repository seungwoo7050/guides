# 보안 테스트와 assurance

보안 테스트 하나가 시스템 전체의 안전을 증명하지 않습니다. 서로 다른 방법이 서로 다른 약점과 실패를 관찰하며, 각 방법에는 false positive·false negative와 환경 한계가 있습니다.

## 1. assurance question

도구를 고르기 전에 질문을 적습니다.

```text
어떤 security property를 확인하려는가?
어느 component·version·configuration인가?
어떤 actor·state·input을 다루는가?
통과와 실패를 판정하는 oracle은 무엇인가?
어떤 범위는 이 검사로 확인하지 못하는가?
```

## 2. 테스트 계층

### Unit·component test

적합:

- authorization policy function
- parser·validator
- token scope 계산
- state transition
- encoding·serialization

한계:

- 실제 framework wiring·proxy·DB policy·runtime identity를 놓칠 수 있음

### Integration test

적합:

- subject-resource authorization
- DB constraint와 transaction
- service-to-service identity
- storage·queue policy
- audit event

한계:

- production topology·secret·network policy와 다를 수 있음

### End-to-end security test

적합:

- gateway부터 storage까지 실제 decision path
- release configuration
- cross-service trace

한계:

- 느리고 실패 원인을 좁히기 어려움
- 모든 input space를 탐색하지 못함

## 3. 정적 분석

정적 분석은 실행하지 않고 source·bytecode·configuration의 pattern과 data flow를 검사합니다.

잘 찾는 것:

- unsafe API와 source-to-sink path 후보
- secret pattern
- permission·configuration smell
- memory·lifetime bug 후보

놓치기 쉬운 것:

- runtime configuration
- framework가 동적으로 만든 route·policy
- 실제 identity·network·data state
- business logic와 cross-service authorization

경고는 candidate이며 suppression에는 근거와 재검토 trigger를 남깁니다.

## 4. 동적 분석

실행 중인 application에 request를 보내 response와 state를 관찰합니다.

- 실제 parser·routing·middleware 확인
- security header·cookie·error behavior
- common input·authorization failure 탐색

한계:

- 도달한 path만 봄
- test account·state·crawler coverage에 의존
- destructive action 위험
- root cause를 직접 알려 주지 않음

Rules of Engagement와 request budget을 적용합니다.

## 5. fuzzing과 property-based testing

fuzzing은 많은 input으로 crash·hang·invariant violation을 찾습니다.

필수 요소:

```text
명확한 target
bounded input
sanitizer·runtime oracle
time·memory·output limit
crash deduplication
minimal reproducer
persistent corpus
```

crash가 security vulnerability인지 별도 triage합니다. crash가 없다고 parser가 안전한 것도 아닙니다.

property-based test는 example 대신 유지해야 할 속성을 검사합니다.

- 명시적으로 승인된 support·delegation requirement가 없는 foreign tenant access는 deny
- parse→serialize가 허용 schema를 보존
- malformed token은 privilege를 만들지 않음
- 같은 idempotency key의 retry는 유효한 business state transition을 최대 한 번만 만듦

property-based testing은 생성된 input과 sequence에서 반례를 찾고 실패 사례를 축소하는
검사 방법입니다. 탐색하지 않은 전체 input space의 정리를 증명하지 않으며, generator가
만들지 못하는 경계는 그대로 blind spot입니다. 마지막 속성도 분산 전달의 “exactly once”를
증명하지 않습니다. message·request는 중복될 수 있고, idempotency key와 atomic state
transition을 기준으로 관찰 가능한 효과가 `at most once`인지 검사하는 것입니다.

## 6. dependency·artifact 검사

- known vulnerability database matching
- license·origin·support state
- SBOM completeness
- artifact malware·secret scan
- signature·provenance verification

한계:

- advisory가 아직 없을 수 있음
- vulnerable code가 실제 reachable하지 않을 수 있음
- version mapping이 틀릴 수 있음
- clean scan이 source·build integrity를 증명하지 않음

각 evidence가 말하는 범위를 분리합니다.

- signature는 검증한 key identity가 해당 digest에 서명했음을 보이지만 signer와 build가
  안전했음을 보이지 않습니다.
- provenance는 명시된 builder·source·parameter 관계에 대한 attestation이며 그 내용의
  진실성은 issuer와 build 경계의 신뢰에 의존합니다.
- SBOM은 보고된 component inventory이며 완전성·reachability·무취약성을 자동 증명하지
  않습니다.
- reproducible build의 일치는 독립 build 결과를 비교할 근거지만 source 자체의 안전성과
  모든 build input의 신뢰를 증명하지 않습니다.

따라서 source review, builder trust, dependency policy, artifact digest와 runtime identity를
별도 evidence로 연결합니다.

## 7. configuration·policy test

- network·storage·IAM policy
- container·host setting
- CI workflow permission
- secret·logging configuration
- backup·retention

텍스트 lint만으로 runtime effective policy를 증명하지 않습니다. 가능한 경우 실제 principal과 synthetic resource로 allow·deny matrix를 검사합니다.

## 8. 수동 code·design review

수동 검토가 필요한 영역:

- business logic과 state transition
- trust boundary·delegation
- exception·fallback
- cross-service attack path
- recovery·incident capability
- tool이 이해하지 못하는 custom abstraction

검토자는 “보안 코드”만 보지 않고 requirement가 실제 call path와 실패 경로에 연결되는지 봅니다.

## 9. penetration test의 위치

penetration test는 독립적인 시점 검증입니다. secure development를 대신하지 않습니다.

좋은 평가:

- 명확한 scope·objective
- system context와 threat model 사용
- 자동·수동 방법 조합
- 최소 영향 proof
- finding·root cause·remediation·retest
- 발견하지 못한 범위와 time limit 명시

NIST SP 800-115와 OWASP WSTG는 평가 계획과 web test scenario를 구성하는 참고로 사용할 수 있습니다.

## 10. test oracle

security test가 실패를 판정하려면 oracle이 필요합니다.

약한 oracle:

```text
status가 403이면 안전함
```

강한 oracle:

```text
의도한 authorization policy가 foreign subject-resource 조합을 거절함
+ response에 foreign data와 존재 여부 leak가 없음
+ storage·DB state가 바뀌지 않음
+ audit event가 subject·resource·deny reason을 기록
+ downstream service가 호출되지 않음
```

dependency timeout, fixture 누락, process crash처럼 다른 실패가 우연히 공격을 막은 것을
보안 통제 성공으로 오해하지 않습니다. oracle은 decision, 보호 상태, side effect, event를
함께 보고 정상 owner path도 성공하는지 확인해야 `deny-all` 구현을 걸러낼 수 있습니다.

## 11. negative와 abuse test

정상 기능 test에 다음을 추가합니다.

- 다른 owner·tenant·role
- revoked·expired·wrong audience identity
- duplicate·out-of-order·concurrent action
- malformed·oversized·unexpected type
- unavailable dependency와 timeout
- partial write·retry·rollback
- missing log·audit sink failure
- stale cache·old artifact·old credential

## 12. known-bad와 mutation

검사기가 실제 잘못된 구현을 거부하는지 확인합니다.

- authorization call 제거
- resource scope를 wildcard로 변경
- signature verification bypass
- audit field 누락
- error fallback을 allow로 변경

실제 production code를 고의로 약화해 배포하지 않고, isolated fixture 또는 mutation environment에서 검사합니다.

## 13. assurance matrix

| Requirement | Unit | Integration | E2E | Static | Manual | Runtime evidence |
|---|---:|---:|---:|---:|---:|---:|
| object authorization | applicable | applicable | applicable | candidate | applicable | deny audit |
| task-scoped token | calculation | applicable | applicable | policy lint | applicable | issue·use event |
| trusted artifact | verifier | applicable | applicable | workflow review | applicable | runtime digest |
| restore integrity | partial | drill | drill | config review | applicable | restore report |

각 cell은 최소한 `applicable-pass`, `applicable-fail`, `not-run`, `unknown`, `N/A` 중 하나로
판정합니다. 빈 칸을 의도적 비적용으로 해석하지 않습니다. `N/A`라면 requirement 전제가
해당 component·path에서 성립할 수 없다는 근거, 승인한 owner, re-review trigger를 남깁니다.
도구가 없거나 아직 검사하지 않은 상태는 `not-run`이고, 적용 여부 자체를 확인하지 못했다면
`unknown`입니다. threat 수준 test가 통과해도 별도 attack path cell이 자동으로 통과하지
않습니다.

## 14. evidence age

보안 evidence는 시간이 지나면 낡습니다.

- code·configuration 변경
- dependency·tool update
- threat·exploit 공개
- topology·identity change
- test environment drift
- expired certificate·credential

각 검사의 source version, environment, 실행 시점과 re-run trigger를 남깁니다.

## 15. 이 장의 산출물

requirement 8개를 골라 다음을 작성합니다.

1. test method와 이유
2. oracle
3. normal·boundary·failure input
4. known-bad mutation
5. false positive·negative 가능성
6. environment 차이
7. runtime evidence
8. re-run trigger와 evidence expiry
9. path별 applicable·N/A·unknown 판단과 근거

[보안 테스트 template](../reference/security-test-template.md)을 사용합니다.

## 16. 완료 질문

- static analyzer와 dynamic scanner가 서로 대체할 수 없는 이유는 무엇입니까?
- status code 하나가 약한 oracle인 이유는 무엇입니까?
- fuzzing crash와 security vulnerability는 어떻게 다릅니까?
- clean dependency scan이 supply-chain integrity를 증명하지 못하는 이유는 무엇입니까?
- 검사기 자체를 known-bad mutation으로 검증해야 하는 이유는 무엇입니까?
- property-based test가 전체 input space나 exactly-once delivery를 증명하지 못하는 이유는 무엇입니까?
