# Meta 수정 계획

## 즉시 완화
PATCH-001은 FND-001 구조 오류가 발견되면 완료 표시를 차단합니다.

## 원인 수정
PATCH-001에서 FND-001의 상태별 schema와 behavior evidence 재실행 검사를 verifier에 추가합니다.

## 유사 경로 검토
다른 status와 Markdown trace에도 같은 누락이 있는지 확인합니다.

## Credential·Artifact·Data 정리
이 fixture는 실제 credential과 data를 사용하지 않으며 임시 artifact를 제거합니다.

## 회귀 검사
valid 통과, invalid 거부, template 거부를 반복합니다.

## 배포와 Rollback
검사기 변경은 이전 script로 되돌릴 수 있으며 결과 차이를 기록합니다.

## 재검증과 종료 조건
세 meta-test가 예상 종료 코드를 만들면 구조 수정이 완료됩니다.
