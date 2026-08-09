# Meta 보안 테스트 계획

## 검증할 주장
TEST-001은 REQ-001, TEST-002는 REQ-002, TEST-003은 REQ-003이 미완성 자료를 거부하는지 확인합니다.

## 테스트 행렬
정상 fixture, 필수 field 누락, evidence source 부족을 각각 실행합니다.

## Oracle
valid는 종료 코드 0, invalid와 template는 종료 코드 1이어야 합니다.

## Known-bad Mutation
confirmed finding의 독립 evidence를 한 개로 줄여 검사기를 시험합니다.

## 실행 근거
LAB-NORMAL-OWNER·LAB-NORMAL-JOB과 LAB-DENY-CROSS-OWNER·LAB-DENY-CROSS-JOB, LAB-DETECT-POSITIVE·LAB-DETECT-BENIGN을 포함한 subprocess 종료 코드와 evidence를 확인합니다.

## 한계
finding의 실제 보안 영향과 risk decision은 사람이 검토해야 합니다.
