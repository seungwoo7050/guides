# Meta 보안 테스트 계획

## 검증할 주장
REQ-001, REQ-002, REQ-003이 미완성 자료를 거부하는지 확인합니다.

## 테스트 행렬
정상 fixture, 필수 field 누락, evidence source 부족을 각각 실행합니다.

## Oracle
valid는 종료 코드 0, invalid와 template는 종료 코드 1이어야 합니다.

## Known-bad Mutation
confirmed finding의 독립 evidence를 한 개로 줄여 검사기를 시험합니다.

## 실행 근거
subprocess 종료 코드와 error message를 별도 meta-test가 확인합니다.

## 한계
finding의 실제 보안 영향과 risk decision은 사람이 검토해야 합니다.
