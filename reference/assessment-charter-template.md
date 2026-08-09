# 보안 평가 계약 Template

## 1. 평가 목적

- 보호할 상태:
- 확인할 주장:
- 성공 조건:
- 명시적으로 확인하지 않는 것:

## 2. 허가

현재 허가는 변경 가능한 versioned state입니다.

| 항목 | 내용 |
|---|---|
| 허가 ID·version | |
| 상태 | `draft | approved | active | paused/revised | expired/revoked` |
| 허가 주체 | |
| 평가 책임자 | |
| 대상 환경 | |
| 시작·종료 시각 | |
| 긴급 연락 | |
| 변경 승인 경계 | |

### 상태 이력과 재승인

| 시각 | 이전 → 새 상태 | 변경 사건 | 승인 authority | Evidence |
|---|---|---|---|---|

- scope·asset 변경:
- 평가 identity·credential 변경:
- 시간·허용 행동·예산 변경:
- pause·revoke를 enforcement point에 전파하는 owner와 확인 방법:

## 3. 범위

### In scope

| Asset | Environment | Identity | 허용 행동 | Evidence source |
|---|---|---|---|---|

### Out of scope

| Asset·provider | 제외 이유 | 발견 시 행동 |
|---|---|---|

## 4. 허용·금지 행동

### 허용

- TODO

### 금지

- TODO

## 5. 실행 예산

- 최대 요청 수:
- 최대 동시성:
- 최대 데이터 크기:
- 최대 실행 시간:
- 최대 비용:
- 허용된 도구:

## 6. 중단 조건

| 관찰 상태 | 즉시 행동 | 연락 대상 | Evidence 처리 |
|---|---|---|---|

## 7. 증거 처리

- 저장 위치:
- 분류:
- redact 기준:
- 접근자:
- 보존 기간:
- 삭제 확인:

## 8. Cleanup과 복구

- 임시 identity·credential:
- process·container·network·volume:
- 설정 복원:
- 정상 기능 재검증:
- 실패한 cleanup owner:

## 9. 승인

| 역할 | 이름·ID | 승인 시각 | 조건 |
|---|---|---|---|
