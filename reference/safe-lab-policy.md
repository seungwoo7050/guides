# 선택 실습 안전 계약

선택 profile은 실제 플랫폼 원리를 관찰하기 위한 폐기 가능한 실험입니다. 운영 환경의 축소판이나 production 보장의 근거로 사용하지 않습니다.

## 시작 전 승인 조건

- 자신이 소유한 local host, 전용 sandbox 또는 명시적으로 허가된 환경만 사용합니다.
- 기본 예산은 `0`이며, cloud resource를 만드는 변형은 이 가이드의 범위 밖입니다.
- production kubeconfig, repository, identity, secret, customer data와 telemetry를 사용하지 않습니다.
- cluster·namespace·container·state·repository 이름에는 `platform-guide` 또는 별도 실행 ID를 사용하고 기존 이름과 충돌하면 중단합니다.
- tool, image, provider와 module의 실제 version 또는 digest를 실행 기록에 남깁니다.
- 시작 전 process, container, cluster, workspace와 credential inventory를 기록합니다.

## 실행 중 제한

- CPU·memory·disk·실행 시간을 local 환경에서 감당할 수 있게 제한합니다.
- 실패 주입은 실습 namespace와 workspace 안에서만 수행합니다.
- credential이 필요한 확장은 최소 scope와 짧은 TTL을 사용하고, 장기 fallback credential을 만들지 않습니다.
- 예상하지 않은 외부 endpoint, 비용, 다른 namespace/repository 또는 기존 resource를 발견하면 즉시 중단합니다.
- cleanup 명령을 실행할 수 없는 상태가 되면 새 실험을 시작하지 않고 원인과 owner를 기록합니다.

## 종료와 복구

성공·실패·중단 여부와 관계없이 다음을 확인합니다.

1. 실습 namespace·cluster·container·network·volume·workspace를 식별합니다.
2. 정상 cleanup 명령을 먼저 사용하고 강제 삭제는 finalizer·외부 effect를 조사한 뒤 선택합니다.
3. 시작 전과 같은 종류의 inventory를 다시 수집해 잔여 resource, process, credential, state와 비용을 비교합니다.
4. 남은 항목마다 owner, 영향, 다음 cleanup 명령과 확인 시점을 기록합니다.
5. 로그에 secret·token·kubeconfig·state의 민감 값이 없는지 확인합니다.

실제 제품 profile을 실행하지 못했으면 결정적 대체 검사의 결과와 함께 무엇을 관찰하지 못했는지 기록합니다. `SKIP`은 성공이 아니며 핵심 simulator 경로를 대신 생략할 근거도 아닙니다.
