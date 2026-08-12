# 설정과 라우터

설정은 런타임 객체를 직접 수정하지 않습니다. 별도 `Config` 후보를 토큰화하고 파싱·검증한 뒤, 검증된 라우트와 핸들러를 한 번에 구성합니다.

## 실행

```sh
make observe
make exercise-test
make test
make failure-test
```

## 잘못된 설정 확인하기

중복 라우트, 알 수 없는 지시어, 잘못된 메서드와 인자 수를 주입합니다. 생성 도중 실패해도 이미 만든 핸들러가 누수되지 않아야 합니다.

## 확인할 동작

핸들러는 소켓이나 원시 헤더를 보지 않고, 라우트 없음과 처리 결과를 구조화된 `Response`로 반환합니다.

## 권장 구현 순서

<!-- implementation-scope: cpp98-http-02 -->
아래 번호는 실제 과거 작성 순서가 아니라 권장 구현 순서입니다.

| 번호 | anchor | 책임 |
|---|---|---|
| `1` | `reference/Router.hpp` | transport와 독립된 Request·Response·Handler 계약을 정의합니다. |
| `2` | `reference/Router.hpp` | configuration 오류와 RouteSpec model을 만듭니다. |
| `3` | `reference/Router.cpp` | 설정 전체를 candidate route 목록으로 검증합니다. |
| `4` | `reference/Router.cpp` | socket을 모르는 concrete handler 동작을 구현합니다. |
| `5` | `reference/Router.cpp` | handler 수명과 검증된 route dispatch를 Router에 commit합니다. |
| `6` | `demo.cpp` | 설정에서 만든 Router의 health·echo 선택을 관찰합니다. |
<!-- /implementation-scope -->
