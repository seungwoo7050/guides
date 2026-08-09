# 표준과 외부 자료 지도

이 브랜치는 provider-neutral 원리를 정본으로 사용하고, 특정 공급자 제품의 현재 limit·API·가격·동작은 공식 문서에서 다시 확인합니다.

확인 기준일: **2026-08-09**

이 문서는 아래 기관·공급자의 공식 페이지 제목과 URL을 attribution으로 기록하고, 원문을 복제하지 않고 학습 목표에 필요한 판단 기준만 요약합니다. URL 도달 여부는 확인 기준일에 다시 검사했지만, 실제 서비스의 region·계정·API별 의미는 선택 profile에서 같은 날짜와 관측 결과로 재검증해야 합니다.

## 1. 클라우드 정의와 서비스 모델

### NIST SP 800-145 — The NIST Definition of Cloud Computing

- https://csrc.nist.gov/pubs/sp/800/145/final
- 다섯 essential characteristic, 세 service model(IaaS·PaaS·SaaS), 네 deployment model을 정의합니다.
- 이 브랜치에서 FaaS를 별도 실행 모델로 구분하는 기준점입니다.

### NIST SP 500-322 — Evaluation of Cloud Computing Services Based on NIST SP 800-145

- https://www.nist.gov/publications/evaluation-cloud-computing-services-based-nist-sp-800-145
- 주어진 capability가 cloud service인지, 어떤 service model에 가까운지 판정하는 보조 기준입니다.

## 2. Cloud access control

### NIST SP 800-210 — General Access Control Guidance for Cloud Systems

- https://csrc.nist.gov/pubs/sp/800/210/final
- IaaS·PaaS·SaaS에서 access control 대상과 책임이 어떻게 달라지는지 검토할 때 사용합니다.

## 3. Serverless와 event source

공급자별 event semantics는 서비스와 source에 따라 달라집니다. 아래 문서를 예시로 사용하고, 실제 선택한 source의 최신 문서를 확인합니다.

### AWS Lambda event source mapping API

- https://docs.aws.amazon.com/lambda/latest/api/API_CreateEventSourceMapping.html
- batch, retry, record age, failure destination 등 event source mapping의 configuration을 확인합니다.

### AWS Lambda와 Amazon MQ

- https://docs.aws.amazon.com/lambda/latest/dg/with-mq.html
- at-least-once processing과 duplicate 가능성, source별 concurrency 제한의 실제 예를 확인합니다.

### AWS Lambda Kafka retry configuration

- https://docs.aws.amazon.com/lambda/latest/dg/kafka-retry-configurations.html
- maximum retry, failure destination와 partial batch 관련 현재 동작을 확인합니다.

이 자료는 AWS 사용을 필수로 만들지 않습니다. provider-specific semantics가 generic FaaS 용어보다 구체적이라는 사실을 보여 주는 예시입니다.

## 4. Multitenancy

### Azure Architecture Center — Tenancy models

- https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/tenancy-models
- isolation을 fully shared와 fully isolated 사이의 연속선으로 검토할 때 사용합니다.

### Azure Architecture Center — Multitenant solution architecture

- https://learn.microsoft.com/en-us/azure/architecture/guide/saas-multitenant-solution-architecture/
- SaaS business model과 technical tenancy가 동일하지 않을 수 있음을 검토합니다.

provider 문서의 특정 Azure service 설계를 그대로 정답으로 사용하지 않고 tenant isolation trade-off를 비교하는 자료로 사용합니다.

## 5. FinOps

### FinOps Framework

- https://www.finops.org/framework/
- engineering·finance·product가 cloud value와 cost를 함께 운영하는 capability와 lifecycle을 확인합니다.

가격과 할인은 자주 바뀌므로 이 브랜치에는 고정 숫자를 정본으로 넣지 않습니다. 실제 실험의 estimate는 provider calculator와 billing export의 확인 날짜를 기록합니다.

## 6. 공급자 architecture framework

실제 profile을 만들 때 다음 provider 공식 framework를 참고할 수 있습니다.

- AWS Well-Architected Framework: https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html
- Microsoft Azure Well-Architected Framework: https://learn.microsoft.com/azure/well-architected/
- Google Cloud Architecture Framework: https://cloud.google.com/architecture/framework

이 framework는 질문 목록과 provider 기능을 찾는 출발점입니다. 브랜치의 책임·상태·실패·evidence 모델을 대신하지 않습니다.

## 7. 현재성 규칙

다음 정보는 문서 작성 시점 뒤 바뀔 가능성이 높습니다.

- 서비스 이름
- region availability
- runtime version
- timeout·payload·concurrency limit
- retry default
- SLA
- 가격
- free tier
- support 종료
- API field

provider-specific profile에는 다음 metadata를 남깁니다.

```text
provider
service
document_url
checked_at
region
account_type
cli_or_sdk_version
observed_behavior
```

본문 원리와 provider-specific current fact가 충돌하면 실제 계약·공식 문서·실험 evidence를 우선하고 브랜치 문서를 갱신합니다.

외부 링크 검사는 필수 오프라인 `verify.sh`에 포함하지 않습니다. 링크가 살아 있다는 사실은 내용의 정확성·적용 가능성·가격을 증명하지 않으므로, 문서 변경자는 공식 도메인·제목·확인 날짜와 선택한 region·account 조건을 함께 검토합니다.

## 8. 읽기 순서

```text
NIST 정의
→ service classification
→ 선택 workload의 provider architecture framework
→ 실제 service API·limit·delivery documentation
→ 실험 evidence
→ responsibility·failure·cost·exit 문서 갱신
```
