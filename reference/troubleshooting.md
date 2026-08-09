# 문제 해결

## 증상부터 package를 바꾸지 않습니다

```text
재현 가능한 사용자 action
→ 마지막 성공 계층
→ 첫 실패 계층
→ 관련 state와 artifact identity
→ 한 가지 가설
→ 반증 가능한 검사
```

## app가 시작 즉시 종료됩니다

확인 순서:

1. app version/build/runtime와 device OS
2. native crash log
3. 최근 native package/config/plugin 변경
4. generated manifest/plist/entitlement
5. development vs preview build 차이
6. JS bundle 실행 전인지 후인지

Metro error와 native crash를 같은 로그로 다루지 않는다.

## Expo Go에서는 되고 development build에서는 안 됩니다

- Expo Go에 포함된 module과 프로젝트 binary의 module 집합 비교
- config plugin 적용 여부
- native build를 변경 후 다시 만들었는지
- app identifier·permission·environment
- stale installed binary/runtime

Expo Go 성공을 native 설정 증거로 사용하지 않는다.

## SDK 57 프로젝트가 물리 기기 Expo Go에서 열리지 않습니다

2026-08 현재 Expo의 공식 create-project 안내는 transition 동안 물리 기기 Expo Go에는 SDK 54를 사용하라고 명시한다. 이 브랜치는 SDK 57을 고정하므로 다음을 확인한다.

- emulator/simulator 또는 SDK 57 development build를 사용하는가
- `npx expo start --dev-client`로 올바른 installed binary에 연결했는가
- installed build의 native module 집합과 현재 package/config가 같은가
- Expo Go 성공/실패를 permission·config·signing evidence로 오해하지 않았는가

## permission dialog가 나오지 않습니다

- 현재 permission 상태와 `canAskAgain`
- native usage description/manifest가 실제 binary에 있는지
- 기능 action 안에서 request하는지
- Expo Go 제한
- Settings에서 이미 거절/제한했는지
- simulator/device capability
- Android 13+에서는 stable notification channel을 permission/token 요청 전에 생성했는지

## picker 뒤 결과가 사라집니다

- cancel/error/success 구분
- Android Activity/process recreation
- pending result recovery
- temporary URI를 언제 durable file로 copy하는지
- duplicate result marker
- file copy와 DB transaction 사이 failure

## offline save가 사라집니다

- UI state만 바꿨는지
- SQLite transaction commit 시점
- draft와 saved record 의미
- schema migration 오류
- cache directory/AsyncStorage 오용
- process kill로 실제 재현했는지

## sync가 계속 pending입니다

- outbox row state와 lease expiry
- session blocked/auth refresh
- network hint와 실제 request result
- retry nextAttemptAt와 maximum attempts
- foreground/background worker claim 충돌
- malformed response
- conflict를 retry로 잘못 처리했는지

## 같은 record가 두 번 생성됩니다

- commandId를 retry마다 새로 만드는지
- server duplicate handling
- timeout 뒤 UNKNOWN을 새 create로 처리했는지
- button double tap과 local transaction
- notification/background trigger가 별도 command를 만드는지

## 오래된 server 값이 편집을 덮습니다

- active command localRevision
- response generation/command identity
- active 중 새 edit가 queued됐는지
- success transaction이 current localRevision을 비교하는지
- query refresh가 local pending record를 무조건 replace하는지

## background task가 실행되지 않습니다

먼저 정확성 문제가 아닌지 확인한다. foreground resume에서 sync되는가?

그 뒤:

- development build/native config
- task definition load 위치
- registration state
- OS capability·battery·network
- app force-stop/recent removal
- iOS simulator 제한과 실제 device
- Android vendor 정책
- task trace와 next pending count

interval을 exact schedule로 기대하지 않는다.

## notification tap이 잘못된 화면을 엽니다

- payload runtime parsing
- cold/warm start 차이
- pending intent와 startup readiness
- account/tenant mismatch
- record 최신 상태 재조회
- duplicate/old message id
- existing edit draft와 route policy

## update 뒤 native method가 없습니다

- installed build의 runtimeVersion
- update runtime target
- native dependency/config가 바뀌었는지
- 새 binary 없이 remote update만 배포했는지
- preview channel에서 같은 runtime을 검사했는지

## 삭제 후 재설치했는데 session이 남습니다

- iOS Keychain-backed SecureStore 값이 같은 bundle identifier에서 남았는지
- 여러 secure key를 원자 transaction처럼 가정했는지
- credential envelope/generation과 startup reconciliation이 손상 상태를 거부하는지
- reinstall을 logout 또는 credential 삭제의 보장으로 문서화했는지

## AAB를 기기에 설치할 수 없습니다

AAB는 Play가 device별 APK를 만드는 publishing format이다. 직접 설치 smoke에는 debug/release APK 또는 Play가 전달한 split APK/test track을 사용한다. iOS archive도 export/provision 또는 TestFlight 설치 evidence와 구분한다.

## 성능이 느립니다

release build와 실제 device인지 먼저 확인한다.

- startup 구간 분리
- JS/UI/native thread profile
- list rerender와 query
- image decode/cache
- main-thread native I/O
- excessive log
- retry/polling/background 작업
- DB index/migration

추측으로 memoization이나 native module을 추가하지 않는다.

## evidence에 포함할 것

```text
source revision
app/build/runtime/update
platform/device/OS
initial DB/outbox/file/session state
exact user action
normalized logs/traces
expected vs actual final state
```

credential, record content, image, 정확한 위치는 제거한다.
