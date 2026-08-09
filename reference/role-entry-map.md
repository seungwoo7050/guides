# 게임 개발 직무별 진입 지도

`game-development`는 게임 제품의 공통 runtime·상태·콘텐츠·품질 계약을 소유한다. 각 직무의 전문성은 다른 브랜치와 실제 프로젝트에서 확장한다.

## Gameplay / Client

```text
git → c 또는 기존 프로그래밍 경험 → cpp → algorithms → game-development
```

우선 문서: 01~09, 13~16. 이후 실제 엔진에서 player feature, state transition, save/replay와 content integration에 기여한다.

## Engine / Core Systems

```text
git → c → cpp → algorithms → computer-architecture → operating-systems → game-development
```

우선 문서: 01~07, 09, 12~14. memory, streaming, job, lifecycle와 platform abstraction을 실제 subsystem에서 확장한다.

## Rendering / Graphics

```text
git → c → cpp → algorithms → computer-architecture → game-development → computer-graphics
```

현재 브랜치는 renderer가 소비하는 world/presentation/resource/frame 계약을 제공한다. rasterization, shader와 GPU synchronization은 `computer-graphics`가 소유한다.

## Game Server

```text
git → web-app → java → backend-spring-boot → database-systems
→ algorithms → game-development → computer-networks → distributed-services → web-infra
```

우선 문서: 05, 09, 11, 13, 16. authoritative session과 game rule을 서비스 상태·DB·운영으로 확장한다.

## Tools / Build / Platform

```text
git → python → unix-systems → algorithms → game-development
→ web-infra → platform-engineering
```

우선 문서: 04, 06, 09, 12~16. editor workflow, asset pipeline, content validator, build/release와 개발자 self-service를 확장한다.

## Data / Machine Learning

```text
git → python → algorithms → game-development → database-systems
→ data-engineering → machine-learning
```

우선 문서: 05, 09, 13, 16. gameplay event semantics를 analytics, feature, model evaluation과 운영 의사결정으로 확장한다.

## Security / Anti-cheat

```text
git → c → cpp → algorithms → game-development
→ computer-architecture → operating-systems → computer-networks → cybersecurity
```

우선 문서: 03, 05, 09, 11~13, 15~16. client trust, process/protocol abuse, server validation, telemetry와 대응을 별도 보안 프로젝트에서 깊게 다룬다.

## QA Automation / Technical QA

```text
git → python 또는 cpp → algorithms → game-development
```

우선 문서: 전체 runtime 계약과 특히 09, 12~15. deterministic fixture, record/replay, content validation, target-device matrix와 failure injection을 실제 저장소에 적용한다.
