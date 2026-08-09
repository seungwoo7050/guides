# Backstage catalog 실습

Software catalog와 portal이 platform API·control plane과 다른 책임을 갖는지 관찰합니다. Backstage를 예로 들지만 핵심은 특정 portal 제품이 아닙니다.

## 목표

- component, system, resource와 owner 관계를 metadata로 표현합니다.
- catalog ingestion 실패와 runtime failure를 구분합니다.
- template가 repository 시작점을 만들 뿐 지속적인 runtime state를 소유하지 않음을 확인합니다.
- portal이 없어도 platform API를 사용할 수 있는 경계를 설계합니다.

## 필수 local 판정

Backstage가 없어도 다음 검사는 owner reference 형식, profile version과 HTTPS status API 계약의 정상·대표 실패를 비교합니다.

```sh
python3 examples/optional-labs/check_profiles.py
```

`catalog/owned-component`는 통과하고 `catalog/missing-owner`는 거부돼야 합니다. 이 결과는 Backstage schema, catalog processor, database와 plugin 동작을 검증하지 않습니다.

## 기존 local Backstage에 연결하는 선택 profile

이 단계는 이미 폐기 가능한 local Backstage 개발 환경을 가진 경우에만 실행합니다. 새 application 생성과 package download는 이 가이드의 자동 검증 범위가 아닙니다. 먼저 실제 version과 기존 entity 위치를 기록합니다.

```sh
node --version
npm --version
test -f package.json
test -f app-config.yaml
```

두 fixture를 local catalog location에 복사하거나 `app-config.local.yaml`의 `catalog.locations`에서 file target으로 등록합니다.

```text
examples/catalog/component.yaml
examples/optional-labs/catalog/component-invalid.yaml
```

개발 server를 기존 프로젝트의 documented command로 시작한 뒤 catalog API/UI에서 다음을 기록합니다.

- 정상 component의 owner, system, profile version과 status link
- `missing-team` reference의 unresolved 관계 또는 ingestion error
- portal을 중지했을 때도 별도 platform status API가 유지되는지 여부
- template 실행 뒤 생성된 repository와 runtime state의 writer가 다른지 여부

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

추가한 local location, fixture entity와 생성된 test repository/resource를 제거합니다. Catalog backend의 local data를 재사용한다면 `checkout-invalid-owner`와 test entity가 남지 않았는지 API/UI에서 확인합니다. 제거 실패 시 catalog owner가 cleanup 책임자입니다.
