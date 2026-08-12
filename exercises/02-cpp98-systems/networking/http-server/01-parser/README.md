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

## 권장 구현 순서

<!-- implementation-scope: cpp98-http-01 -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/HttpParser.hpp` | byte buffer와 ready request·sticky error 상태 계약을 정의합니다. |
| `2` | `reference/HttpParser.cpp` | protocol 상한과 header·body helper 검증을 만듭니다. |
| `3` | `reference/HttpParser.cpp` | ready/error 상태를 보존하며 새 byte를 parser에 공급합니다. |
| `4` | `reference/HttpParser.cpp` | 요청 줄·header·body를 검증한 뒤 request를 commit합니다. |
| `5` | `reference/HttpParser.cpp` | 완성 request를 꺼내고 다음 pipeline message를 준비합니다. |
| `6` | `demo.cpp` | 분할 feed의 NeedMore→Complete 전이를 관찰합니다. |
<!-- /implementation-scope -->
