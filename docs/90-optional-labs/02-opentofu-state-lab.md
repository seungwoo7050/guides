# OpenTofu state와 drift 실습

로컬 file resource 또는 폐기 가능한 sandbox provider를 사용해 configuration, state와 실제 resource의 차이를 관찰합니다. OpenTofu를 예로 들며 Terraform도 같은 핵심 경계를 관찰할 수 있습니다.

## 목표

- configuration과 state가 같은 것이 아님을 확인합니다.
- resource address와 외부 object identity를 구분합니다.
- plan이 현재 refresh 결과에 의존한다는 사실을 봅니다.
- out-of-band 변경과 drift를 탐지합니다.
- state move/import/remove가 실제 resource 수명과 어떻게 다른지 확인합니다.

## 안전 기준

- local file 또는 비용 없는 sandbox resource를 사용합니다.
- production backend와 credential을 사용하지 않습니다.
- state에는 민감 값이 포함될 수 있으므로 Git에 추가하지 않습니다.
- backend 변경 전 backup과 복원 경로를 확인합니다.

## 기본 흐름

1. 작은 configuration을 작성합니다.
2. `init`, `plan`, `apply` 뒤 resource와 state를 각각 확인합니다.
3. 실제 resource를 도구 밖에서 수정합니다.
4. 새 plan에서 drift가 어떻게 표현되는지 확인합니다.
5. stale plan을 일부러 만들고 configuration 또는 resource를 바꾼 뒤 apply 결과를 관찰합니다.
6. resource address rename을 state move 없이 수행한 경우와 move한 경우의 차이를 비교합니다.
7. destroy와 state remove의 차이를 기록합니다.

## 관측 질문

- State는 desired state입니까, observed mapping입니까?
- State lock이 없을 때 동시에 apply하면 어떤 race가 생깁니까?
- Drift를 자동 수정해야 합니까, 조사 후 승인해야 합니까?
- Resource를 rename할 때 replace가 발생하면 어떤 data와 endpoint가 영향을 받습니까?
- State만 제거하면 실제 resource와 비용은 어떻게 됩니까?

## Evidence

- configuration revision
- plan identity와 생성 시점
- apply 결과
- state resource address와 external ID
- drift 전후 plan
- migration 명령과 backup
- destroy/cleanup 결과

실습 뒤 `.terraform`, `.tofu`, state, plan과 생성 resource를 명시적으로 정리합니다.
