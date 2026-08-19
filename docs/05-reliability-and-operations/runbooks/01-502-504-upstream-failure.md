# 런북: 게이트웨이 502·504

## 대상 증상과 사용자 영향

- 공개 요청이 `502 Bad Gateway` 또는 `504 Gateway Timeout`을 반환합니다.
- 정적 파일이나 `/healthz`는 성공하지만 동적 요청만 실패할 수 있습니다.
- 502는 게이트웨이가 유효한 업스트림 응답을 얻지 못한 경우가 많고 504는 정해진 시간 안에 응답을 받지 못한 경우가 많습니다. 상태 코드만으로 원인을 확정하지 않습니다.

## 필요한 권한과 도구

- 외부 위치에서 `curl`, `openssl`
- 호스트의 Compose 상태·로그 읽기 권한
- 게이트웨이 설정 읽기 권한
- 릴리스 매니페스트와 최근 배포 기록 읽기 권한

## 사전 안전 조건

- 같은 시간에 새 배포와 설정 변경을 중지합니다.
- `docker compose down`, 볼륨 삭제, 무조건 재시작을 먼저 실행하지 않습니다.
- 최초 오류 로그, 실행 이미지 다이제스트, 현재 설정을 보존합니다.

## 1. 외부 경계 확인

```sh
curl --fail-with-body --show-error --silent \
  --max-time 10 \
  https://service.example/healthz

curl --show-error --silent --include \
  --max-time 10 \
  https://service.example/api/notes
```

기록할 것:

- DNS와 TLS가 성공했는가?
- 모든 경로가 실패하는가, 동적 경로만 실패하는가?
- 502인가 504인가?
- 시작 시각과 영향 비율은 얼마인가?

TLS 자체가 실패하면 인증서 런북으로 이동합니다.

## 2. 최근 변경 확인

```text
최근 release
Gateway 설정 변경
Secret 회전
DB maintenance
Host update·reboot
```

최근 변경은 가설일 뿐 원인으로 단정하지 않습니다.

## 3. Compose와 최초 오류 확인

```sh
cd /srv/example
docker compose ps -a
docker compose logs --since 15m --no-color gateway app db
```

관찰:

- `app`이 exited·restarting인가?
- 게이트웨이에 `connection refused`, `host not found`, `upstream timed out` 중 무엇이 있는가?
- 애플리케이션의 최초 오류가 DB·비밀값·스키마를 가리키는가?
- OOM 또는 호스트 디스크 오류가 있는가?

로그를 무제한 출력하지 않고 시간 범위와 서비스를 제한합니다.

## 4. 게이트웨이 설정과 업스트림 이름 확인

```sh
docker compose exec gateway nginx -t
docker compose exec gateway nginx -T
```

민감한 헤더나 자격 증명이 출력될 수 있는 환경이면 민감 정보를 제거한 설정 사본을 사용합니다.

확인:

- 업스트림 서비스 이름과 포트가 현재 Compose와 같은가?
- HTTP 업스트림과 FastCGI 업스트림을 혼동하지 않았는가?
- IPv4·IPv6 또는 DNS 결과가 예상과 같은가?
- 타임아웃이 실제 처리 시간보다 지나치게 짧은가?

## 5. 업스트림 경계 확인

PHP-FPM 예:

```sh
docker compose exec app sh -c '
  REQUEST_METHOD=GET \
  SCRIPT_NAME=/ping \
  SCRIPT_FILENAME=/ping \
  cgi-fcgi -bind -connect 127.0.0.1:9000
'
```

서비스 이름 해석은 게이트웨이 내부에서 확인합니다.

```sh
docker compose exec gateway getent hosts app
```

도구가 이미지에 없다면 임의로 패키지를 설치해 실행 상태를 바꾸지 말고 동일 네트워크의 진단용 임시 컨테이너 또는 호스트의 `docker network inspect`를 사용합니다.

## 6. 분기

### `host not found`

- Compose 서비스 이름과 네트워크 연결을 확인합니다.
- 새 컨테이너 주소를 고정 IP로 가정한 설정이 있는지 봅니다.
- 잘못된 별칭을 수정한 뒤 게이트웨이 설정 검사와 리로드를 수행합니다.

### `connection refused`

- 애플리케이션 프로세스가 실제 포트에서 수신하는지 확인합니다.
- 애플리케이션이 시작 직후 종료하는지 최초 로그를 봅니다.
- 게이트웨이 포트와 런타임 포트를 비교합니다.

### `upstream timed out`

- 애플리케이션 내부 처리 시간과 DB·외부 API 타임아웃을 확인합니다.
- 무작정 게이트웨이 타임아웃만 늘리지 않습니다.
- 요청 중단, 워커 고갈, DB 연결 고갈, lock wait를 조사합니다.

### 애플리케이션은 정상인데 일부 요청만 실패

- 라우트별 오류율과 request ID를 확인합니다.
- 특정 payload, 사용자, DB 쿼리 또는 외부 의존성으로 범위를 좁힙니다.

## 7. 가역 완화

- 호환성이 확인된 이전 정확한 릴리스로 롤백합니다.
- 문제가 있는 쓰기 경로만 유지보수·읽기 전용으로 제한합니다.
- 과부하가 원인이면 admission control이나 제한된 워커 수로 입력을 줄입니다.
- 일시적인 의존성 장애라면 제한 시간과 횟수가 제한된 재시도를 적용합니다.

설정 하나를 수정한 뒤 다음을 반복합니다.

```text
nginx 설정 검사
→ graceful reload 또는 해당 service 재생성
→ 내부 readiness
→ 외부 동적 경로
```

## 8. 고위험 조치

다음은 사고 지휘자 승인과 복구 지점 없이 수행하지 않습니다.

- DB 스키마 변경
- 볼륨 제거
- 모든 컨테이너와 네트워크 일괄 삭제
- 방화벽 전체 교체
- 타임아웃을 무제한 확대
- 원인 분석 전 로그·실패 컨테이너 삭제

## 9. 복구 확인

- 외부 동적 읽기와 안전한 쓰기가 성공합니다.
- 502·504 비율과 지연 시간이 정상 범위로 돌아옵니다.
- 애플리케이션 재시작과 DB 연결이 안정적입니다.
- 실행 이미지 다이제스트와 릴리스 기록이 일치합니다.
- 같은 request ID를 게이트웨이와 애플리케이션 로그에서 추적할 수 있습니다.

## 10. 보존할 증거와 후속 작업

```text
장애 시작·종료 시각
영향 경로와 비율
Gateway·app 최초 오류
현재·이전 image digest
변경한 설정과 승인자
완화·rollback 결과
재발 검증 방법
```
