# Backstage catalog 실습

Software catalog와 portal이 platform API·control plane과 다른 책임을 갖는지 관찰합니다. Backstage를 예로 들지만 핵심은 특정 portal 제품이 아닙니다.

## 목표

- component, system, resource와 owner 관계를 metadata로 표현합니다.
- catalog ingestion 실패와 runtime failure를 구분합니다.
- template가 repository 시작점을 만들 뿐 지속적인 runtime state를 소유하지 않음을 확인합니다.
- portal이 없어도 platform API를 사용할 수 있는 경계를 설계합니다.

## 기본 흐름

1. local Backstage 개발 환경을 준비합니다.
2. [`examples/catalog/component.yaml`](../../examples/catalog/component.yaml)을 등록합니다.
3. owner, repository, system, dependency와 lifecycle이 표시되는지 확인합니다.
4. 잘못된 owner reference 또는 schema를 넣어 ingestion 오류를 관찰합니다.
5. component의 runtime status를 static annotation으로 쓰지 말고 external status API 또는 link로 연결하는 방식을 설계합니다.
6. 작은 software template를 만들어 repository metadata와 platform API request 예시를 생성합니다.
7. template 실행 뒤 생성된 service의 upgrade가 template 재실행이 아닌 profile migration으로 이뤄지는지 설명합니다.

## 검토 질문

- Catalog metadata의 writer는 누구입니까?
- Runtime Ready와 current release의 정본은 어디입니까?
- Owner가 존재하지 않거나 팀이 바뀌면 어떻게 탐지합니까?
- Portal plugin이 실패해도 service deployment와 reconciliation은 계속됩니까?
- Template에 secret 또는 production credential이 들어가지 않습니까?
- 생성된 repository가 platform profile version을 기록합니까?

## Cleanup

개발 환경과 생성된 test repository/resource를 제거합니다. Catalog backend의 local data를 재사용한다면 test entity가 남지 않았는지 확인합니다.
