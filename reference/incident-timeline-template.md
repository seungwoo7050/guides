# Incident Timeline Template

## 기본 정보

- Incident ID:
- 발견 시각:
- Incident commander:
- Severity와 현재 근거:
- 사용자·asset 범위:

## 시간 기준

- Event time source:
- Ingest delay:
- Clock skew:
- Discovery time:
- Decision log location:

## Timeline

| Time 종류 | Time | Type | Source | Statement | Confidence | Evidence ID | Owner·next step |
|---|---|---|---|---|---|---|---|
| event | | FACT | | | | | |

Type은 `FACT`, `HYPOTHESIS`, `DECISION`, `ACTION`, `RESULT`, `UNKNOWN` 중 하나를 사용합니다.

## Scope

- Earliest-observed known-bad:
- Last-known-good:
- 두 시점 사이의 미확인 시간 구간과 실제 최초 침해 시각을 단정하지 못하는 이유:
- 확인된 asset·identity:
- 조사 중 asset·identity:
- 제외 근거:
- scope 확대 조건:

## Evidence preservation

- 원본 source:
- immutable copy·hash:
- access log:
- redact:
- retention:

## Containment

| 후보 | 기대 효과 | Evidence 영향 | 사용자 영향 | 가역성 | 승인·결정 |
|---|---|---|---|---|---|

## Eradication

- root cause:
- compromised identity·artifact·data:
- trusted rebuild source:
- similar path review:

## Recovery

- credential·artifact·data별 독립 trust anchor:
- 복원 순서:
- 사용자 기능 검증:
- 보안 control 검증:
- 강화 monitoring 기간:
- rollback criteria:
- 재수립하지 못한 신뢰와 남은 `UNKNOWN`:

## Communication

| 대상 | 확정 사실 | 미확인 표현 | 담당자 | 시각 |
|---|---|---|---|---|

## 후속 조치

| Action | Root cause·control gap | Owner | Due | Verification | Status |
|---|---|---|---|---|---|
