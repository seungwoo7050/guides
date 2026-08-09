# Identity·secret·policy와 공급망

## 목표

사람·workload·automation 권한, secret 수명, policy 단계와 source-to-runtime trust chain을 설계합니다.

## 먼저 읽을 문서

- [`11-identity-secrets-and-policy.md`](../../docs/11-identity-secrets-and-policy.md)
- [`16-supply-chain-and-platform-security.md`](../../docs/16-supply-chain-and-platform-security.md)

## 시작 상태

`skeleton/submission.json`은 의도적으로 미완성입니다. 원본을 직접 수정하지 말고 `.workspace/`에 복사합니다.

```sh
mkdir -p .workspace/08-identity-policy
cp exercises/08-identity-policy/skeleton/submission.json \
  .workspace/08-identity-policy/submission.json
```

## 수행할 작업

1. Identity별 attestation, scope, TTL과 revocation을 작성합니다.
2. Secret 원본·reference·materialized credential을 분리합니다.
3. Policy를 early feedback부터 admission/runtime까지 배치합니다.
4. Exception과 break-glass에 scope·owner·expiry·audit를 둡니다.
5. Source, builder, artifact와 deployment verifier의 신뢰 경로를 연결합니다.

필드 이름과 최소 구조는 `contract.json`이 정의합니다. `reference/submission.json`은 Northstar 시나리오의 한 가지 답이며, 자신의 설계가 다른 경우 결과·소유권·실패·증거가 왜 다른지 설명합니다.

## 반드시 다룰 실패

- CI와 controller가 사람의 장기 token을 공유합니다.
- Secret plaintext가 Git, artifact 또는 log에 남습니다.
- Policy를 마지막 admission 단계에서 처음 알립니다.
- SBOM 또는 signature 하나로 공급망 전체가 안전하다고 주장합니다.

## 검증

```sh
python3 scripts/verify_submission.py \
  exercises/08-identity-policy/contract.json \
  .workspace/08-identity-policy/submission.json
```

검사기는 필수 field, 배열 항목, stable value와 placeholder 부재를 확인합니다. 실제 조직에서 설계가 옳거나 실제 cloud/Kubernetes 동작이 안전하다는 사실은 증명하지 않습니다.

## 완료 근거

- 검사 결과
- 선택한 상태와 책임 경계의 이유
- 자동 검증하지 못한 주장
- 실제 프로젝트에서 다음에 확인할 evidence
- reference와 다른 중요한 결정 및 trade-off
