# Meta 격리 행동 검토

## End-to-end Trace

FND-001 → THR-001 → REQ-001 → TEST-001 → PATCH-001 → DET-001 → incident/recovery → release decision을 같은 근거 묶음으로 추적합니다.

## 취약 상태와 State Oracle

canonical skeleton에서 LAB-VULN-CROSS-OWNER와 LAB-VULN-CROSS-JOB이 allow이고 실행 전후 state SHA-256이 같은 결과를 취약 proof로 사용합니다.

## Causal Root Cause

owner와 tenant를 같은 결정에서 비교하지 않고 credential의 job, prefix, expiry, revoke context를 모두 강제하지 않는 것이 FND-001의 causal mechanism입니다.

## 최소 Patch와 정상 기능 보존

PATCH-001은 authorization 정본에서 누락된 비교와 audit·detector 계약을 복원합니다. LAB-NORMAL-OWNER와 LAB-NORMAL-JOB이 계속 통과하는지를 정상 기능 oracle로 사용합니다.

## 정상·경계·Known-bad 근거

TEST-001은 LAB-DENY-CROSS-OWNER·LAB-DENY-CROSS-JOB, TEST-002는 LAB-DENY-PREFIX-CONFUSION·LAB-DENY-AT-EXPIRY, TEST-003은 LAB-DENY-CREDENTIAL-ACTOR·LAB-DENY-MISSING-JOB-CONTEXT를 확인합니다.

## Corrected Deny Event

FND-001과 연결된 EV-LAB-002·EV-LAB-006 deny event가 actor, effective actor, credential, tenant, job, resource, correlation과 policy version을 보존합니다.

## 탐지 Positive·Negative

DET-001은 LAB-DETECT-POSITIVE와 LAB-DETECT-CORRELATION을 positive로, LAB-DETECT-BENIGN을 negative로 사용해 duplicate와 unrelated correlation을 구분합니다.

## Cleanup 근거

외부 network와 process를 만들지 않고 임시 evidence 디렉터리는 검사 종료 시 제거됩니다. tracked scenario와 합성 state hash가 실행 전후 같습니다.

## 검증 한계

이 evidence는 합성 in-memory Python contract만 보장합니다. OS sandbox가 아니므로 검토한 fixture code만 실행하며 실제 IAM, network, provider log와 production 복구를 증명하지 않습니다.
