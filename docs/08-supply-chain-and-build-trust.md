# 소프트웨어 공급망과 빌드 신뢰

production이 실행하는 code는 개발자가 작성한 source만으로 결정되지 않습니다.

```text
source
+ dependency
+ build tool
+ CI identity
+ build environment
+ artifact registry
+ deployment policy
+ runtime configuration
```

이 경로 중 하나가 손상되면 application vulnerability 없이도 trusted code로 배포될 수 있습니다.

CI/CD·registry·배포 플랫폼의 구축과 여러 팀을 위한 paved road는 `platform-engineering`, 한 서비스의 배포·rollback·runtime 운영은 `web-infra`가 소유합니다. 이 장은 그 도구 사용법을 다시 설명하지 않고, source에서 runtime까지의 trust edge가 공격 경로가 되는 조건과 artifact별 증거·차단·복구를 다룹니다.

## 1. 공급망의 보안 속성

- source 변경이 승인된 review와 identity를 거칩니다.
- build input이 식별되고 재현 가능한 범위가 기록됩니다.
- build process가 의도하지 않은 source·dependency·secret을 사용하지 않습니다.
- artifact가 어느 source와 build identity에서 만들어졌는지 증명할 수 있습니다.
- registry에서 받은 artifact가 승인된 digest와 같습니다.
- deployment는 verification을 통과한 artifact만 승격합니다.
- 발견된 compromise 뒤 영향 artifact·release를 추적하고 digest 기준 사용 거부 정책을 전파할 수 있습니다.

## 2. trust graph

다음 관계를 그립니다.

```text
개발자 identity
  → source repository
  → review·merge policy
  → CI workflow
  → runner·build environment
  → dependency source
  → artifact
  → registry
  → release manifest
  → production runtime
```

각 edge에서 묻습니다.

- 누가 쓰고 승인할 수 있는가?
- 어떤 identity와 credential을 사용하는가?
- 입력과 출력이 immutable하게 식별되는가?
- 로그와 provenance가 남는가?
- 이전 상태로 rollback할 수 있는가?

## 3. source integrity

- protected branch와 review policy
- required check의 정체성과 bypass 권한
- maintainer·bot·app token scope
- workflow file 변경 승인
- tag·release 생성 권한
- history rewrite와 force push policy
- generated code와 vendored source의 원본

서명된 commit 하나만으로 review·CI·dependency·artifact까지 보장되지 않습니다. 어느 edge를 보장하는지 구분합니다.

## 4. dependency trust

lockfile이 있어도 다음 위험이 남습니다.

- dependency source 또는 maintainer compromise
- package name 혼동
- transitive dependency
- install script와 build plugin
- registry replacement·proxy behavior
- yanked·deleted artifact
- 알려진 취약점과 지원 종료
- license·origin·binary blob

dependency마다 최소한 다음을 추적합니다.

```text
name·version·digest
source registry·repository
transitive path
runtime/build/test scope
known vulnerability
maintainer·support status
update owner
```

새 dependency를 추가할 때 필요한 capability와 대체 가능성을 검토합니다.

## 5. build environment

위험:

- mutable base image와 toolchain
- host의 ambient credential
- shared runner의 residual state
- network에서 임의 input 다운로드
- untrusted PR code와 privileged secret의 동시 실행
- build cache poisoning
- output에 포함된 secret·debug artifact

통제:

- ephemeral·isolated runner
- 최소 credential과 environment separation
- input pinning과 digest verification
- network policy
- repeatable·reproducible 여부와 비교 조건을 명시한 build evidence
- build output inventory
- untrusted contribution과 release build 분리

같은 builder에서 다시 성공하는 repeatable build와 독립 환경이 같은 output을 만드는 reproducible build를 구분합니다. 재현 결과가 같아도 source·dependency·toolchain 자체의 악성 동작이나 모든 runtime input의 안전을 증명하지 않습니다. 결과가 다르면 non-determinism, 누락된 input 또는 손상 가능성을 조사할 신호가 되지만, 차이만으로 어느 build가 신뢰할 수 있는지는 정해지지 않습니다.

## 6. artifact identity

tag나 filename은 변경될 수 있습니다. release는 immutable digest와 metadata로 식별합니다.

```text
artifact digest
source revision
build workflow identity
build timestamp
builder identity
platform
SBOM
provenance
signature 또는 attestation
verification result
```

서명은 “안전한 artifact”를 의미하지 않습니다. 성공한 검증은 **특정 key가 특정 bytes에 유효한 signature를 만들었다는 사실**을 보여 줄 뿐, signer가 사람인지 승인된 builder인지, source가 review됐는지, artifact에 취약점이 없는지, 현재 release로 허용되는지까지 증명하지 않습니다. key identity·보호·algorithm·certificate chain·서명 시점·revocation 상태와 무엇을 서명했는지를 정책이 별도로 연결해야 합니다.

## 7. SBOM과 provenance

### SBOM

artifact에 포함된 component를 조사·영향 분석할 수 있게 합니다. 존재만으로 취약점이 없음을 보장하지 않습니다.

생성 방식에 따라 누락·오식별이 있을 수 있고, 동적 다운로드·runtime configuration·외부 service까지 포함하지 않을 수 있습니다. component가 목록에 있다는 사실만으로 취약 code의 reachability나 exploitability를 알 수 없습니다. SBOM 자체의 artifact digest·creator·format·생성 시점과 completeness 한계를 기록합니다.

### provenance

artifact가 어떤 source·builder·parameters·materials에서 생성됐는지 설명합니다. provenance를 생성한 build identity와 verifier policy가 신뢰 경계입니다.

attestation이 문법적으로 유효해도 builder가 관찰하지 못한 input, 거짓 statement, 손상된 builder와 실행 뒤 변경은 남을 수 있습니다. provenance는 선언한 build 경로와 materials를 추적하는 근거이지 source의 안전성, build output의 무결점 또는 production runtime digest를 혼자 보장하지 않습니다.

SLSA는 source·build provenance와 공급망 threat를 구조화하는 데 사용할 수 있습니다. 이 가이드는 특정 level 인증을 목표로 하지 않고, 현재 release path에서 어떤 보장을 실제 증명하는지 기록합니다.

## 8. registry와 promotion

- write·delete·retag 권한 분리
- immutable artifact와 retention
- malware·vulnerability scan의 위치와 한계
- environment promotion 시 새 build 금지 여부
- release manifest와 runtime digest 비교
- denylisted digest와 폐기된 signing identity의 promotion·deployment 차단
- rollback artifact 보존
- registry compromise 때 alternate recovery source

production이 tag를 pull하면 review한 artifact와 실제 실행 artifact가 달라질 수 있습니다.

artifact revoke는 immutable bytes를 세상에서 회수하는 동작이 아닙니다. registry 삭제만으로 cache·mirror·이미 실행 중인 workload가 사라지지 않습니다. 영향 digest와 signer를 denylist에 넣고 registry, promotion verifier, deployment controller와 runtime inventory에 전파한 뒤, 실행 중인 instance 교체와 rollback 후보 검증까지 확인해야 합니다. 그래서 “revoked” evidence에는 enforcement 지점, 정책 version, 전파 시간, 남은 copy·instance와 예외 owner가 포함됩니다.

## 9. CI credential

CI는 여러 control plane을 연결하므로 높은 가치의 identity입니다.

- repository read/write
- registry push
- cloud deploy
- secret store
- signing·attestation
- issue·release publishing

장기 static secret보다 workload identity와 short-lived token을 선호합니다. job·repository·branch·environment·audience scope를 제한합니다. PR code가 release secret에 접근하지 못하도록 trust level을 분리합니다.

## 10. supply-chain incident

의존성 또는 build path 손상이 의심되면 다음을 조사합니다.

1. 영향 source·version·artifact digest
2. build·publish identity와 time
3. 어떤 release와 environment가 artifact를 실행했는지
4. artifact가 가진 runtime capability
5. credential·data 접근 가능성
6. log·audit·backup의 신뢰성
7. revoke·rollback·rebuild 범위
8. clean source·builder·credential로 trust 재설정

단순히 package를 새 version으로 올리는 것으로 끝나지 않을 수 있습니다.

## 11. SSDF와 secure-by-design

NIST SSDF는 secure development practice를 조직의 SDLC에 통합하는 공통 구조를 제공합니다. CISA의 Secure by Design 원칙은 고객이 별도 hardening을 수행해야만 안전한 제품보다, 제조자가 기본 설정과 제품 설계에서 위험을 줄이는 책임을 강조합니다.

이 가이드에서는 다음 질문으로 적용합니다.

- 취약점 class를 개별 patch가 아니라 개발·build rule에서 제거할 수 있는가?
- 안전한 기본값이 opt-in입니까, opt-out입니까?
- 고객이 product security를 검증할 evidence를 받을 수 있는가?
- vulnerability disclosure와 patch delivery 경로가 존재하는가?

## 12. 이 장의 산출물

현재 프로젝트의 release 하나를 골라 다음을 작성합니다.

1. source-to-runtime trust graph
2. 각 edge의 writer·approver·identity
3. mutable input과 ambient credential
4. dependency inventory와 위험 5개
5. artifact identity와 required evidence
6. SBOM·provenance·signature가 보장하는 것과 한계
7. CI credential scope
8. compromise 시 영향 release를 찾는 query 또는 절차
9. clean rebuild와 credential reset 계획
10. artifact deny 정책의 enforcement·전파·실행 중 instance 처리
11. 각 evidence가 보장하는 trust edge와 보장하지 않는 안전성

## 13. 완료 질문

- source가 안전해도 artifact가 손상될 수 있는 경로는 무엇입니까?
- lockfile과 signature가 각각 보장하지 못하는 것은 무엇입니까?
- PR build와 release build의 trust level을 분리해야 하는 이유는 무엇입니까?
- SBOM과 provenance는 어떻게 다릅니까?
- supply-chain incident 뒤 단순 update보다 trust reset이 필요한 경우는 언제입니까?
