# Nginx, TLS와 PHP-FPM

이 장에서는 외부 HTTPS 요청을 Nginx가 받아 정적 파일은 직접 응답하고 PHP 요청은 PHP-FPM으로 전달하는 구조를 만듭니다.

핵심은 설정 지시어를 암기하는 것이 아니라 요청이 어느 프로토콜과 파일 경로를 거치는지 추적하는 것입니다.

```text
curl 또는 브라우저
       │ HTTPS
       ▼
    Nginx :443
       │ FastCGI
       ▼
  PHP-FPM :9000
       │
       ▼
  /var/www/html/index.php
```

## 1. 역할 분리

### Nginx

- TCP 연결과 HTTP(S) 요청을 받습니다.
- TLS를 종료합니다.
- 정적 파일을 직접 응답합니다.
- 요청 경로를 분류합니다.
- 동적 요청을 다른 프로세스로 전달합니다.
- upstream 오류를 클라이언트 응답으로 변환합니다.

### PHP-FPM

- PHP worker 프로세스를 미리 유지합니다.
- FastCGI 요청을 받습니다.
- 지정된 PHP 파일을 실행합니다.
- 실행 결과를 FastCGI 응답으로 반환합니다.

### PHP 애플리케이션

- 요청 입력을 읽습니다.
- 비즈니스 로직을 실행합니다.
- 데이터베이스에 접근합니다.
- HTTP 응답으로 변환될 헤더와 본문을 생성합니다.

Nginx는 PHP 언어를 직접 실행하지 않습니다. PHP-FPM은 일반 브라우저가 말하는 HTTP 서버가 아닙니다. 둘 사이를 FastCGI가 연결합니다.

## 2. 왜 한 프로세스에 모두 넣지 않는가

역할을 나누면 다음 경계가 생깁니다.

- 외부 네트워크에 노출되는 것은 Nginx뿐입니다.
- PHP worker 수와 Nginx 연결 처리를 별도로 조정할 수 있습니다.
- 정적 요청은 PHP 실행 비용 없이 처리합니다.
- TLS 인증서와 웹 라우팅을 gateway에 집중합니다.
- app을 교체해도 gateway의 외부 주소를 유지할 수 있습니다.

대신 설정과 장애 지점이 늘어납니다. 502가 발생하면 Nginx, DNS, 포트, FastCGI, PHP-FPM 중 어느 지점인지 찾아야 합니다. 이 장의 실습은 바로 그 경계를 관찰합니다.

## 3. Nginx 설정의 구조

Nginx 설정은 컨텍스트가 중첩된 트리입니다.

```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;

    server {
        listen 443 ssl;

        location / {
            try_files $uri $uri/ /index.php?$query_string;
        }
    }
}
```

주요 컨텍스트:

- main: 파일 최상위, worker 프로세스 등
- `events`: 연결 처리 방식
- `http`: HTTP 전반 설정
- `server`: 주소·포트와 Host 이름으로 구분되는 가상 서버
- `location`: 한 server 안에서 URI를 처리하는 규칙

공식 Nginx 이미지에서는 기본 `nginx.conf`가 `http` 컨텍스트 안에서 `/etc/nginx/conf.d/*.conf`를 포함합니다. 실습은 전체 파일을 교체하지 않고 `server` 블록 파일을 제공합니다.

설정을 적용하기 전에 문법을 검사합니다.

```sh
nginx -t
```

컨테이너에서는 다음과 같이 실행할 수 있습니다.

```sh
docker compose exec gateway nginx -t
```

## 4. `listen`과 `server_name`

```nginx
server {
    listen 443 ssl default_server;
    listen [::]:443 ssl default_server;
    server_name _;
}
```

`listen`은 어떤 주소와 포트에서 요청을 받을지 정합니다. 같은 포트에 여러 server 블록이 있으면 Nginx는 요청의 Host 헤더와 `server_name`을 비교합니다. 일치하지 않으면 해당 listen 주소의 default server가 처리합니다.

단일 학습 사이트에서는 `_`를 캐치올 이름처럼 사용하지만, 실제 다중 사이트에서는 명시적 도메인과 default server 정책을 둡니다.

### HTTP/2 문법

최근 Nginx에서는 다음처럼 별도 지시어를 사용합니다.

```nginx
listen 443 ssl;
http2 on;
```

오래된 버전은 `listen 443 ssl http2;`를 사용합니다. 설정을 다른 버전으로 옮길 때 `nginx -t`와 해당 버전 공식 문서를 확인합니다. 이 저장소의 실습 이미지는 별도 `http2 on;` 문법을 사용하는 버전을 전제로 합니다.

## 5. 문서 루트와 정적 파일

```nginx
root /var/www/html;
index index.php index.html;
```

요청 URI `/assets/site.css`는 기본적으로 다음 파일 경로와 결합됩니다.

```text
/var/www/html/assets/site.css
```

정적 파일이 존재하고 Nginx worker가 읽을 권한이 있으면 Nginx가 직접 응답합니다.

확인할 것:

```sh
docker compose exec gateway ls -l /var/www/html
docker compose exec gateway id
```

경로가 맞아도 상위 디렉터리에 execute 권한이 없거나 파일에 read 권한이 없으면 403이 발생할 수 있습니다.

## 6. `location` 매칭

자주 쓰는 형식:

```nginx
location = /healthz { ... }      # 정확 일치
location ^~ /assets/ { ... }     # 우선 prefix
location / { ... }               # 일반 prefix
location ~ \.php$ { ... }        # 대소문자 구분 정규식
location ~* \.(jpg|png)$ { ... } # 대소문자 무시 정규식
```

단순화한 선택 순서:

1. 정확 일치 `=`가 맞으면 즉시 선택합니다.
2. prefix 중 가장 긴 것을 찾습니다.
3. 선택된 prefix가 `^~`이면 정규식을 건너뜁니다.
4. 그렇지 않으면 선언 순서대로 정규식을 검사하고 첫 일치를 선택합니다.
5. 정규식이 없으면 가장 긴 prefix를 사용합니다.

정규식 location의 순서는 결과에 영향을 줄 수 있습니다. 요청이 예상과 다른 location으로 들어간다면 파일 존재보다 먼저 location 선택을 확인합니다.

## 7. `try_files`

PHP 애플리케이션의 일반적인 front controller 패턴:

```nginx
location / {
    try_files $uri $uri/ /index.php?$query_string;
}
```

처리 순서:

1. URI에 대응하는 파일이 있으면 정적 파일로 응답합니다.
2. 디렉터리가 있으면 그 경로를 사용합니다.
3. 둘 다 없으면 `/index.php`로 내부 redirect합니다.
4. 내부 redirect된 URI는 다시 location 선택을 거쳐 PHP location으로 들어갑니다.

`try_files`의 마지막 값은 클라이언트에게 302를 보내는 외부 redirect가 아닙니다. Nginx 내부에서 URI를 다시 처리합니다.

PHP location에서도 실행할 파일이 실제로 있는지 확인합니다.

```nginx
location ~ \.php$ {
    try_files $uri =404;
    ...
}
```

이 검사가 없으면 공격자가 존재하지 않는 PHP 경로를 이용해 잘못된 FastCGI 설정을 악용할 가능성이 커집니다.

## 8. TLS의 구성요소

### 개인키

서버만 보유해야 하는 비밀 파일입니다. 인증서와 TLS 핸드셰이크에서 서버가 키를 보유하고 있음을 증명하는 데 사용합니다.

### 인증서

다음을 포함하는 X.509 문서입니다.

- 공개키
- subject와 발급자
- 유효기간
- 도메인 이름을 나타내는 SAN
- 발급자의 서명

### CA와 신뢰 체인

클라이언트는 인증서의 서명을 따라 신뢰하는 CA까지 연결되는지 확인합니다. 도메인 일치, 유효기간, 용도도 확인합니다.

### 자체 서명 인증서

자신의 개인키로 자신의 인증서에 서명합니다. 암호화 통신은 가능하지만 클라이언트가 사전에 신뢰하지 않으면 서버 신원을 검증할 수 없습니다.

로컬 실습에서 사용하되 다음을 분명히 구분합니다.

```sh
curl -k https://127.0.0.1:18443/
```

`-k`는 인증서를 신뢰 목록에 추가하지 않습니다. 검증을 끕니다.

## 9. 개발용 인증서 생성

실습 시작 스크립트는 파일이 없을 때만 인증서를 만듭니다.

```sh
openssl req -x509 -newkey rsa:2048 -nodes \
  -days 30 \
  -subj "/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
  -keyout /etc/nginx/tls/development.key \
  -out /etc/nginx/tls/development.crt
```

주요 옵션:

- `req`: CSR/인증서 요청 관련 서브커맨드
- `-x509`: CSR 대신 self-signed 인증서를 바로 생성
- `-newkey rsa:2048`: 새 RSA 키 생성
- `-nodes`: 개인키를 passphrase로 암호화하지 않음
- `-subj`: 대화형 질문 없이 subject 설정
- `-addext subjectAltName=...`: 클라이언트가 확인할 호스트 이름과 IP
- `-days`: 유효기간

무인 서버는 부팅 때 개인키 passphrase를 사람이 입력할 수 없으므로 평문 PEM 키를 사용하는 경우가 많습니다. 대신 파일 권한과 secret 저장소로 키를 보호합니다.

```sh
chmod 600 /etc/nginx/tls/development.key
```

인증서 내용을 검사합니다.

```sh
openssl x509 -in development.crt -noout -subject -issuer -dates -ext subjectAltName
```

## 10. Nginx TLS 설정

```nginx
ssl_certificate     /etc/nginx/tls/development.crt;
ssl_certificate_key /etc/nginx/tls/development.key;
ssl_protocols       TLSv1.2 TLSv1.3;
```

인증서와 키가 서로 맞지 않거나 읽을 수 없으면 Nginx가 시작하지 못합니다. 로그에 키 로드 오류가 나타납니다.

TLS 설정은 인증서 경로만의 문제가 아닙니다. 운영 환경에서는 다음도 관리해야 합니다.

- 신뢰 가능한 CA 발급
- 체인 인증서
- 자동 갱신
- 키 회전
- HSTS 적용 조건
- cipher 정책과 클라이언트 호환성

이 가이드에서는 로컬 TLS 요청 경로를 이해하는 데 필요한 범위까지만 다룹니다.

## 11. PHP-FPM의 프로세스 모델

PHP-FPM은 master 프로세스와 worker 프로세스로 구성됩니다.

```text
php-fpm master (PID 1)
├─ worker 1 (www-data)
├─ worker 2 (www-data)
└─ worker 3 (www-data)
```

master는 설정을 읽고 worker를 생성·종료합니다. worker는 실제 PHP 요청을 처리합니다. 일반적인 PHP-FPM worker 하나는 한 시점에 요청 하나를 처리합니다.

Nginx와 PHP-FPM을 별도 컨테이너로 실행하면 PHP-FPM master가 app 컨테이너의 PID 1이 됩니다.

```dockerfile
CMD ["php-fpm", "-F"]
```

`-F`는 foreground 실행을 뜻합니다.

## 12. FPM pool 설정

예제:

```ini
[www]
user = www-data
group = www-data
listen = 9000

pm = dynamic
pm.max_children = 8
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3

ping.path = /ping
ping.response = pong
clear_env = no
catch_workers_output = yes
decorate_workers_output = no
```

### `listen`

FastCGI 요청을 받을 주소입니다.

- `9000` 또는 `0.0.0.0:9000`: TCP
- `/run/php/php-fpm.sock`: Unix domain socket

Nginx와 PHP-FPM이 다른 컨테이너라면 파일 시스템의 Unix socket을 기본적으로 공유하지 않습니다. 같은 Docker 네트워크의 TCP `app:9000`이 단순합니다.

app의 9000 포트를 호스트에 게시할 필요는 없습니다. gateway만 같은 내부 네트워크에서 접근합니다.

### 작업자 사용자

`user`와 `group`은 PHP 코드를 실행하는 작업자의 권한입니다. 웹 파일과 쓰기 디렉터리의 소유권이 이 사용자와 맞아야 합니다.

### 프로세스 관리 모드

- `static`: `pm.max_children`만큼 항상 유지
- `dynamic`: 최소·최대 예비 작업자 범위에 맞춰 증감
- `ondemand`: 요청이 올 때 생성하고 유휴 시 종료

일반적인 웹 서비스에서는 동적 방식이 균형 잡힌 시작점이지만 트래픽과 메모리 조건에 따라 다릅니다.

### `pm.max_children`

동시에 실행 가능한 PHP 요청의 대략적인 상한이자 최대 메모리 사용량을 결정하는 값입니다.

```text
max_children ≈ PHP에 할당 가능한 메모리 / 작업자 하나의 관측 RSS
```

추측으로 크게 잡지 않습니다. 실제 요청을 처리하는 작업자의 메모리를 측정하고, 주 프로세스·OPcache·운영체제 여유를 제외합니다. 값이 너무 작으면 요청이 대기하고, 너무 크면 메모리 부족이 발생할 수 있습니다.

## 13. FastCGI

FastCGI는 웹 서버가 애플리케이션 프로세스에 요청 정보를 전달하고 결과를 받는 프로토콜입니다. HTTP 클라이언트인 `curl`을 FPM 9000 포트에 직접 보내면 말이 통하지 않습니다.

Nginx는 HTTP 요청을 FastCGI parameter로 변환합니다.

```text
HTTP method        → REQUEST_METHOD
URI path           → SCRIPT_NAME, REQUEST_URI
query string       → QUERY_STRING
server file path   → SCRIPT_FILENAME
content metadata   → CONTENT_TYPE, CONTENT_LENGTH
```

FPM은 `SCRIPT_FILENAME`으로 실행할 PHP 파일을 결정합니다. 이 값이 잘못되면 네트워크 연결이 성공해도 `Primary script unknown` 또는 `File not found`가 발생합니다.

## 14. Nginx에서 FPM으로 전달

```nginx
location ~ \.php$ {
    try_files $uri =404;

    include fastcgi_params;
    fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    fastcgi_param HTTPS on;
    fastcgi_pass app:9000;
}
```

### `fastcgi_pass`

FastCGI 서버 주소입니다.

```text
app:9000
```

`app`은 Compose 서비스 이름이며 Docker DNS가 주소를 제공합니다.

### `include fastcgi_params`

요청 메서드, 쿼리 문자열, 콘텐츠 길이 등 일반 FastCGI parameter를 포함합니다. 배포판과 이미지에 따라 파일 경로와 포함 내용이 다를 수 있으므로 실제 파일을 확인합니다.

### `SCRIPT_FILENAME`

```text
$document_root + $fastcgi_script_name
```

요청 `/index.php`와 root `/var/www/html`을 결합해 `/var/www/html/index.php`를 만듭니다.

Nginx 컨테이너와 app 컨테이너가 같은 경로에서 같은 PHP 파일을 볼 수 있어야 합니다. 한쪽은 `/srv/site/index.php`, 다른 쪽은 `/var/www/html/index.php`로 보면 Nginx가 만든 경로가 app에 존재하지 않습니다.

### `HTTPS on`

Nginx에서 TLS를 종료한 뒤 FPM에는 FastCGI로 전달합니다. 애플리케이션이 원래 요청이 HTTPS였음을 알아야 링크와 redirect를 올바르게 생성할 수 있습니다.

## 15. 파일 공유 전략

### 코드가 각 이미지에 포함되는 방식

빌드 시 같은 소스를 gateway와 app 이미지에 각각 복사할 수 있습니다. 배포 아티팩트가 불변이고 volume 의존이 적습니다. 두 이미지가 반드시 같은 커밋으로 빌드되도록 관리해야 합니다.

### 공유 볼륨 또는 호스트 경로 마운트

Nginx는 읽기 전용, 애플리케이션은 필요에 따라 읽기·쓰기로 같은 경로를 봅니다.

```yaml
volumes:
  - type: bind
    source: ./app/public
    target: /var/www/html
    read_only: true
```

개발 환경에서는 간단하지만 호스트 파일 권한과 경로에 종속됩니다. 운영에서는 정적 파일을 별도 이미지나 객체 저장소로 배포할 수도 있습니다.

실습은 요청 경로를 눈으로 확인하기 위해 동일한 `public` 디렉터리를 두 서비스에 읽기 전용으로 마운트합니다.

## 16. 계층별 검사

### Nginx HTTPS

```sh
curl -kfsS https://127.0.0.1:18443/healthz
```

### TLS 인증서

```sh
openssl s_client -connect 127.0.0.1:18443 -servername localhost </dev/null
```

### Nginx 설정

```sh
docker compose exec gateway nginx -t
```

### FPM 포트

```sh
docker compose exec app sh -c 'php -r '\''$s=fsockopen("127.0.0.1",9000,$e,$m,1); exit($s?0:1);'\'''
```

이 검사는 TCP 포트까지만 봅니다.

### FPM ping

```sh
docker compose exec app sh -c '
  REQUEST_METHOD=GET \
  SCRIPT_NAME=/ping \
  SCRIPT_FILENAME=/ping \
  cgi-fcgi -bind -connect 127.0.0.1:9000
'
```

FastCGI 응답에 `pong`이 있어야 FPM이 실제 요청을 처리한 것입니다.

### 프로세스와 로그

```sh
docker compose exec app ps -ef
docker compose logs gateway
docker compose logs app
```

## 17. 오류를 계층으로 분류하기

### 연결 거부

호스트 포트가 게시되지 않았거나 gateway가 실행 중이지 않습니다. `docker compose ps`, host의 `ss`, gateway 로그를 봅니다.

### TLS 오류

인증서 신뢰, SAN, 유효기간, 키 불일치 문제입니다. `curl -v`, `openssl s_client`, Nginx 시작 로그를 봅니다.

### 404

Nginx가 HTTP 응답을 반환했습니다. location 선택, `root`, `try_files`, 파일 존재를 봅니다.

### 403

Nginx 실행 사용자가 경로를 읽거나 통과할 권한이 없을 수 있습니다. `namei -l`, `ls -ld`, `id`를 사용합니다.

### 502 Bad Gateway

Nginx가 app에 연결하거나 유효한 FastCGI 응답을 받지 못했습니다.

확인 순서:

1. app 컨테이너 실행 상태
2. PHP-FPM 프로세스
3. app의 9000 listen
4. gateway에서 `app` DNS 해석
5. `fastcgi_pass` 포트
6. FPM 로그

### `File not found` 또는 `Primary script unknown`

FastCGI 연결은 됐지만 `SCRIPT_FILENAME`이 app 파일 시스템의 실제 PHP 파일과 맞지 않습니다. 두 컨테이너 안에서 경로를 각각 확인합니다.

### HTTP 500

PHP가 실행됐지만 애플리케이션 내부 오류가 발생했습니다. PHP-FPM stderr와 애플리케이션 로그를 봅니다.

## 18. 실습

실습 위치:

```sh
python3 scripts/new-workspace.py exercises/04-gateway-runtime
cd exercises/04-gateway-runtime
```

### 실습 1: 자신의 gateway/runtime 실행

```sh
./verify.sh workspace
```

다음을 검증합니다.

- 게이트웨이 HTTPS 상태 검사
- 정적 파일 응답
- PHP 응답
- 애플리케이션 FastCGI 연결 확인
- 외부에 게이트웨이 포트만 게시됨

### 실습 2: 시작 코드 완성

`workspace/gateway/default.conf.template`과 `workspace/app/www.conf`의 미완성 경계를 채웁니다.

실행 전 다음을 답합니다.

- Nginx가 app을 어떤 이름과 포트로 찾는가?
- `/index.php`가 app 안에서 어느 절대 경로가 되는가?
- FPM ping은 HTTP 요청인가?
- Nginx와 app이 각각 어떤 파일 경로를 보는가?

### 실습 3: 잘못된 FastCGI 포트

`APP_UPSTREAM=app:9999`로 gateway를 재생성합니다.

예상:

- 게이트웨이 자체 상태 검사는 성공할 수 있습니다.
- 정적 파일은 성공할 수 있습니다.
- PHP 요청은 502가 됩니다.

이는 gateway의 생존과 전체 애플리케이션 준비가 다른 상태임을 보여 줍니다.

### 실습 4: 잘못된 `SCRIPT_FILENAME`

Nginx 템플릿에서 `/var/www/html`을 `/wrong/path`로 바꿉니다.

예상:

- app 포트와 FastCGI 연결은 성공합니다.
- PHP 파일 실행만 실패합니다.
- 오류 계층은 네트워크가 아니라 파일 경로입니다.

두 장애의 증거와 자기 설명을 마친 뒤에만 `reference/`와 `./verify.sh reference`를 비교합니다.

## 19. 계층을 혼동하기 쉬운 오류

### “PHP-FPM 포트에 curl을 보내면 됩니다”

FPM은 FastCGI를 말합니다. HTTP curl은 적절한 클라이언트가 아닙니다.

### “Nginx와 애플리케이션이 같은 볼륨을 쓰면 경로가 달라도 됩니다”

`SCRIPT_FILENAME`은 app이 해석하는 경로입니다. 같은 파일을 같은 절대 경로로 보는 구성이 가장 단순합니다.

### “자체 서명 인증서도 암호화되니 운영에서 그대로 안전합니다”

암호화와 신원 검증은 다릅니다. 클라이언트가 신뢰하도록 배포한 사설 CA가 아니라 단순 self-signed라면 서버 신원을 검증할 수 없습니다.

### “502는 PHP 코드 오류입니다”

대부분 gateway와 upstream 통신 계층을 먼저 의심합니다. PHP 코드가 유효한 FastCGI 응답으로 500을 반환하면 클라이언트는 일반적으로 500을 봅니다.

## 20. 게이트웨이 점검

- Nginx는 외부 HTTP(S), PHP-FPM은 내부 FastCGI를 담당합니다.
- `location`과 `try_files`가 정적·동적 요청을 분류합니다.
- TLS 인증서와 개인키는 서로 다른 자산이며 자체 서명 인증서는 기본 신뢰를 제공하지 않습니다.
- PHP-FPM은 주 프로세스와 작업자 풀로 동작합니다.
- `pm.max_children`은 동시성과 메모리 상한을 함께 결정합니다.
- `fastcgi_pass`는 네트워크 주소, `SCRIPT_FILENAME`은 app 파일 시스템 경로입니다.
- 404, 403, 502, 500은 서로 다른 계층을 우선 가리킵니다.
- 상태 검사는 서비스가 실제로 사용하는 프로토콜로 수행합니다.

## 공식 문서

- Nginx 요청 처리: https://nginx.org/en/docs/http/request_processing.html
- Nginx FastCGI 모듈: https://nginx.org/en/docs/http/ngx_http_fastcgi_module.html
- Nginx SSL 모듈: https://nginx.org/en/docs/http/ngx_http_ssl_module.html
- PHP-FPM 설정: https://www.php.net/manual/en/install.fpm.configuration.php
- OpenSSL `req`: https://docs.openssl.org/master/man1/openssl-req/
