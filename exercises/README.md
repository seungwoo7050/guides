# 클라우드 컴퓨팅 실습

실습은 cloud provider 콘솔을 따라 하는 과정이 아닙니다. 같은 workload를 책임·상태·실패·evidence·비용으로 분석하고, 공급자 제품이 달라져도 남는 판단을 연습합니다.

## 진행 순서

| 순서 | 실습 | 핵심 판단 |
|---:|---|---|
| 1 | [서비스 분류](01-service-classification/README.md) | service·execution·deployment model을 분리합니다. |
| 2 | [IaaS failure domain](02-iaas-failure-domains/README.md) | resource 수명과 공동 실패를 찾습니다. |
| 3 | [Managed service 계약](03-managed-service-contract/README.md) | 공급자에게 이동한 작업과 남은 책임을 적습니다. |
| 4 | [FaaS event lifecycle](04-faas-event-lifecycle/README.md) | duplicate·timeout·retry·DLQ를 상태로 만듭니다. |
| 5 | [SaaS tenant isolation](05-saas-tenant-isolation/README.md) | 모든 access path에 tenant context를 적용합니다. |
| 6 | [비용과 exit](06-cost-and-exit/README.md) | cost driver·budget·cleanup·migration을 연결합니다. |
| 7 | [로컬 cloud model](07-local-cloud-model/README.md) | cross-tenant·duplicate·quota·cleanup failure를 코드로 수정합니다. |

## 문서 실습

원본 `template/`은 직접 수정하지 않습니다.

```sh
scripts/new_workspace.sh exercises/01-service-classification
scripts/check_workspace.sh exercises/01-service-classification
```

복사 직후 검사는 `TODO`와 최소 근거 누락 때문에 실패합니다. 문서를 완성한 뒤 통과시키고 `reference/`와 비교합니다.

검사 통과는 문서가 훌륭하다는 뜻이 아닙니다. 필수 구조와 미완성 표시가 없음을 확인할 뿐입니다. 각 README의 사람 검토 질문을 사용합니다.

## 코드 실습

07의 `skeleton`은 의도적으로 다음 결함을 가집니다.

- cross-tenant document read 허용
- quota 초과 뒤 partial state
- duplicate event의 output·usage 중복
- stateful resource public exposure
- tenant deletion 뒤 resource와 event 잔존

공개 tests가 외부 행동을 검사합니다. `reference`를 먼저 복사하지 않고 실패를 한 개씩 재현하고 수정합니다.

## 실제 공급자 실험

필수 실습은 credential이나 비용을 요구하지 않습니다. 실제 계정을 사용할 때는 [`reference/cloud-experiment-safety.md`](../reference/cloud-experiment-safety.md)의 계약을 먼저 작성합니다.
