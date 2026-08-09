# Delivery Contract

## 공통 식별자

promotion record는 service `svc-payments`, resource `env-payments-staging`, operation `op-payments-staging-v3`, tenant `tenant-checkout`, artifact `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, profile `stateless-http/v3`를 담는다.

## Build Once와 Promotion

build identity는 source revision으로 artifact를 한 번 만들고 digest, provenance, test/scan attestation에 서명한다. deploy identity는 artifact를 만들거나 registry content를 바꿀 권한이 없고 승인된 digest를 환경에 승격할 권한만 가진다. stage마다 재빌드하거나 mutable tag를 배포하면 동일 artifact 승격 주장을 거부한다.

promotion admission은 provenance, required tests, vulnerability exception expiry, profile compatibility와 change policy를 평가한다. 승인 결과와 policy version은 operation evidence가 된다. secret은 pipeline variable로 장기 저장하지 않고 audience가 좁은 workload/federated identity로 short-lived token을 발급한다.

## GitOps Reconciliation

desired deployment record는 artifact digest, profile version, config revision과 environment ID를 선언한다. Git merge는 request일 뿐 성공 evidence가 아니다. reconciler가 observed digest/generation을 비교하고 runtime observation과 smoke result를 status로 되돌려야 한다.

일반 live edit는 desired state로 자동 수렴한다. emergency edit는 security/platform approver, reason, expiry, affected resource와 before/after evidence가 있는 break-glass record에만 허용된다. record가 만료되면 Git desired state로 수렴시키고 결과를 `op-payments-staging-v3`에 연결한다.

## Rollback과 Partial Effect

rollback 조건은 artifact regression이고 config/data/schema가 이전 artifact와 호환될 때다. 호환되지 않거나 irreversible migration이 시작됐으면 검증된 다음 digest로 roll-forward한다. 두 경우 모두 traffic step, data commitment, policy change와 verification을 명시한다.

cluster A만 새 artifact를 적용하고 cluster B가 실패하면 operation을 `Ready`로 만들지 않는다. applied target, old/new digest, traffic fraction과 cleanup/forward owner를 partial effect로 남긴다. retry는 같은 promotion identity를 사용하며 새 build로 실패 기록을 덮지 않는다. `svc-payments` retirement 때 Git desired objects, deploy credentials, promotion reservation과 runtime artifact inventory를 함께 닫는다.
