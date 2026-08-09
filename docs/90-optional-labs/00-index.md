# 선택 도구 실습 색인

핵심 과정은 특정 cloud 계정이나 Kubernetes cluster 없이 완료할 수 있습니다. 이 디렉터리의 실습은 문서에서 설계한 계약을 실제 도구의 상태와 명령으로 관찰하기 위한 **선택 profile**입니다.

## 공통 원칙

- 개인 sandbox 또는 폐기 가능한 로컬 환경만 사용합니다.
- 설치 전 공식 문서에서 현재 지원 version과 host 요구사항을 확인합니다.
- image·module·chart·action은 가능한 한 version 또는 digest를 고정합니다.
- 실제 조직 credential과 production data를 사용하지 않습니다.
- 비용이 발생하는 cloud resource는 만들지 않거나 budget·TTL·cleanup을 먼저 설정합니다.
- 성공 명령만 기록하지 않고 실패 주입과 cleanup evidence를 남깁니다.
- 도구 동작을 platform contract와 동일시하지 않습니다.

## 실습 목록

| 실습 | 관찰할 경계 | 필수 도구 |
|---|---|---|
| [Local Kubernetes](01-kind-kubernetes-lab.md) | API object, controller, scheduling, service와 cleanup | Docker, `kubectl`, `kind` 또는 동등 도구 |
| [OpenTofu state](02-opentofu-state-lab.md) | configuration·state·resource identity·drift | OpenTofu 또는 Terraform |
| [Backstage catalog](03-backstage-catalog-lab.md) | catalog metadata, owner, template와 platform API 분리 | Node.js, Backstage 개발 환경 |
| [GitOps controller](04-gitops-controller-lab.md) | desired revision, reconciliation, drift와 suspend | local cluster, Flux 또는 Argo CD |
| [Admission policy](05-policy-admission-lab.md) | audit/warn/deny, exception과 실제 enforcement | local cluster, CEL/Kyverno/Gatekeeper 중 하나 |

모든 실습을 수행할 필요는 없습니다. 목표 프로젝트에서 사용하는 구현 profile 한두 개를 선택합니다.

## 공통 evidence

각 실습 뒤 다음을 남깁니다.

```text
환경과 tool version
입력 source와 digest/version
실행 명령
초기 관측 상태
주입한 실패
실패 중 상태와 event
복구 또는 cleanup
최종 잔여 resource 검사
문서 계약과 실제 도구 동작의 차이
```

`verify.sh`는 선택 도구를 설치하거나 실제 실습 성공을 판정하지 않습니다. 학습자가 남긴 evidence와 환경 안전성은 별도로 검토합니다.
