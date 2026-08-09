# 위협 모델 Template

## 시스템 한 문장

누가 어떤 기능을 사용하며, 어떤 상태가 반드시 보호돼야 하는지 작성합니다.

## 범위와 환경

- In scope:
- Out of scope:
- Version·build·configuration:
- Evidence age:

## 자산과 보안 목표

| Asset | 업무·위험 owner | 상태 정본 owner | Enforcement owner | Evidence custodian | 보호할 상태 | 실패 결과 | 복구 원본 |
|---|---|---|---|---|---|---|---|

## 행위자와 capability

| Actor | 초기 capability | 얻을 수 있는 capability | 신뢰 근거 | 제한 |
|---|---|---|---|---|

## 신뢰 경계와 흐름

| Flow | Source → Destination | Data | Identity | Validation | Evidence |
|---|---|---|---|---|---|

## 위협

### THR-001 — 제목

```text
[actor]가 [precondition]에서 [boundary/flow]를 이용해
[protected state]를 [undesired state]로 바꿀 수 있다.
```

- Observable evidence:
- Current control:
- Control owner:
- Bypass·failure mode:
- Impact:
- Assumption·unknown:

## 공격 경로

| Step | 이전 capability | 사건·약점 | 새 capability | Evidence | Choke point |
|---:|---|---|---|---|---|

## 정상·경계·대표 실패

| 종류 | 초기 상태와 사건 | 기대 상태·불변식 | 관찰 evidence | 보장하지 않는 범위 |
|---|---|---|---|---|
| 정상 | | | | |
| 경계 | | | | |
| 실패 | | | | |

## Edge 검증 수준

| Edge | 직접 실행·관찰 | 문서·snapshot 추론 | Oracle | 남는 종단 간 가정 |
|---|---|---|---|---|

한 edge의 관찰을 전체 공격 경로 성공으로 확대하지 않습니다. 결합하지 못한 time·identity·version 조건은 `UNKNOWN`으로 남깁니다.

## Prevention·Detection·Recovery mapping

| Threat·path | Prevention 또는 N/A 근거 | Detection 또는 N/A 근거 | Recovery 또는 N/A 근거 | Owner·evidence |
|---|---|---|---|---|

## 우선순위

- Path가 도달하는 asset:
- 필요한 attacker capability:
- 현재 exposure:
- 탐지 가능성:
- 수정 비용·운영 영향:
- 결정과 owner:

## 재검토 trigger

- architecture·identity·data flow 변경
- 새 public entry point
- release·dependency·policy 변경
- incident 또는 새로운 evidence
