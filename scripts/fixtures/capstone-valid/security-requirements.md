# Meta 보안 요구사항

## 추적표
FND-001과 THR-001은 REQ-001·TEST-001로, THR-002는 REQ-002·TEST-002로, THR-003은 REQ-003·TEST-003으로 연결합니다.

## 요구사항
REQ-001은 필수 파일을 강제하고 REQ-002는 finding evidence를 요구하며 REQ-003은 문서 ID 추적을 요구합니다.

## Enforcement와 Failure Behavior
parser가 누락을 발견하면 fail-closed로 종료 코드 1을 반환합니다.

## Runtime Evidence
검사 종료 코드와 표준 출력이 meta-test evidence입니다.

## 예외와 Expiry
예외는 없으며 schema 변경은 2027-01-01 전에 재검토합니다.
