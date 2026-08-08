# 점진적 HTTP 파서

`feed`는 임의 크기의 바이트 조각을 받고 `NeedMore`, `Complete`, `Error` 중 하나를 반환합니다. 소켓이나 라우트를 알지 않고 HTTP/1.1 요청 줄, 헤더와 `Content-Length` 본문만 처리합니다.

## 실행

```sh
make observe
make exercise-test
make test
make failure-test
```

## 잘못된 요청 확인하기

`Host` 누락, 중복 `Content-Length`, 잘못된 헤더 이름, 헤더·본문 상한
초과와 지원하지 않는 전송 인코딩을 독립적으로 거부합니다. 헤더 8192바이트와
100개는 허용하지만 그다음 바이트나 헤더는 거부합니다. 여러 `feed` 호출로
나뉜 입력도 같은 상한을 적용합니다.

## 확인할 동작

분할 입력과 파이프라인 입력에서 완성된 요청만 꺼내며, 오류 뒤 파서 상태를 명시적으로 처리합니다.
