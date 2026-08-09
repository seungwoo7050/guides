# 실습 06 — 사고 timeline과 복구 근거

사고 기록은 모든 로그를 시간순으로 복사하는 문서가 아닙니다. 의사결정자가 **무엇을 알고 있었고, 무엇을 몰랐으며, 어떤 조치가 어떤 결과를 만들었는지** 재구성할 수 있어야 합니다.

## 초기 자료

- [`inputs/event-log.jsonl`](inputs/event-log.jsonl)
- [`inputs/operator-notes.md`](inputs/operator-notes.md)
- [`template/incident-timeline.md`](template/incident-timeline.md)

## 작업공간과 시작 상태

저장소 루트에서 다음을 실행합니다.

```sh
python3 scripts/new_workspace.py exercise 06-incident-timeline
```

작업 경로는 `exercises/06-incident-timeline/work/`입니다. 생성된 `incident-timeline.md`는 `FACT` 예시 한 행도 `TODO` 상태이며, 입력에는 상충하는 시간과 불완전한 actor가 있습니다. 빈칸을 추측으로 채우지 말고 확인되지 않은 항목은 `UNKNOWN`으로 유지합니다.

## 상황

합성 서비스에서 worker credential이 예상 scope 밖 object를 읽은 event가 발견됐습니다. 같은 시각에 mutable image tag가 다른 digest를 가리키기 시작했습니다. event가 지연·중복됐고 일부 component의 actor field가 없습니다.

## 작업

1. event time, ingest time, discovery time과 decision time을 구분합니다.
2. 각 항목을 다음 중 하나로 표시합니다.
   - `FACT`
   - `HYPOTHESIS`
   - `DECISION`
   - `ACTION`
   - `RESULT`
   - `UNKNOWN`
3. 최초 known-bad, 마지막 known-good와 현재 조사 범위를 기록합니다.
4. containment 후보별 보존되는 evidence와 운영 영향을 비교합니다.
5. credential, artifact와 data의 신뢰 회복 조건을 작성합니다.
6. 복구 뒤 사용자 경로와 보안 통제를 어떻게 검증할지 작성합니다.
7. communication 대상과 확정되지 않은 표현을 분리합니다.

## 금지

- tag 변경만으로 공급망 침해를 확정하지 않습니다.
- log 부재를 무행동의 증거로 사용하지 않습니다.
- 가장 먼저 log·container·host를 삭제하도록 제안하지 않습니다.
- credential 폐기만으로 이미 생성된 artifact와 data를 신뢰하지 않습니다.
- 복구 완료를 process running 상태로만 판정하지 않습니다.

## 제출 evidence

- `work/incident-timeline.md`: source·confidence가 있는 정규화된 timeline과 discovery·decision 기록
- known-good/known-bad 범위, 중복·지연 event의 처리와 unresolved unknown
- containment 후보별 evidence 보존, 운영 영향, 가역성과 실제 결정 근거
- credential·artifact·data별 trust 재수립 조건, 정상 기능·보안 통제 recovery evidence
- communication 대상, 후속 owner, production에서 별도 승인이 필요한 검증 계획

## 반드시 검토할 사례

| 종류 | 사례 | 기대하는 판단 |
|---|---|---|
| 정상 | trusted source에서 재빌드한 고정 digest와 회전된 credential로 정상·보안 검사를 통과 | 각각의 trust anchor와 독립 recovery evidence를 기록한다. |
| 경계 | event와 ingest 순서가 다르거나 actor가 누락되어 최초 시점을 확정할 수 없음 | 시간 종류를 분리하고 조사 범위와 `UNKNOWN`을 유지한다. |
| 실패 | credential만 폐기하고 기존 artifact·data를 신뢰하거나 process 실행만으로 복구를 선언 | 관련 상태마다 신뢰 재수립과 회귀·탐지 evidence가 없으면 복구 완료를 거부한다. |

## 완료 rubric

- [ ] 모든 timeline 항목에 source와 confidence가 있습니다.
- [ ] 사실과 원인 가설이 분리됐습니다.
- [ ] containment가 evidence에 미치는 영향이 있습니다.
- [ ] scope expansion 조건이 있습니다.
- [ ] trusted rebuild·credential rotation·data review가 연결됩니다.
- [ ] 사용자 기능과 보안 상태의 recovery evidence가 있습니다.
- [ ] unresolved unknown과 후속 owner가 있습니다.

## 사람 검토와 자동화 한계

Reviewer는 “사실과 원인 가설이 명확히 갈리는가?”, “containment가 증거와 사용자에게 주는 영향을 비교했는가?”, “credential·artifact·data마다 신뢰의 출발점이 있는가?”, “release·risk acceptance authority와 기술 reviewer가 구분되는가?”를 질문합니다. 자동 검사는 timestamp·필수 열·참조 형식을 확인할 수 있지만 인과 관계, 조사 범위의 충분성, 신뢰 회복, release 결정의 타당성을 인증하지 않습니다.
