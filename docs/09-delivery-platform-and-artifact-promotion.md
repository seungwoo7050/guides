# Delivery platform과 artifact promotion

Delivery platform은 팀마다 작성한 CI script를 중앙에서 대신 관리하는 것이 아닙니다. Source 변경이 어떤 검증을 거쳐 어떤 artifact가 됐고, 그 artifact가 어느 환경에 어떤 configuration과 함께 배포됐는지 추적 가능한 **전달 계약**을 제공합니다.

`web-infra`는 한 서비스의 immutable image, release manifest, staged deployment와 rollback을 소유합니다. 이 장은 그 기준을 여러 저장소·팀·환경에서 재사용하도록 확장합니다.

Reusable workflow와 OCI content identity의 공식 기준은 [source index의 delivery](../reference/source-index.md#delivery)를 확인합니다. 특정 CI YAML을 복제하지 않고 typed input, 최소 권한, immutable digest와 evidence를 플랫폼 계약으로 적용합니다.

## 1. Build once, promote many

같은 source revision을 환경마다 다시 build하면 서로 다른 dependency, base image와 build time input 때문에 artifact가 달라질 수 있습니다.

권장 흐름:

```text
source revision
→ 검증된 build
→ immutable artifact digest
→ provenance·SBOM·test evidence
→ preview
→ staging
→ production
```

환경 차이는 artifact 재생성이 아니라 versioned configuration과 external dependency binding으로 표현합니다.

### 분리할 항목

| 구분 | 예 |
|---|---|
| build input | source commit, lockfile, build image, compiler flags |
| artifact | OCI image digest, package checksum |
| release configuration | replica, route, feature flag, external endpoint reference |
| secret | runtime에 전달되는 credential reference |
| deployment result | environment, timestamp, controller revision, smoke evidence |

Artifact 안에 environment secret이나 production URL을 bake하지 않습니다.

## 2. Delivery pipeline의 상태 기계

Pipeline을 job 목록보다 상태 전이로 봅니다.

```text
Candidate
→ Built
→ Verified
→ Published
→ Eligible(environment)
→ Deploying
→ Observed
→ Promoted
```

실패 상태:

```text
BuildFailed
VerificationFailed
PolicyBlocked
DeploymentFailed
ObservationFailed
PromotionRejected
Cancelled
```

각 전이에는 다음이 필요합니다.

- 입력 identity
- 실행 주체
- policy version
- 생성 evidence
- timeout과 retry
- rollback 또는 재시작 경계

CI 화면의 초록색 표시만으로 release를 증명하지 않습니다. Release record가 source, artifact와 environment result를 연결해야 합니다.

## 3. Reusable workflow의 계약

중앙 workflow는 복사하는 YAML보다 interface를 제공해야 합니다.

입력 예:

- language/build profile
- test command 또는 standard build target
- artifact name
- runtime profile
- security classification
- optional capability

출력 예:

- artifact digest
- SBOM location과 digest
- provenance statement
- test report identity
- policy decision
- release candidate ID

Workflow version은 고정하고 migration 경로를 제공합니다.

```yaml
uses: northstar/platform-workflows/build-service@v4
with:
  profile: java-21
  artifact: checkout
```

`@main`처럼 변하는 ref를 사용하면 같은 commit의 재실행 결과를 설명하기 어렵습니다.

## 4. Trusted build와 pull request 경계

외부 또는 신뢰하지 않은 contribution이 secret과 production credential을 사용할 수 없게 합니다.

분리 예:

```text
Pull request validation
- untrusted code
- read-only token
- no production secret
- artifact는 promotion 불가

Trusted branch build
- protected revision
- isolated build identity
- signing/provenance 가능
- immutable registry publish

Deployment
- build identity와 분리
- environment-specific authorization
- artifact digest만 입력
```

Artifact를 build한 주체가 자동으로 production 배포 권한까지 갖지 않게 합니다.

## 5. Evidence bundle

Release candidate에는 최소한 다음을 연결합니다.

```json
{
  "source": {
    "repository": "northstar/checkout",
    "revision": "commit-sha"
  },
  "artifact": {
    "uri": "registry.example/checkout",
    "digest": "sha256:..."
  },
  "build": {
    "workflowVersion": "build-service/v4",
    "builderIdentity": "spiffe://northstar/build/runner",
    "provenance": "artifact://provenance/..."
  },
  "verification": {
    "tests": "artifact://test-report/...",
    "sbom": "artifact://sbom/...",
    "policyDecision": "allow"
  }
}
```

Evidence가 존재한다는 사실과 충분하다는 판단은 다릅니다. Workload risk에 따라 필요한 gate를 profile로 정합니다.

## 6. Environment promotion

Promotion은 artifact를 복사하는 것보다 **같은 artifact가 다음 환경에서 사용 가능하다는 결정**입니다.

Promotion 조건 예:

- 이전 환경 deployment와 smoke 성공
- 최소 관찰 시간 통과
- 오류율·latency guardrail 충족
- database migration compatibility 확인
- production policy와 승인
- known incident 또는 freeze 여부
- rollback artifact와 procedure 확인

사람 승인이 필요해도 evidence를 다시 수동으로 모으지 않게 합니다.

## 7. Progressive delivery

전체 traffic을 한 번에 새 release로 이동하지 않을 수 있습니다.

- rolling update
- canary
- blue/green
- traffic shadow
- feature flag

Platform은 기법 이름보다 다음 계약을 제공해야 합니다.

- 어떤 population과 traffic을 새 version에 노출하는가?
- 비교할 SLI와 최소 sample은 무엇인가?
- 자동 중단 조건은 무엇인가?
- database와 external effect가 두 version 공존을 허용하는가?
- rollback이 artifact만 되돌리면 충분한가?
- operator가 수동으로 개입할 때 audit가 남는가?

잘못된 SLI를 기준으로 자동 promotion하면 빠르게 실패를 확산시킵니다.

## 8. Database와 stateful change

Delivery platform은 application migration 의미를 대신 결정하지 않습니다. 그러나 안전한 실행 경계를 요구할 수 있습니다.

- expand/contract compatibility
- old/new version 동시 실행 가능성
- migration identity와 lock
- 재실행 가능성
- backup 또는 restore point
- deploy와 migration 순서
- rollback이 불가능한 지점
- post-migration verification

Migration을 image 시작 script마다 실행하지 않게 하고, 별도 operation과 evidence로 추적합니다.

## 9. Rollback과 roll-forward

Rollback은 이전 artifact를 다시 배포하는 것만으로 끝나지 않을 수 있습니다.

검토:

- configuration schema가 이전 version과 호환됩니까?
- database state가 되돌릴 수 있습니까?
- message와 event contract가 변했습니까?
- credential rotation을 되돌릴 수 있습니까?
- feature flag가 old version의 안전한 경로를 유지합니까?
- 외부 system에 이미 effect가 발생했습니까?

되돌릴 수 없는 상태 변화 뒤에는 새 수정 artifact를 빠르게 전달하는 roll-forward가 더 안전할 수 있습니다. 어떤 조건에서 어느 방법을 선택하는지 runbook에 기록합니다.

## 10. Pipeline failure와 재시도

Pipeline 재실행이 source를 다시 build하는지, 기존 artifact를 다시 검증·배포하는지 구분합니다.

```text
build retry        같은 입력으로 새 build execution, 결과 digest 비교
verification retry 같은 artifact에 검사 재실행
promotion retry    같은 evidence와 artifact를 다음 환경에서 재평가
deployment retry   같은 desired release의 reconciliation 재시도
```

Timeout 뒤 이미 publish 또는 deploy됐을 수 있으므로 operation ID와 external state를 확인합니다.

## 11. Delivery platform의 SLI

사용자 여정과 내부 상태를 함께 측정합니다.

- commit에서 verified artifact까지 시간
- artifact에서 환경 Ready까지 시간
- workflow infrastructure failure rate
- policy rejection 중 actionable message 비율
- queue wait와 runner saturation
- promotion·rollback 성공률
- 오래된 workflow version 사용량
- 동일 artifact가 환경마다 다른지 여부
- provenance와 release record 누락률

애플리케이션 test 실패를 delivery platform 장애율에 그대로 포함하지 않습니다. Platform failure와 user code failure를 분리해야 개선 owner를 찾을 수 있습니다.

## 12. 실습

[`07-delivery-gitops`](../exercises/07-delivery-gitops/)에서 다음을 설계합니다.

- source부터 artifact까지 identity chain
- build와 deployment identity 분리
- evidence bundle
- 환경별 promotion gate
- progressive delivery 중단 조건
- database change 경계
- rollback 또는 roll-forward 판단
- retry 시 재사용하는 상태

## 13. 검토 질문

- 환경마다 source를 다시 build하지 않습니까?
- Artifact와 configuration·secret·deployment result가 분리돼 있습니까?
- Untrusted change가 trusted credential을 사용할 수 없습니까?
- Release record가 source·artifact·policy·environment를 연결합니까?
- Promotion gate가 실제 사용자 risk를 측정합니까?
- Database와 외부 effect 때문에 rollback이 불가능한 지점을 알고 있습니까?
- Pipeline 재시도가 중복 artifact·deployment를 만들지 않습니까?

다음 장에서는 release desired state를 Git에 선언하고 controller가 수렴시키는 GitOps 운영 경계를 다룹니다.
