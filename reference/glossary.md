# 용어

이 문서는 처음 등장한 용어를 빠르게 다시 찾기 위한 보조 자료입니다. 정의를 외우기보다 해당 문서와 실습에서 입력·출력·실패를 함께 확인합니다.

## Client

다른 process나 service에 요청을 보내는 쪽입니다. 웹에서는 주로 browser가 HTTP client이지만, API server가 PostgreSQL이나 외부 API의 client가 되기도 합니다.

## Server

요청을 기다리고 계약에 따라 응답하는 process입니다. “서버”는 반드시 별도 물리 컴퓨터를 뜻하지 않으며 개발 중에는 같은 컴퓨터의 다른 port에서 실행될 수 있습니다.

## URL

scheme, host, port, path, query와 fragment로 자원의 위치와 요청 대상을 표현합니다. fragment는 일반 HTTP 요청에 전송되지 않습니다.

## Origin

scheme, host와 port의 조합입니다. 브라우저의 same-origin policy, CORS와 CSRF 판단에서 사용합니다.

## Runtime

코드가 실제로 실행되는 환경입니다. browser와 Node.js는 같은 JavaScript 문법을 사용해도 제공 API와 비밀값 경계가 다릅니다.

## 상태와 정본

상태는 시간에 따라 변하는 값이며, 정본(source of truth)은 서로 다른 복사본이 충돌할 때 최종 기준이 되는 위치입니다. URL, server, component와 임시 실시간 상태의 소유자를 구분합니다.

## 계약

두 구성 요소가 교환하는 입력, 출력, 오류와 수명을 정한 약속입니다. TypeScript 형뿐 아니라 실행 시점 schema, HTTP status와 종료 뒤 상태도 포함합니다.

## Schema

외부 값이나 데이터베이스 구조가 가져야 할 모양과 제약입니다. TypeScript 형은 실행 중 사라지므로 HTTP·storage·DB 경계에서는 runtime schema나 DB constraint가 별도로 필요합니다.

## Adapter

외부 시스템의 세부 형식과 애플리케이션 내부 모델 사이를 변환하는 경계입니다. HTTP client, repository와 WebSocket transport가 대표적입니다.

## Migration

데이터베이스 schema를 한 알려진 버전에서 다음 버전으로 이동시키는 변경입니다. application startup과 분리하고, 기존 데이터·재실행·rollback 또는 forward recovery 정책을 고려합니다.

## Transaction

여러 데이터베이스 변경을 하나의 성공 또는 실패 단위로 묶습니다. 항목 갱신과 활동 event처럼 함께 성공해야 하는 쓰기를 보호합니다.

## 세션

로그인 이후 여러 요청에서 같은 사용자를 식별하기 위한 server 상태입니다. browser에는 불투명 token을 cookie로 전달하고 server는 만료·폐기·계정 상태를 확인합니다.

## 인증과 권한

인증(authentication)은 “누구인가”, 권한(authorization)은 “이 자원에 무엇을 할 수 있는가”를 판정합니다. 로그인 성공만으로 모든 자원 접근이 허용되지는 않습니다.

## CORS

브라우저가 다른 origin의 응답을 frontend JavaScript에 공개할 수 있는지 server가 알리는 정책입니다. 요청자의 신원이나 자원 권한을 대신하지 않습니다.

## CSRF

사용자의 cookie가 자동 전송되는 성질을 이용해 다른 site가 원치 않는 상태 변경을 보내는 공격입니다. SameSite, Origin 검사와 CSRF token을 제품 구조에 맞게 조합합니다.

## XSS

신뢰하지 않는 입력이 HTML이나 JavaScript로 해석되어 실행되는 취약점입니다. text 렌더링, 검증된 정화, 안전한 template와 Content Security Policy로 위험을 줄입니다.

## Hydration

server가 만든 HTML에 browser의 React 동작을 연결하는 과정입니다. server와 browser의 첫 render가 다르면 mismatch가 발생합니다.

## 서버 권위 상태

여러 client가 서로 다른 값을 가질 때 server가 최종 정본을 결정하는 방식입니다. 협업 보드에서는 좌표 범위, role, item version과 event sequence를 server가 확정합니다.

## Snapshot

특정 시점의 전체 상태입니다. 연결 직후, patch 누락 또는 재연결 뒤 복구 기준으로 사용합니다.

## Patch

전체 snapshot보다 작은 한 번의 확정 변경입니다. sequence와 version을 함께 보내 누락·역전·충돌을 감지합니다.

## 낙관적 동시성

읽은 version을 변경 요청에 포함하고 저장 시 현재 version과 같을 때만 갱신하는 방식입니다. 충돌은 조용히 덮지 않고 최신 상태와 사용자 draft를 함께 보존합니다.

## 멱등성

같은 작업을 여러 번 시도해도 최종 효과가 한 번 수행한 것과 같은 성질입니다. 종료 함수, migration, 재시도 가능한 요청과 operation ID에서 중요합니다.

## Backpressure

생산 속도가 소비 속도보다 빠를 때 queue와 memory가 무한히 커지지 않도록 흐름을 제한하는 계약입니다. WebSocket `bufferedAmount`, bounded queue와 느린 client 정책이 예입니다.

## Heartbeat

WebSocket ping/pong처럼 응답하지 않는 연결을 찾아 정리하는 절차입니다. application message가 없다는 이유만으로 연결이 끊겼다고 단정하지 않습니다.
