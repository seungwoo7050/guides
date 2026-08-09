# 실제 Cloud provider profile

필수 과정은 provider-neutral 문서와 로컬 모델로 완료할 수 있습니다. 이 디렉터리는 실제 공급자 하나를 선택해 generic contract를 매핑할 때 사용하는 선택 경로입니다.

## profile 원칙

- provider 제품을 core 문서의 정본으로 만들지 않습니다.
- official documentation과 확인 날짜를 기록합니다.
- 실제 비용과 credential을 요구하는 명령을 자동 실행하지 않습니다.
- account/project, region, identity, budget, prefix, TTL와 destroy evidence를 먼저 준비합니다.
- 한 provider profile만 수행해도 충분합니다.

## 작성 파일

[`provider-experiment-template.md`](provider-experiment-template.md)를 복사해 작성합니다.

```text
experiment charter
service crosswalk
responsibility matrix
resource inventory
failure test
cost estimate
cleanup evidence
observed differences
```

## 지원 범위

이 브랜치에는 provider SDK나 IaC module을 고정하지 않습니다. 실제 provider integration은 별도 프로젝트에서 구현하고, 여기에는 핵심 계약과 관측 결과만 되돌립니다.
