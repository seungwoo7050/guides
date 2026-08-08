# Runbook: Container restart loop

## 대상 증상과 사용자 영향

- Container가 반복해서 `restarting` 또는 `exited` 상태가 됩니다.
- Restart policy가 최초 오류를 빠르게 덮을 수 있습니다.
- App, gateway, DB 중 어느 service인지에 따라 영향이 다릅니다.

## 사전 안전 조건

- 반복 재시작 횟수를 늘리거나 모든 service를 동시에 재시작하지 않습니다.
- 실패 container의 inspect, exit code와 최초 로그를 먼저 보존합니다.
- Volume과 DB data를 삭제하지 않습니다.

## 1. 상태와 종료 이유 확인

```sh
cd /srv/example
docker compose ps -a
docker inspect '<container>' --format \
  '{{json .State}}'
docker compose logs --tail 200 --no-color '<service>'
```

확인:

- Exit code와 signal
- `OOMKilled`
- 시작·종료 시각
- Healthcheck 실패인지 process 종료인지
- Error message의 최초 발생 지점
- Restart count

## 2. 실행 산출물과 설정 확인

```sh
docker inspect '<container>' --format '{{.Image}}'
docker inspect '<container>' --format '{{json .Config.Labels}}'
docker compose config >/dev/null
```

Release manifest의 expected digest와 실제 image를 비교합니다. Environment 전체를 출력하지 않고 필요한 공개 설정 이름과 secret mount 존재만 확인합니다.

## 3. 원인 분기

### OOMKilled

- Host memory, container limit와 runtime heap을 비교합니다.
- 최근 traffic·worker·batch 변경을 확인합니다.
- Memory leak인지 정상 peak인지 구분합니다.
- Limit 제거보다 입력 제한·worker 축소·호환 rollback을 우선 검토합니다.

### 설정·Secret 누락

- Release가 요구하는 config schema와 secret version을 확인합니다.
- 파일 owner·mode와 mount 경로를 검사합니다.
- Secret 값은 출력하지 않습니다.

### DB schema 비호환

- 현재 schema version과 image 허용 범위를 비교합니다.
- Migration을 반복 실행하지 않습니다.
- 이전 release rollback 가능성을 manifest로 확인합니다.

### Port·permission 오류

- Process 실행 사용자, bind port, writable path와 read-only filesystem을 확인합니다.
- Root로 임시 실행해 문제를 숨기지 않습니다.

### Healthcheck만 실패

Process와 실제 protocol은 정상인데 healthcheck가 틀릴 수 있습니다. 검사 명령, 도구 존재, path, timeout과 start period를 확인합니다.

## 4. Restart storm 제한

반복 시작이 dependency와 로그를 압박하면 영향 service만 일시 중지할 수 있습니다.

```sh
docker compose stop '<service>'
```

중지 전에 현재 사용자 영향과 대체 경로를 확인합니다. DB recovery 중인 container를 무작정 중지하지 않습니다.

## 5. 가역 완화

- 호환 이전 exact digest로 rollback
- 잘못된 공개 설정·secret pointer 복구
- 검증된 resource limit·worker 수로 복귀
- 잘못된 healthcheck만 수정

Candidate를 별도 project name 또는 격리 환경에서 실행해 startup을 확인한 뒤 production을 바꿉니다.

## 6. 복구 확인

- Restart count가 더 이상 증가하지 않습니다.
- Process와 protocol health가 모두 정상입니다.
- 외부 핵심 경로가 성공합니다.
- Memory·CPU·disk가 안정됩니다.
- 실제 image digest와 release 기록이 일치합니다.
- 최초 오류 원인을 재현하는 검사가 추가됩니다.

## 7. 증거와 후속 작업

```text
Exit code·OOMKilled·restart count
최초 오류 로그
Image digest·config schema·secret version
완화와 rollback 대상
Resource 사용 전후
새 startup·failure test
```
