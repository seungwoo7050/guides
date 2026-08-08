# CI/CD, 배포와 rollback

배포는 `docker compose up -d` 한 줄이 아닙니다. 후보 release를 선택하고, 호환성을 검사하고, 실행 상태를 바꾸고, 사용자 경로를 확인한 뒤에야 현재 release로 확정하는 **상태 전이**입니다.

이 장의 목표는 다음 규칙을 구현하는 것입니다.

```text
검증되지 않은 산출물은 production 후보가 아님
동시에 둘 이상의 배포가 상태를 바꾸지 않음
현재 release는 smoke test 전에는 확정되지 않음
실패하면 원인을 보존한 채 이전 호환 release로 돌아감
DB 변경이 이전 application의 실행 가능성을 파괴하지 않음
누가 무엇을 언제 배포했는지 기록됨
```

대응 실습은 [`exercises/12-deployment-rollback`](../exercises/12-deployment-rollback/)입니다.

## 1. CI와 CD의 책임 분리

### CI

소스 변경이 배포 가능한 산출물이 될 수 있는지 검증합니다.

```text
format·lint
→ unit·integration test
→ image build
→ image policy·vulnerability scan
→ SBOM·provenance
→ registry push
→ digest와 manifest 생성
```

### Delivery

검증된 산출물을 특정 환경의 후보로 만듭니다.

```text
release 승인
→ 환경별 설정·secret 존재 확인
→ staging 또는 canary 검증
→ production 배포 대기
```

### Deployment

실제 production 실행 상태를 바꿉니다.

```text
배포 잠금
→ preflight
→ backup 또는 복구 지점 확인
→ migration
→ image pull
→ 새 container 시작
→ readiness
→ 외부 smoke test
→ release 확정
```

이 세 경계를 한 workflow에 구현해도 논리적 책임은 분리합니다.

## 2. 배포 입력은 release manifest 하나

배포 스크립트가 branch나 변경 가능한 tag를 직접 해석하지 않게 합니다.

나쁜 입력:

```text
main
latest
현재 디렉터리의 Dockerfile
```

좋은 입력:

```text
release manifest URI 또는 검증된 파일
```

manifest에서 exact digest, source revision, schema 호환 범위와 smoke path를 읽습니다.

배포 시점에 image tag를 digest로 다시 해석하면 tag가 검증 이후 바뀌었을 수 있습니다.

## 3. 배포 동시성

두 배포가 동시에 실행되면 다음 경쟁이 생길 수 있습니다.

- 서로 다른 image pull과 container 재생성
- migration 중복 실행
- `current-release.json` 덮어쓰기
- 한 배포의 smoke test가 다른 배포를 검사
- rollback 대상이 잘못 기록됨

환경별 배포 잠금을 둡니다.

```text
production 환경에는 한 번에 하나의 상태 변경 배포만 허용
```

CI 제품의 concurrency 기능, host file lock 또는 중앙 lock 중 하나를 사용할 수 있습니다. lock의 만료·소유자·강제 해제 절차를 문서화합니다.

## 4. 배포 전 검사

상태를 바꾸기 전에 실패할 수 있는 검사를 최대한 수행합니다.

### 산출물

- manifest 형식과 서명·provenance가 유효한가?
- 모든 image digest를 registry에서 pull할 수 있는가?
- architecture가 host와 맞는가?
- 필요한 이전 release가 registry에 남아 있는가?

### 환경

- disk와 inode 여유가 있는가?
- Docker daemon이 정상인가?
- 설정 schema와 secret version이 맞는가?
- 공개 포트가 예상 프로세스에 의해 사용 중인가?
- backup 또는 복구 지점이 최근에 성공했는가?

### 호환성

- 현재 DB schema가 후보 release의 허용 범위 안인가?
- migration 뒤 현재 release가 계속 동작할 수 있는가?
- rollback release가 migration 뒤에도 동작하는가?

preflight가 실패하면 current release를 건드리지 않습니다.

## 5. Migration과 expand-contract

가장 위험한 rollback 실패는 application image는 되돌렸지만 schema가 이전 code와 호환되지 않는 경우입니다.

안전한 일반 흐름:

```text
1. Expand
   새 column·table·index를 이전 code와 호환되게 추가
2. Migrate
   새 code가 구·신 구조를 함께 다룸
3. Backfill
   기존 데이터를 제한된 batch로 채움
4. Switch
   읽기·쓰기 정본을 새 구조로 전환
5. Contract
   이전 release가 더 이상 필요 없음을 확인한 뒤 옛 구조 제거
```

한 release에서 column을 즉시 rename하거나 삭제하면 이전 application rollback을 막을 수 있습니다.

모든 migration이 자동 rollback 가능한 것은 아닙니다. 데이터 파괴 작업은 별도 승인, backup과 복원 검증을 요구합니다.

## 6. Compose 배포의 상태 전이

단일 호스트 기준선에서 한 가지 구현 흐름은 다음과 같습니다.

```sh
# 1. manifest에서 exact image digest를 환경 파일에 기록
# 2. pull
# 3. config 렌더링 검사
docker compose config >/dev/null
# 4. 필요한 migration 실행
# 5. container 재생성
docker compose up -d --remove-orphans
# 6. 내부 readiness 대기
# 7. 호스트 밖에서 smoke test
```

`docker compose up`의 종료 코드가 0이라고 모든 서비스가 준비된 것은 아닙니다. readiness와 외부 smoke test를 별도로 기다립니다.

Compose가 새 container를 시작하는 방식은 서비스 구성과 버전에 따라 짧은 중단을 만들 수 있습니다. 무중단이 필수라면 단일 replica Compose 기준선보다 더 강한 배포 구조가 필요합니다.

## 7. Smoke test

smoke test는 가장 중요한 사용자 경로를 작고 안전하게 검사합니다.

최소 구성:

- 공개 DNS 사용
- 인증서 검증 활성화
- 실제 gateway 통과
- 읽기 경로
- 필요한 경우 되돌릴 수 있는 쓰기 경로
- 응답 schema 또는 핵심 본문 검사
- 명확한 timeout

```sh
curl --fail --show-error --silent \
  --max-time 10 \
  https://service.example/api/notes >/dev/null
```

고정 `/healthz`만 검사하면 application과 database 장애를 놓칠 수 있습니다.

쓰기 smoke는 production 데이터 오염을 막기 위해 전용 계정·namespace·idempotency key와 cleanup을 사용합니다.

## 8. Release 확정 지점

다음이 모두 성공하기 전에는 새 release를 `current`로 기록하지 않습니다.

- container가 기대 digest로 실행 중
- readiness 통과
- 외부 smoke 통과
- error rate와 핵심 metric이 허용 범위
- migration 상태가 기대 version

확정 시 원자적으로 다음을 기록합니다.

```yaml
current: 2026-08-07.1
previous: 2026-08-01.2
activated_at: 2026-08-07T11:00:00Z
manifest_digest: sha256:...
operator: ci://run/1234
```

현재 파일을 먼저 덮어쓰고 smoke가 실패하면 rollback 대상과 실제 상태가 어긋납니다.

## 9. 자동 rollback의 경계

자동 rollback이 적합한 경우:

- 새 container가 시작되지 않음
- readiness가 제한 시간 안에 통과하지 않음
- deterministic smoke test 실패
- migration이 상태 변경 전에 실패함
- 이전 release와 schema 호환이 확인됨

자동 rollback을 멈추고 사람이 판단해야 하는 경우:

- destructive migration 일부가 적용됨
- 데이터 정합성 위반 가능성
- 현재와 이전 release 모두 실패
- 외부 의존 서비스 장애
- 보안 사고 또는 credential 유출
- 원인이 불명확한 반복 재배포

rollback을 “무조건 이전 image 실행”으로 정의하지 않습니다. application, schema, 설정과 secret의 호환성을 함께 봅니다.

## 10. Rollback 절차

```text
새 트래픽 또는 추가 변경 중지
→ 증거 보존
→ 현재 실행 digest·schema 확인
→ 이전 manifest 호환성 재검사
→ 이전 exact digest 배포
→ readiness
→ 외부 smoke
→ 현재 release 기록 복구
→ incident 또는 deployment failure 기록
```

실패한 candidate container와 로그를 즉시 모두 지우지 않습니다. 원인 분석에 필요한 정보를 먼저 보존합니다. 다만 사용자 영향이 지속되면 완화가 분석보다 우선입니다.

## 11. Roll-forward

데이터 변경 때문에 rollback이 위험하면 수정 release를 앞으로 배포하는 편이 안전할 수 있습니다.

선택 기준:

- 이전 code가 현재 schema를 읽을 수 있는가?
- 데이터 변환을 되돌릴 수 있는가?
- 문제 원인이 작고 수정이 검증됐는가?
- 현재 사용자 영향이 얼마나 큰가?
- 수정 release 준비 시간과 rollback 시간이 어떻게 다른가?

runbook에 자동 답을 넣기보다 판단에 필요한 증거를 정의합니다.

## 12. CI/CD 권한

workflow는 필요한 최소 권한만 가집니다.

분리 예:

```text
검사 job       source read
build job      package/image push
attest job     provenance write
deploy job     production environment access
```

production 배포는 환경 보호 규칙과 승인을 사용할 수 있습니다. 같은 workflow를 실행한 사람이 자신의 배포를 승인할 수 있는지 조직 정책에 맞게 결정합니다.

클라우드나 registry가 지원하면 장기 access key 대신 OIDC로 짧은 수명 credential을 발급받습니다. OIDC trust 조건은 repository 이름만이 아니라 branch, environment와 immutable identifier를 가능한 범위에서 제한합니다.

외부 CI action이나 plugin은 가능한 경우 검토된 버전과 변경 불가능한 revision으로 고정하고 업데이트 절차를 둡니다.

## 13. Self-hosted runner 주의

production host를 CI runner로 직접 사용하는 방식은 단순하지만 신뢰 경계를 합칩니다.

- pull request code가 host에서 실행될 수 있는가?
- runner workspace에 production secret이 남는가?
- 이전 job의 container·file이 다음 job에 영향을 주는가?
- runner compromise가 Docker daemon과 production 전체를 제어하는가?

사용해야 한다면 public·untrusted workflow와 분리하고, ephemeral runner 또는 별도 배포 agent를 검토합니다.

## 14. 배포 후 관찰 창

smoke 통과 직후 모든 문제가 드러나지는 않습니다.

배포 후 일정 시간 다음을 비교합니다.

- HTTP error rate
- latency percentile
- container restart
- memory와 CPU
- DB connection·lock
- queue 또는 background job lag
- application-specific failure

문제가 생겼을 때 release marker를 로그와 metric에 연결할 수 있어야 합니다.

## 15. 배포 기록

각 시도마다 성공·실패와 무관하게 기록합니다.

```text
release id와 manifest digest
source revision
image digest 목록
시작·종료 시각
승인자와 실행 주체
preflight 결과
migration 결과
readiness·smoke 결과
rollback 여부와 대상
관찰한 오류 링크
```

CI 실행 기록만 유일한 정본이면 보존 기간이 끝난 뒤 증거가 사라질 수 있습니다. 필요한 운영 보존 정책을 정합니다.

## 16. 실습

[`exercises/12-deployment-rollback`](../exercises/12-deployment-rollback/)은 실제 Docker daemon을 바꾸지 않는 배포 상태 기계를 구현합니다.

fixture:

- `v1`: 현재 정상 release
- `v2`: 정상 candidate
- `bad`: smoke가 실패하는 candidate

학습자는 다음 계약을 구현합니다.

1. preflight 실패 시 현재 상태 불변
2. 동시에 하나의 배포만 허용
3. candidate를 staging 상태에 둠
4. readiness와 smoke 성공 뒤에만 current 확정
5. 실패 시 previous release 복원
6. 모든 전이를 append-only event log에 기록
7. schema 비호환이면 자동 rollback 거부

이 상태 기계는 실제 배포 스크립트에서 가장 중요한 순서와 실패 후 상태를 작은 파일 시스템 모델로 검증합니다.

## 17. 공식 확인 자료

- GitHub Actions deployments and environments: <https://docs.github.com/actions/reference/workflows-and-actions/deployments-and-environments>
- GitHub Actions deployment controls: <https://docs.github.com/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments>
- GitHub Actions OIDC: <https://docs.github.com/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect>
- Docker Compose production guidance: <https://docs.docker.com/compose/how-tos/production/>

다음 장에서는 배포에 필요한 secret과 공개 설정을 분리하고, 서비스 중단 없이 교체하는 수명 주기를 만듭니다.
