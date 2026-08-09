# 실습 05 — 보안 telemetry와 탐지 설계

탐지는 이벤트를 많이 저장하는 일이 아니라, **어떤 보안 상태 변화가 발생했는지 재구성할 수 있도록 관찰 계약을 설계하는 일**입니다.

## 초기 자료

- [`inputs/event-dictionary.md`](inputs/event-dictionary.md)
- [`inputs/events.jsonl`](inputs/events.jsonl)
- [`template/detection-plan.md`](template/detection-plan.md)

## 작업공간과 시작 상태

저장소 루트에서 다음을 실행합니다.

```sh
python3 scripts/new_workspace.py exercise 05-detection-engineering
```

작업 경로는 `exercises/05-detection-engineering/work/`입니다. 생성된 `detection-plan.md`의 event field와 `DET-TODO`는 비어 있고, 입력 event에는 의도적으로 identity 누락·지연·중복이 있습니다. 입력을 정답 label로 바꾸지 말고 관측 가능한 범위와 blind spot을 남깁니다.

## 상황

`ReportFlow`의 audit event는 component마다 field가 다릅니다. 일부 요청은 사용자에서 service로 위임되고, worker는 한 job 동안 여러 object를 읽고 씁니다. 운영 팀은 “비정상 object access” 경보를 원하지만 정상 batch 작업과 구분 기준이 없습니다.

## 작업

1. canonical event schema를 설계합니다.
2. direct actor, effective actor, delegated identity와 credential ID를 구분합니다.
3. resource와 authorization decision을 기록합니다.
4. 최소 세 개의 detection hypothesis를 작성합니다.
5. known-positive와 known-negative fixture를 지정합니다.
6. alert별 triage 질문과 첫 containment 후보를 작성합니다.
7. 수집 지연·누락·중복·시간 차이에서 analytic이 어떻게 실패하는지 기록합니다.
8. pipeline health 자체를 감시하는 지표를 정의합니다.

## 제한

- actor가 없는 event를 임의 사용자에게 귀속하지 않습니다.
- threshold 하나를 보편적인 공격 판정으로 사용하지 않습니다.
- event가 없다는 사실을 행동이 없었다는 뜻으로 사용하지 않습니다.
- 원본 event를 잃고 정규화 결과만 저장하지 않습니다.

## 제출 evidence

- `work/detection-plan.md`: canonical event schema, identity chain과 최소 세 detection hypothesis
- known-positive·known-negative가 각 hypothesis의 조건을 충족하거나 충족하지 않는 근거
- 중복·out-of-order·late event 처리와 원본 event로 되돌아가는 provenance
- alert triage 질문, 첫 containment 후보, pipeline health와 blind spot

## 반드시 검토할 사례

| 종류 | 사례 | 기대하는 판단 |
|---|---|---|
| 정상 | 같은 owner·job 안의 허용된 batch object 접근 | known-negative로 보존하고 정상 행위를 공격으로 만들지 않는다. |
| 경계 | 같은 event가 중복 수집되거나 event time보다 ingest time이 늦고 순서가 바뀜 | event ID·correlation과 명시한 window로 중복·순서를 처리한다. |
| 실패 | actor 또는 authorization decision이 없는데 cross-owner 접근을 특정 사용자 공격으로 확정 | `unknown`과 telemetry gap을 기록하고 pipeline 장애를 별도 신호로 탐지한다. |

## 완료 rubric

- [ ] event마다 actor·resource·action·outcome·correlation이 정의됩니다.
- [ ] event time과 ingest time을 구분합니다.
- [ ] hypothesis가 공격 이름이 아니라 상태 변화로 작성됐습니다.
- [ ] known-positive와 known-negative가 있습니다.
- [ ] 중복과 out-of-order 처리 기준이 있습니다.
- [ ] alert에서 원본 evidence로 이동할 수 있습니다.
- [ ] pipeline 장애와 실제 조용한 상태를 구분할 수 있습니다.

## 사람 검토와 자동화 한계

Reviewer는 “탐지 가설이 어떤 보호 상태 변화를 말하는가?”, “positive와 negative가 실제로 독립된 반례인가?”, “중복·지연 처리로 alert가 숨거나 증폭되지 않는가?”, “false positive·false negative와 수집 blind spot을 누가 검토하는가?”를 질문합니다. 자동 검사는 JSONL 형식, 필드와 fixture 참조는 확인할 수 있지만 precision·recall, threshold 적절성, containment의 운영 영향을 보장하지 않습니다.
