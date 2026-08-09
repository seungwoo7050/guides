# Supply chain과 platform security

플랫폼은 source, build runner, artifact registry, deployment controller, cluster와 workload identity를 연결합니다. 이 경로 중 하나가 손상되면 표준화된 자동화가 공격을 더 빠르게 확산시킬 수 있습니다.

이 장은 플랫폼이 제공해야 하는 **신뢰 근거와 강제 지점**을 다룹니다. 취약점 연구, 침투 테스트와 사고 대응 전체 과정은 `cybersecurity`의 소유 범위이며, 여기서는 개발·배포 platform의 경계를 설계합니다.

## 1. 보호할 자산

- source repository와 review rule
- build definition과 reusable workflow
- runner와 build credential
- dependency와 toolchain
- artifact와 registry
- provenance·SBOM·signature
- GitOps/IaC desired state
- deployment/controller credential
- cluster/API/admission
- secret broker와 identity issuer
- policy repository
- audit·telemetry
- platform API state

각 자산의 owner, writer, reader, backup/restore와 compromise 영향 범위를 적습니다.

## 2. Threat path

대표 경로:

```text
악성 source 또는 dependency
→ trusted build 실행
→ credential 탈취 또는 artifact 변조
→ registry publish
→ promotion policy 우회
→ controller가 여러 environment에 배포
→ workload identity로 lateral access
```

또 다른 경로:

```text
platform API/controller 결함
→ 다른 tenant resource 변경
→ secret 또는 policy reference 교체
→ GitOps가 desired state로 정상화
→ 공격 상태가 지속
```

도구별 취약점 목록보다 신뢰가 어디에서 다음 단계로 전달되는지 추적합니다.

## 3. Source trust

- protected branch와 review
- CODEOWNERS 또는 정책 owner
- signed commit/tag를 요구할지
- 외부 contribution과 내부 trusted change 분리
- workflow file 변경의 강화된 review
- repository admin와 bypass audit
- dependency bot identity
- archived/deleted repository lifecycle

Review는 자동 policy와 runtime guardrail을 대체하지 않지만 중요한 사람 판단 지점입니다.

## 4. Build isolation

Untrusted code가 build runner에서 실행됩니다.

Guardrail:

- ephemeral runner
- clean workspace와 cache boundary
- root/privileged 실행 최소화
- network egress 제한
- cloud metadata 차단
- job별 short-lived identity
- pull request와 trusted release job 분리
- secret 최소 주입
- output size·time·process 제한
- 종료 뒤 workspace·credential 폐기

공유 cache는 dependency와 artifact poisoning 경로가 될 수 있습니다. Key, writer와 validation을 정합니다.

## 5. Dependency와 toolchain

- lockfile과 immutable digest
- package registry allowlist/proxy
- namespace confusion 방지
- checksum/signature
- builder/base image pin
- compiler/plugin version
- end-of-life 추적
- license와 known vulnerability
- emergency patch와 rebuild

SBOM은 구성요소 목록을 제공하지만 artifact가 실제 그 source에서 만들어졌다는 사실을 단독으로 증명하지 않습니다.

## 6. Provenance와 artifact identity

Release artifact에는 다음 질문에 답할 근거가 필요합니다.

- 어느 source revision에서 만들어졌는가?
- 어떤 build definition과 builder가 사용됐는가?
- 어떤 input dependency가 있었는가?
- build output digest는 무엇인가?
- 누가 publish했는가?
- statement가 artifact와 일치하는가?

Provenance를 생성하는 pipeline과 검증하는 deployment 경계를 분리합니다. 같은 credential이 artifact와 evidence를 임의로 모두 바꿀 수 있으면 신뢰 가치가 약합니다.

공식 개념 연결은 [`reference/source-index.md#supply-chain`](../reference/source-index.md#supply-chain)에서 확인합니다.

## 7. Signing과 verification

Signature는 key holder가 해당 statement에 서명했다는 사실을 제공합니다. 다음이 추가로 필요합니다.

- signer identity와 발급 근거
- key 또는 certificate 수명
- trusted root
- revocation
- signature가 묶는 정확한 digest
- verification policy
- transparency/audit

이미지를 tag로 검증한 뒤 digest가 다른 artifact를 deploy하지 않습니다.

## 8. Promotion policy

Production admission 예:

```text
artifact digest가 immutable registry에 존재
provenance의 source repository가 허용됨
trusted builder identity
필수 test evidence
SBOM과 vulnerability policy
profile-compatible runtime
승인과 exception 유효
```

모든 취약점 발견을 무조건 차단하면 patch delivery가 멈출 수 있습니다. Severity, exploitability, exposure, fix availability와 exception expiry를 포함한 risk policy가 필요합니다.

## 9. Platform control plane 보안

Control plane은 높은 권한을 가집니다.

- API authentication/authorization
- tenant object visibility
- controller field ownership
- dependency input validation
- queue/resource limits
- command/template injection 방지
- external URL allowlist
- secret redaction
- admission/webhook fail-open/fail-closed 정책
- backup·restore와 state integrity
- admin/break-glass audit

사용자 입력을 IaC variable, shell command, template와 Kubernetes metadata에 연결할 때 각 경계에서 validation과 escaping을 적용합니다.

## 10. Policy와 controller compromise

중앙 policy repository 또는 controller가 손상되면 여러 workload에 영향을 줍니다.

방어:

- 최소 권한과 scope
- 변경 review와 signed release
- canary rollout
- immutable deployment artifact
- independent audit
- config version과 rollback
- controller별 namespace/cluster 분리
- kill switch와 reconciliation pause
- compromise drill

Centralization의 편익과 blast radius를 동시에 관리합니다.

## 11. Cluster와 workload baseline

Platform profile이 제공할 수 있는 기본:

- restricted workload privilege
- read-only 또는 최소 filesystem
- non-root
- capability 제한
- host namespace/path 금지
- resource request/limit
- default-deny network
- workload identity
- secret reference
- image provenance policy
- telemetry와 audit

모든 workload에 같은 hardening을 강제하지 않고 risk profile과 exception을 명확히 합니다.

## 12. Platform state와 backup

IaC state, catalog, API resource와 Git desired state를 보호합니다.

- encryption과 access
- writer 분리
- version history
- backup과 restore drill
- integrity check
- delete protection
- sensitive output redaction
- incident 시 evidence 보존

Git과 state backend가 모두 있다고 복구 가능한 것은 아닙니다. External resource identity와 credential issuer, registry, policy version을 함께 복원해야 할 수 있습니다.

## 13. Security evidence와 continuous verification

- source/workflow change audit
- runner identity와 job
- artifact digest·provenance·SBOM
- promotion policy decision
- admission result
- workload identity 발급
- secret access
- exception/break-glass
- runtime drift와 anomaly
- controller admin action

Evidence를 생성하는 system과 조회·보존하는 system의 trust를 검토합니다.

## 14. Incident containment

공급망 또는 platform compromise 의심 시 가능한 조치:

```text
영향 artifact·builder·credential 식별
→ 새 promotion 일시 중지
→ 증거 보존
→ compromised identity 폐기
→ affected artifact quarantine
→ desired/live deployment inventory
→ safe artifact로 교체
→ controller/policy 복구
→ credential rotation
→ 재검증과 단계적 재개
```

무조건 cluster 전체를 삭제하는 것이 첫 행동은 아닙니다. 영향과 복구 가능성을 증거로 좁힙니다.

## 15. 실습

[`08-identity-policy`](../exercises/08-identity-policy/)와 [`12-capstone-plan`](../exercises/12-capstone-plan/)에서 다음을 작성합니다.

- source-to-runtime trust chain
- untrusted/trusted build 경계
- artifact evidence와 verification
- controller·policy blast radius
- workload baseline
- exception과 emergency action
- compromise containment와 복구 evidence

## 16. 검토 질문

- Source에서 runtime까지 각 단계의 writer와 verifier가 보입니까?
- Untrusted code가 장기 credential과 production network에 접근하지 못합니까?
- Artifact tag가 아니라 digest와 provenance를 검증합니까?
- SBOM·signature·vulnerability scan 각각의 보장 범위를 구분합니까?
- Platform API와 controller가 tenant 간 권한을 넘지 않습니까?
- 중앙 policy/controller 변경이 canary와 rollback을 거칩니까?
- Compromise 시 promotion을 중지하고 영향 artifact를 찾을 수 있습니까?
- State·registry·identity·policy를 포함한 복구 근거가 있습니까?

다음 장에서는 지금까지의 계약을 하나의 내부 개발자 플랫폼 설계와 실패 drill로 통합합니다.
