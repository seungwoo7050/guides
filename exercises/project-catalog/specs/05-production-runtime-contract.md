# Stage 05 — 운영 런타임 계약

## 사용자 결과

배포 도구는 production server를 시작하고 health와 release를 확인할 수 있다. test-only reset endpoint는 명시적인 test mode와 token 없이는 닫혀 있다. server secret은 HTML, health와 초기 JavaScript에 노출되지 않는다.

## 구현할 것

### Health

- `GET /api/health`를 구현한다.
- body는 정확히 `status`, `release`만 가진다.
- `APP_RELEASE`가 없으면 `local`을 사용한다.
- `Cache-Control: no-store`를 설정한다.
- 환경 변수 전체나 secret을 반환하지 않는다.

### 제공된 Test boundary

제공된 reset Route Handler는 다음 두 조건을 모두 요구한다. 학습자는 이 route를 구현하는 대신 Stage 검증으로 경계가 유지되는지 확인한다.

- `NODE_ENV=test` 또는 `PLAYWRIGHT=1`
- `x-catalog-test-token`과 `CATALOG_TEST_RESET_TOKEN` 일치

### 제공된 Production smoke 검증

제공된 smoke harness는 학습자가 구현한 health route와 production 산출물을 다음 계약으로 검증한다. smoke script 자체는 learner 수정 대상이 아니다.

- production server를 사용 가능한 고유 port에서 시작한다.
- 제한 시간 안에 health 준비를 기다린다.
- health exact contract와 release를 검사한다.
- root HTML과 project API를 검사한다.
- server-only secret canary가 health, HTML, 초기 JavaScript body에 없는지 검사한다.
- 성공·실패 모두 child process와 process group을 정리한다.

`TODO(stage-05)` 표시를 모두 제거한다.

## 완료 조건

```sh
pnpm exercise:verify:05
```

전체 unit test, production build, browser E2E와 standalone smoke가 통과해야 한다.
