# HTTPS 게이트웨이와 PHP-FPM

Nginx가 개발용 TLS 인증서를 생성하고, 정적 파일은 직접 응답하며 PHP 요청은 FastCGI로 애플리케이션에 전달합니다.

## 통과해야 할 요청

- Nginx와 PHP-FPM의 프로토콜 경계를 구분합니다.
- `fastcgi_pass`의 네트워크 주소와 `SCRIPT_FILENAME`의 파일 경로를 구분합니다.
- FPM `/ping`을 FastCGI 클라이언트로 검사합니다.
- 게이트웨이만 호스트에 공개합니다.

## 실행

저장소 루트에서 작업공간을 만든 뒤 그 사본의 PHP-FPM·Nginx 설정을 수정합니다.

```sh
python3 scripts/new-workspace.py exercises/04-gateway-runtime
cd exercises/04-gateway-runtime
```

시작 상태에서는 실패하고 구현 뒤에는 통과해야 합니다.

```sh
./verify.sh workspace
```

장애 실험과 자기 설명을 끝낸 뒤에만 `reference/`와 `./verify.sh reference`를 비교합니다.

## FastCGI 구성

### 애플리케이션의 `www.conf`

- 풀 작업자를 `www-data`로 실행합니다.
- TCP 9000에서 FastCGI 요청을 받습니다.
- 동적 프로세스 관리자 값을 채웁니다.
- `/ping` 요청에 `pong`을 반환합니다.

### 게이트웨이의 `default.conf.template`

- 443 포트의 TLS 서버를 구성합니다.
- `/healthz`는 Nginx가 직접 200을 반환합니다.
- 실제 파일이 없으면 `/index.php`로 내부 전달합니다.
- PHP 요청은 `${APP_UPSTREAM}`으로 전달합니다.
- `SCRIPT_FILENAME`은 app이 보는 `/var/www/html/...` 절대 경로가 되어야 합니다.

## 장애 실험

### 잘못된 업스트림 포트

```sh
APP_UPSTREAM=app:9999 docker compose -f workspace/compose.yaml up -d --build --force-recreate gateway
curl -k -i https://127.0.0.1:18443/
docker compose -f workspace/compose.yaml down --remove-orphans
```

`/healthz`와 정적 파일은 성공할 수 있지만 PHP 요청은 502를 반환합니다. 이 수동 흐름은 고정 포트 18443을 사용하므로 한 번에 하나만 실행하고 중단했으면 같은 `down --remove-orphans` 명령으로 정리합니다. 정식 verifier는 충돌하지 않는 실행 ID와 임의 host port를 사용합니다.

### 잘못된 스크립트 경로

`SCRIPT_FILENAME`의 문서 루트를 `/wrong/path`로 바꿉니다. FastCGI 연결은 되지만 PHP 파일 실행이 실패합니다.

## 권장 구현 순서

아래 번호는 실제 Git 이력이 아니라 `reference/` 전체의 학습용 construction order입니다. 파일마다 번호를 다시 시작하지 않습니다.

| 번호 | 구현 경계 |
|---:|---|
| [Implementation 0] | app의 FastCGI 도구와 gateway의 `curl`·OpenSSL dependency 설치 |
| 1 | PHP request contract |
| 2 | FPM worker·listener·ping |
| 3 | FPM image assembly |
| 4 | OpenSSL 후보 인증서 생성과 권한·entrypoint lifecycle |
| 5 | TLS·static·health·FastCGI route |
| 6 | gateway image assembly |
| 7 | bind mount·dependency·network·public port 조립 |

4번의 `openssl req -x509`는 dependency bootstrap이 아니라 개발 인증서를 만드는 중간 CLI입니다.

## 완료 기준

- [ ] `./verify.sh workspace`가 통과하고 `/healthz`, 정적 파일, PHP 동적 요청의 담당 구성요소를 각각 확인한다.
- [ ] 호스트에는 gateway만 게시되고 PHP-FPM 9000은 Compose 내부 네트워크에서만 접근된다.
- [ ] 잘못된 upstream 포트와 잘못된 `SCRIPT_FILENAME`을 주입해 연결 실패와 파일 경로 실패의 증거 차이를 기록한다.

## 자기 설명

1. `fastcgi_pass`의 주소와 `SCRIPT_FILENAME`의 경로는 왜 서로 다른 컨테이너 관점에서 해석되는가?
2. Nginx `/healthz` 성공만으로 PHP 사용자 요청의 준비 상태를 보장할 수 없는 이유는 무엇인가?
3. gateway 외 서비스를 호스트에 게시하지 않는 것이 공격 표면과 문제 진단에 어떤 영향을 주는가?
