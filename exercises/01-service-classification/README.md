# 01. 서비스 분류와 책임

## 목적

마케팅 이름이 아니라 소비자가 얻는 capability, 제어하는 상태와 공급자에게 이동한 작업을 근거로 IaaS·PaaS·SaaS와 FaaS를 분류합니다.

## 입력

[`inputs/scenarios.md`](inputs/scenarios.md)에 다섯 사례가 있습니다.

## 결과물

`assessment.md`에 다음을 작성합니다.

- 사례별 capability
- service model
- execution model
- deployment model
- 공급자·소비자 책임
- 실패와 evidence
- 분류가 애매한 지점

## 진행

```sh
scripts/new_workspace.sh exercises/01-service-classification
scripts/check_workspace.sh exercises/01-service-classification
```

## 사람 검토 질문

1. FaaS를 IaaS·PaaS·SaaS와 같은 열에만 적지 않았습니까?
2. 제품 이름 없이도 분류 근거를 설명할 수 있습니까?
3. managed라는 표현을 실제 운영 작업으로 분해했습니까?
4. 소비자에게 남는 data·identity·cost·exit 책임을 적었습니까?
5. evidence가 보장하지 않는 것을 기록했습니까?
