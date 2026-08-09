# 보안 Requirement Template

## Requirement 식별

- ID:
- 연결 threat:
- 적용 asset·flow:
- enforcement owner:

## 계약

```text
[대상]은 [조건]에서 [허용 상태]만 만들 수 있어야 하며,
[거부 상태]가 요청되면 [실패 행동]을 수행하고 [evidence]를 남겨야 합니다.
```

## 상태

- 허용 상태:
- 거부 상태:
- fail-open / fail-closed 결정:
- unavailable control에서의 동작:
- timeout·retry·duplicate에서의 동작:

## Identity와 데이터

- direct actor:
- effective actor:
- delegated identity:
- credential scope·expiry:
- resource ownership source:
- sensitive data handling:

## 검증

| Case | Initial state | Action | Expected state | Oracle | Evidence |
|---|---|---|---|---|---|
| 정상 | | | | | |
| 경계 | | | | | |
| 실패 | | | | | |
| known-bad | | | | | |

## 운영

- telemetry:
- alert 또는 investigation use:
- recovery:
- exception risk owner:
- risk acceptance authority·승인 근거:
- expiry:
- compensating control과 monitoring:
- 재검토 trigger:
