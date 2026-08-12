# 운영 런타임 계약

프런트엔드 변경은 `next build`가 성공했다고 끝나지 않는다. 배포할 산출물이 실제 server에서 시작되고, release를 식별하며, 비밀값을 노출하지 않고, 외부 smoke test가 핵심 경로를 확인할 수 있어야 한다.

이 장은 호스트·container·DNS·TLS를 구축하지 않는다. 애플리케이션이 `guide-web-infrastructure`에 제공할 **운영 산출물과 검증 계약**을 정의한다.

## 목표

이 장을 마치면 다음을 수행할 수 있어야 한다.

- production build와 production start를 독립적으로 실행한다.
- readiness 판단에 사용할 최소 health response를 설계한다.
- release identifier를 browser와 server 오류에 연결한다.
- public·server-only 환경 변수를 분리하고 canary로 누출을 검사한다.
- 제공된 standalone smoke harness의 소유권·실패·정리 계약을 분석하고 고유 port에서 실행한다.
- application contract와 infrastructure responsibility를 구분한다.

연결 실습은 [Stage 05](../exercises/project-catalog/specs/05-production-runtime-contract.md)다.

## 배포 산출물을 명시합니다

배포 방식이 무엇이든 다음을 기록한다.

- build 명령
- start 명령
- 필요한 Node.js 범위
- runtime 환경 변수
- public 환경 변수
- listen host와 port
- health URL
- graceful shutdown 기대 시간
- release identifier 주입 방법
- smoke test 명령

실습의 계약:

```text
build   pnpm build
start   pnpm start --hostname 127.0.0.1 --port <port>
health  GET /api/health
smoke   pnpm smoke
```

Docker image 생성과 registry push는 인프라 가이드가 담당하더라도, 어떤 command와 환경으로 application을 실행해야 하는지는 application 저장소가 소유해야 한다.

## Health는 작고 안정된 계약으로 만듭니다

health endpoint는 다음 두 값만 반환한다.

```json
{
  "status": "ok",
  "release": "local"
}
```

응답에는 `Cache-Control: no-store`를 둔다. health 검사에 다음을 노출하지 않는다.

- 환경 변수 전체
- filesystem path
- dependency version 전체
- stack trace
- database credential
- token과 cookie
- 내부 hostname

단순 process liveness와 dependency readiness가 다른 서비스라면 endpoint를 분리할 수 있다. 이 실습은 외부 dependency가 없으므로 process가 route를 처리할 수 있는지와 release만 확인한다.

health field를 무제한으로 늘리면 monitoring client와 배포 script가 application 내부구조에 결합한다. 공개 contract는 최소로 유지한다.

## Test-only endpoint를 실제 운영에서 닫습니다

E2E 데이터 초기화를 위한 endpoint는 편리하지만 운영에서 열리면 치명적인 제어 경로가 된다.

실습의 reset endpoint는 두 조건을 모두 요구한다.

1. `NODE_ENV=test` 또는 명시적인 `PLAYWRIGHT=1`
2. 요청의 `x-catalog-test-token`이 `CATALOG_TEST_RESET_TOKEN`과 일치

하나라도 맞지 않으면 endpoint 존재를 드러내지 않고 404를 반환한다.

이 방식도 일반적인 운영 admin API를 대체하지 않는다. test-only route가 product build에 존재해야 한다면 조건과 검사를 매우 좁게 유지하고, 가능한 프로젝트에서는 별도 test fixture 경로를 선택한다.

## Release를 관찰 가능하게 만듭니다

문제가 발생했을 때 “현재 어떤 코드가 실행 중인가?”를 답할 수 있어야 한다.

```text
source commit
→ build/release identifier
→ application health와 server log
→ browser error report
```

실습은 `APP_RELEASE`를 health response에 노출한다. 값이 없으면 `local`을 사용한다. 실제 배포에서는 commit SHA, image digest 또는 release manifest의 안정적인 식별자를 주입한다.

사용자에게 보이는 오류에 전체 commit과 내부 정보를 직접 표시할 필요는 없다. support가 찾을 수 있는 안전한 short identifier를 제공하고 server log에는 전체 release 정보를 남길 수 있다.

## 환경 변수를 공개 범위로 나눕니다

### Server-only

- API credential
- signing key
- private service URL
- test reset token
- internal release metadata 중 비공개 값

### Browser-public

- 공개 analytics site id
- 공개 origin
- 사용자에게 보여도 되는 feature flag

공개 prefix가 붙은 값은 browser bundle과 response에서 읽힐 수 있다고 가정한다. 이름에 `SECRET`이 들어간다고 보호되지 않는다.

실습 smoke test는 임의의 secret canary를 server 환경에 넣고 다음에서 문자열이 나타나지 않는지 확인한다.

- health body
- root HTML
- 초기 route가 불러온 JavaScript body

이 검사는 모든 형태의 secret leak을 증명하지는 않지만 server-only 값을 client module에서 import하는 회귀를 잡는 안전망이다.

## 제공된 Standalone smoke 검증을 분석·실행합니다

연결 실습은 repository-owned smoke harness를 제공한다. 학습자는 script 자체를 구현하지 않고, health route를 구현한 뒤 harness의 아래 수명과 실패 정리 계약을 읽고 실행 증거를 확인한다. smoke 검증은 기존 개발 서버에 의존하지 않는다.

```text
사용 가능한 임시 port 선택
→ production server process 시작
→ health가 준비될 때까지 제한 시간 polling
→ health contract와 release 확인
→ root HTML의 핵심 heading 확인
→ project API 최소 응답 확인
→ 초기 JavaScript에 secret canary가 없는지 확인
→ process group 종료와 잔존 process 검사
```

모든 network call에는 timeout을 둔다. server가 준비되지 않거나 `pnpm start` 자체가 실패하면 즉시 진단 가능한 output과 함께 종료한다.

검사 중 오류가 발생해도 child process를 정리한다. main failure와 cleanup failure가 동시에 있으면 하나를 숨기지 않는다.

## 운영 실패를 분류합니다

| 증상 | 먼저 확인할 경계 |
| --- | --- |
| process 시작 실패 | Node.js, command, environment, port |
| health 404 | route output, base path, deployment version |
| health는 성공하지만 화면 실패 | route-specific data, client bundle, runtime config |
| HTML은 성공하지만 interaction 실패 | script asset, CSP, hydration, browser error |
| release가 예상과 다름 | deployment target, stale instance, cache |
| smoke 종료 뒤 process 잔존 | signal forwarding, process group, start wrapper |

health 성공을 전체 사용자 기능 성공으로 해석하지 않는다. readiness와 핵심 browser flow는 서로 다른 검사다.

## Application과 Infrastructure 책임을 분리합니다

### 이 가이드가 소유

- reproducible install·build·start command
- route와 runtime 환경 변수 계약
- health response
- release identifier
- browser E2E와 standalone smoke
- application log와 error에 필요한 correlation field
- secret이 client output에 들어가지 않는 검사

### `guide-web-infrastructure`가 소유

- host와 container runtime 준비
- registry, image promotion과 deployment authorization
- DNS, certificate와 reverse proxy
- central log·metric·trace backend
- alert threshold와 on-call routing
- backup, restore, host rebuild와 rollback 실행
- network policy와 secret distribution system

경계를 나누더라도 양쪽은 계약으로 연결된다. 인프라는 application의 health와 start command를 임의로 추측하지 않고, application은 특정 deployment platform 내부 API에 불필요하게 결합하지 않는다.

## Stage 05 완료 기준

```sh
pnpm exercise:verify:05
```

다음을 확인한다.

- 고정 의존성에서 typecheck, unit test와 production build가 통과한다.
- production server가 고유 port에서 시작된다.
- `/api/health`는 정확히 `status`, `release`만 반환하고 `no-store`다.
- reset endpoint는 test mode와 token 없이는 404다.
- root HTML과 project API가 응답한다.
- server-only secret canary가 health, HTML와 초기 JavaScript body에 없다.
- smoke 성공·실패 모두 child process를 정리한다.
- production browser E2E의 핵심 사용자 흐름이 통과한다.

## 완료 후

이 가이드를 마쳤다면 React/Next.js의 새 API를 많이 아는 것보다 다음 능력을 갖춘 상태여야 한다.

```text
실행 경계를 복원한다.
상태와 데이터의 소유자를 정한다.
시간 차이에서 결과를 수렴시킨다.
실제 사용자 행동으로 검증한다.
배포 가능한 산출물의 계약을 증명한다.
```

새 framework API를 도입할 때도 같은 질문으로 평가한다. 어느 문제를 해결하고, 어떤 실행 경계를 추가하며, 실패할 때 어떤 검사로 발견할 수 있는가?
