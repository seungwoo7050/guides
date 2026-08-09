# 실무 체크리스트

기존 React Native·Expo 저장소에 합류하거나 release를 검토할 때 빠뜨리기 쉬운 경계를 찾는 질문이다. 체크 수가 완료를 자동 판정하지 않는다. 각 답에는 source, 실행 결과 또는 사람 검토 evidence가 있어야 한다.

## 프로젝트 합류

- [ ] 지원 Android·iOS 최소 version과 Expo/RN/package patch를 lockfile에서 찾았다.
- [ ] Node/npm pin, package manager와 clean install/test 명령을 확인했다.
- [ ] Expo Go, development, preview와 production build의 증명 범위를 구분했다.
- [ ] `android/`·`ios/`를 직접 소유하는지 CNG로 생성하는지 확인했다.
- [ ] app identifier, backend environment, update channel과 signing owner를 찾았다.
- [ ] 실제로 실행하지 못한 build·device·account 항목을 `not-run`으로 기록했다.

## runtime·navigation·상태

- [ ] OS process, installed native binary, application coordinator와 repository owner를 구분했다.
- [ ] memory, route, draft, SQLite, file, credential와 remote 정본을 구분했다.
- [ ] startup의 migration·session·initial intent 순서와 fallback을 설명할 수 있다.
- [ ] internal link, external link, notification과 restoration을 같은 validated intent로 만든다.
- [ ] malformed·stale·duplicate intent와 DB/session 준비 전 intent를 처리한다.
- [ ] process 종료 뒤 복원할 상태와 버릴 상태가 정해져 있다.
- [ ] Android back, iOS gesture, modal dismiss와 업무 cancel을 혼동하지 않는다.

## UI·입력·접근성

- [ ] safe area와 keyboard가 주요 action·error를 가리지 않는다.
- [ ] 작은 화면, 큰 글자, 긴 번역과 회전 뒤 draft·action을 잃지 않는다.
- [ ] touch target, icon label·role·state와 gesture 대체 action이 있다.
- [ ] route/modal/error 뒤 keyboard와 screen-reader focus 목적지가 있다.
- [ ] TalkBack과 VoiceOver에서 핵심 흐름을 실제 device로 수행했다.
- [ ] 자동 accessibility 검사가 사람의 읽기·focus 경험을 증명한다고 표현하지 않는다.

## network·session

- [ ] network hint와 실제 request·runtime parse·업무 결과를 구분한다.
- [ ] access/refresh credential을 일반 DB·preference와 분리한다.
- [ ] 여러 SecureStore key 쓰기를 원자 transaction으로 가정하지 않는다.
- [ ] reinstall 뒤 iOS Keychain-backed credential이 남는 경우를 처리한다.
- [ ] 동시 401 refresh를 조정하고 auth block과 retry를 구분한다.
- [ ] timeout 뒤 server 결과가 UNKNOWN일 수 있다.
- [ ] cancellation과 stale result guard를 함께 사용한다.

## local·offline·sync

- [ ] 핵심 화면은 durable local database를 읽는다.
- [ ] save와 outbox command 생성이 한 transaction이다.
- [ ] attempted command의 id·payload·baseVersion은 retry 동안 불변이다.
- [ ] unattempted queued command만 명시된 policy로 coalesce/rebase한다.
- [ ] claim/lease와 process restart가 foreground/background overlap에 안전하다.
- [ ] active sync 중 새 edit가 늦은 success에 덮이지 않는다.
- [ ] malformed response, server version regression, auth block과 permanent failure를 `synced`로 표시하지 않는다.
- [ ] conflict가 local/base/remote를 보존하고 해결이 새 command를 만든다.
- [ ] attachment staging/orphan/missing file과 이전 schema migration을 검사한다.

## permission·기기 기능·privacy

- [ ] capability availability와 permission state를 별도 축으로 표현한다.
- [ ] permission은 관련 사용자 action에서 요청하고 Settings 복귀 시 다시 읽는다.
- [ ] denied·limited·restricted·revoked·unavailable에 대체 행동이 있다.
- [ ] system picker와 camera를 별도 adapter·lifecycle로 구현했다.
- [ ] picker/camera URI를 app-owned durable file로 전환한다.
- [ ] foreground location adapter에는 timestamp·accuracy·source가 있고, 거절해도 record를 저장한다.
- [ ] data inventory가 trigger·local/remote·retention·삭제·사용자 control을 설명한다.
- [ ] log/evidence에 record·사진·정확한 위치·token이 없다.

## background·notification

- [ ] background task가 실행되지 않아도 foreground resume에서 수렴한다.
- [ ] task는 bounded·idempotent·checkpointed이고 foreground와 같은 worker를 쓴다.
- [ ] Android 13+에서는 channel 생성→permission→token→backend registration 순서를 검토했다.
- [ ] permission, channel, token, registration과 delivery를 구분한다.
- [ ] notification payload를 최신 업무 상태로 사용하지 않는다.
- [ ] duplicate/old notification response가 DB를 다시 읽고 한 번만 navigation한다.
- [ ] 실제 양 플랫폼 기기에서 cold/warm tap과 task 미실행을 기록했다.

## native boundary 읽기

- [ ] 선택한 dependency의 TypeScript call과 runtime validation을 찾았다.
- [ ] package/autolinking/config plugin에서 generated Android/iOS 결과를 추적했다.
- [ ] Kotlin/Java·Swift/Obj-C entry의 type·error·thread·lifecycle·cancel 의미를 읽었다.
- [ ] 양 플랫폼이 같은 application union 또는 명시적 fallback을 반환하는지 설명한다.
- [ ] installed binary에 없는 API를 JS가 호출하는 대표 mismatch를 controlled 환경에서 거부했다.
- [ ] custom module 구현이나 Kotlin·Swift 전체 숙련을 필수 완료로 주장하지 않는다.

## 품질·release

- [ ] pure model, repository, adapter, screen, integration과 device 검사의 책임이 다르다.
- [ ] reference가 통과하고 의도적 skeleton·known-wrong mutant가 거부된다.
- [ ] process kill, old schema upgrade와 permission revoke를 실제로 만든다.
- [ ] release-like build·실제 기기에서 startup/list/image/sync와 보조기술을 검토한다.
- [ ] 플랫폼별 schema v2 manifest pair에서 같은 source·lockfile·profile·app version·runtime 아래 고유 `artifacts[]` ref를 연결했다.
- [ ] Android AAB+APK/Play split, iOS xcarchive+IPA/TestFlight와 실제 install artifact ref를 구분한다.
- [ ] artifact-linked signing `claimed`/사람 검토와 store-delivered bytes `declared`/사람 검토를 자동 trust·delivery 검증으로 표현하지 않는다.
- [ ] remote update 호환성, signing owner/recovery, store metadata와 rollout 중 미실행 항목을 표시한다.
- [ ] 자동 검사 통과를 교육적 완성이나 `stable` 승인으로 표현하지 않는다.

## 작은 실제 프로젝트로 이동하는 판정

1. 기능의 JavaScript·native·OS·backend 경계와 이 브랜치의 비소유 범위를 그릴 수 있는가?
2. 어느 failure 지점에서 process가 사라져도 commit한 사용자 의도가 남는지 설명할 수 있는가?
3. Android와 iOS의 정상·경계·대표 실패를 같은 application meaning으로 검토할 수 있는가?
4. 실제 device와 release candidate identity가 연결된 evidence를 남길 수 있는가?
5. native binary와 JS update의 호환성을 dependency source에서 판정할 수 있는가?
6. 구현·실행하지 않은 platform, device, permission, signing·store 범위를 `not-run`으로 기록하는가?

이 질문에 근거로 답할 수 있으면 기존 Expo/React Native 저장소에서 작은 route·offline·device·build 문제 하나를 골라 수정, 회귀 검사와 preview artifact까지 연결한다. 모바일 backend 운영은 `web-infra`, 네트워크/보안/native 전문 영역은 각 인접 정본 또는 외부 전문 경로에 맡긴다.
