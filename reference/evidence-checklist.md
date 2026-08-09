# Evidence checklist

## Product

- [ ] 사용자와 반복 문제를 실제 관찰 또는 인터뷰로 확인했습니다.
- [ ] 현재 journey의 시간·handoff·실패를 기록했습니다.
- [ ] outcome과 guardrail을 함께 정의했습니다.

## API와 control plane

- [ ] Request/resource/operation identity가 구분됩니다.
- [ ] Spec·status·condition·generation 예제가 있습니다.
- [ ] Idempotency와 partial failure를 검증했습니다.
- [ ] External resource와 state mapping을 추적할 수 있습니다.
- [ ] Delete/finalizer/orphan 경로가 있습니다.

## Delivery

- [ ] Source revision과 immutable artifact digest가 연결됩니다.
- [ ] Build와 deployment identity가 분리됩니다.
- [ ] Test·SBOM·provenance·policy evidence가 release record에 연결됩니다.
- [ ] 같은 artifact가 환경 사이에서 승격됩니다.
- [ ] Rollback 또는 roll-forward 조건이 있습니다.

## Runtime와 tenancy

- [ ] Workload request/readiness/disruption contract가 있습니다.
- [ ] Identity, network, storage와 telemetry isolation을 확인했습니다.
- [ ] Quota와 platform capacity를 구분합니다.
- [ ] Noisy tenant와 control-plane fairness를 시험했습니다.

## 운영

- [ ] User journey SLI/SLO가 있습니다.
- [ ] Alert와 runbook을 연결했습니다.
- [ ] Capacity failure와 backlog drain을 연습했습니다.
- [ ] 비용 owner와 showback 근거가 있습니다.
- [ ] Backup/restore 또는 state recovery를 검증했습니다.

## Lifecycle

- [ ] Profile/component version inventory가 있습니다.
- [ ] Preflight·canary·wave·abort·rollback을 검증했습니다.
- [ ] Exception과 break-glass가 종료됐습니다.
- [ ] Service/tenant retirement 뒤 orphan·credential·cost를 확인했습니다.

## 주장 제한

- [ ] 실제로 실행하지 않은 검사는 명시했습니다.
- [ ] Local simulation을 production 보장으로 표현하지 않았습니다.
- [ ] Tool output이 증명하는 것과 증명하지 못하는 것을 기록했습니다.
