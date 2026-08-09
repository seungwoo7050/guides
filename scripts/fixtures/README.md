# Capstone 검사기 Meta-test Fixture

이 디렉터리는 LedgerLab의 정답이 아닙니다. `verify_capstone.py`가 완성된 구조를 허용하고 known-bad 구조와 미완성 template를 거부하는지 확인하기 위한 작은 합성 자료입니다.

- `capstone-valid`: 일곱 합성 candidate의 completeness, 구조·trace·재실행 behavior evidence 최소 조건을 만족합니다.
- `scenario`: meta-test 전용 candidate 목록이며 LedgerLab 후보의 정답이 아닙니다.
- `capstone-invalid`: 이전 status 계약을 사용하는 legacy known-bad 자료로, 현재 verifier가 거부해야 합니다.
- `scripts/test_verify_capstone.py`는 valid fixture를 임시 복제해 candidate 누락, 깨진 trace, 변조 evidence, 잘못된 날짜, 대소문자 중복 ID, 승인 근거 없는 risk accept와 미완성 template를 각각 기대한 오류 코드로 거부하는지 확인합니다.

실제 Capstone 판단, candidate status와 release decision은 제공하지 않습니다.
