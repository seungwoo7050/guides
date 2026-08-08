# HTTPS 게이트웨이와 PHP-FPM

Nginx가 개발용 TLS 인증서를 생성하고, 정적 파일은 직접 응답하며 PHP 요청은 FastCGI로 애플리케이션에 전달합니다.

## 통과해야 할 요청

- Nginx와 PHP-FPM의 프로토콜 경계를 구분합니다.
- `fastcgi_pass`의 네트워크 주소와 `SCRIPT_FILENAME`의 파일 경로를 구분합니다.
- FPM `/ping`을 FastCGI 클라이언트로 검사합니다.
- 게이트웨이만 호스트에 공개합니다.

## 실행

```sh
./verify.sh reference
```

시작 코드의 TODO를 채운 뒤:

```sh
./verify.sh skeleton
```

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
APP_UPSTREAM=app:9999 docker compose -f reference/compose.yaml up -d --build --force-recreate gateway
curl -k -i https://127.0.0.1:18443/
```

`/healthz`와 정적 파일은 성공할 수 있지만 PHP 요청은 502를 반환합니다.

### 잘못된 스크립트 경로

`SCRIPT_FILENAME`의 문서 루트를 `/wrong/path`로 바꿉니다. FastCGI 연결은 되지만 PHP 파일 실행이 실패합니다.
