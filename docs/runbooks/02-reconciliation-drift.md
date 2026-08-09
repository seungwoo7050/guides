# Reconciliation drift

## 증상

- Controller가 같은 resource를 반복 update합니다.
- Desired revision과 live state가 계속 달라집니다.
- 수동 변경이 되돌아가거나 반대로 desired state가 적용되지 않습니다.
- 두 controller가 field를 번갈아 수정합니다.

## 영향 확인

- 단순 metadata drift인가, traffic·identity·data 경계에 영향이 있는가?
- 하나의 object인가, profile/cluster 전체인가?
- 반복 update가 API server와 controller capacity를 소진하는가?
- 긴급 변경이 자동으로 되돌아가 사용자 영향이 커지는가?

## 검사 순서

1. Desired source revision과 rendered object를 고정합니다.
2. Live object의 generation, managed fields, event를 확인합니다.
3. Diff를 field 단위로 분류합니다.
4. Admission default/mutation, runtime field, 다른 controller와 manual actor를 찾습니다.
5. GitOps/IaC/platform controller 중 single writer가 누구인지 확인합니다.
6. 최근 policy/controller/version 변경을 확인합니다.
7. Reconcile interval과 update rate를 측정합니다.

## Drift 분류

- 정상 runtime status
- server/defaulted field
- admission mutation
- manual emergency change
- unauthorized manual change
- controller ownership conflict
- stale desired source
- conversion/version difference

## 안전한 완화

- 정상 runtime field는 desired comparison에서 제외하거나 owner를 명시합니다.
- 두 controller 충돌이면 한 writer를 pause하고 ownership을 수정합니다.
- 긴급 변경이면 break-glass scope를 확인하고 desired source에 반영합니다.
- 잘못된 desired state면 안전한 previous revision으로 revert합니다.
- Reconcile storm이면 affected resource 또는 controller shard를 제한합니다.

Live object만 수동으로 계속 고치지 않습니다. 정본과 controller가 그대로면 다시 drift합니다.

## 복구 판정

- Desired와 live의 의미 있는 field가 일치합니다.
- Reconcile update rate가 정상화됩니다.
- Controller condition이 current generation을 관찰합니다.
- Emergency pause와 credential이 종료됩니다.
- Unauthorized actor와 변경 경로가 차단됩니다.
- Audit에 before/after와 owner가 남습니다.

## 후속 action

- field ownership 문서·schema
- mutation 결과 visibility
- drift alert와 rate guard
- break-glass workflow
- controller compatibility test
