# API and Status Contract

## 공통 식별자

이 계약의 canonical tuple은 (`svc-payments`, `env-payments-staging`, `op-payments-staging-v3`, `tenant-checkout`, `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, `stateless-http/v3`)이다. 모든 event와 evidence는 tuple 중 관련 ID와 request generation을 가진다.

## Resource와 상태

`EnvironmentRequest.spec`에는 service, tenant, profile version, artifact digest와 desired parameters가 들어간다. `status`에는 `observedGeneration`, condition, active operation, first failure, owner, retryability, partial effects와 evidence refs가 들어간다. secret 값과 provider credential은 spec/status에 저장하지 않는다.

조건은 `Accepted`, `Progressing`, `Ready`, `Blocked`, `Degraded`, `Retired`다. `Ready=True`는 policy decision, artifact digest, IaC observation, workload readiness와 외부 smoke evidence가 모두 같은 generation을 가리킬 때만 허용한다. `Degraded`는 서비스 가능한 상태에서 drift/부분 실패가 있다는 뜻이며 성공의 별칭이 아니다. `Retired`는 활성 resource가 없고 tombstone만 남은 terminal state다.

## Operation과 Evidence

`op-payments-staging-v3`는 request acceptance 시 원자적으로 만들어진다. 단계마다 `started_at`, `finished_at`, owner, attempt, input hash, output reference를 기록한다. evidence는 inline 성공 문자열이 아니라 content hash를 가진 typed record이며 source, observed generation과 expiry를 포함한다.

idempotency key는 tenant+operation kind scope에서 canonical request hash와 결합한다. 같은 key·같은 hash는 기존 operation을 반환한다. 다른 hash는 `IDEMPOTENCY_CONFLICT`와 기존 operation ref를 반환하고 effect를 만들지 않는다. operation journal은 retry 뒤에도 첫 실패와 이미 생성된 provider ID를 잃지 않는다.

## 정상·경계·실패

- 정상: admission 후 `Progressing`; artifact·policy·runtime·smoke evidence가 모이면 `Ready`.
- 경계: `tenant-checkout`이 quota 2에 도달하면 세 번째 환경은 `QUOTA_EXCEEDED`로 거부되고 다른 tenant queue는 진행한다.
- 실패: provider가 network를 만든 뒤 runtime 생성이 실패하면 `Degraded`, `partial_effects=[network-id]`, cleanup owner와 retry/retire action을 공개한다.
- drift: ordinary live edit는 desired digest로 수렴하고 before/after를 남긴다. 승인된 break-glass는 만료까지 관찰하되 종료 후 자동 수렴한다.
- retirement: `svc-payments` active environment/operation/credential/exception을 닫고 audit tombstone을 남기며 다른 service 상태는 보존한다.

unknown condition이나 evidence source 장애는 `Ready`로 낙관하지 않는다. client는 retryable code와 `retry_after`를 따르고, controller는 상태 변경 없이 동일 observation을 반복 적용할 수 있어야 한다.
