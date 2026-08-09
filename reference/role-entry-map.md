# 게임 개발 직무별 진입 지도

`game-development`는 직접 필수 브랜치가 없는 `field-entry`이며, 게임 제품의 공통 runtime·상태·콘텐츠·품질 계약을 소유한다. 아래 일곱 항목은 `main`의 트랙 카탈로그와 `linear_paths`를 그대로 옮긴 권장 직무 경로다. 선형 경로에 포함된 브랜치가 모두 `game-development`의 직접 필수라는 뜻은 아니다.

## Gameplay / Client (`game-client-gameplay`)

```text
beginner: git → c → cpp → algorithms → game-development
experienced: git → cpp → algorithms → game-development
```

이 트랙에서 `game-development`는 핵심(`required`)이다. 우선 문서: 01~09, 13~16. 이후 실제 엔진에서 player feature, state transition, save/replay와 content integration에 기여한다.

## Engine / Core Systems (`game-engine-core`)

```text
git → c → cpp → algorithms → computer-architecture → operating-systems → game-development
```

이 트랙에서 `game-development`는 핵심(`required`)이다. 우선 문서: 01~07, 09, 12~14. memory, streaming, job, lifecycle와 platform abstraction을 실제 subsystem에서 확장한다.

## Rendering / Graphics (`game-rendering`)

```text
git → c → cpp → algorithms → computer-architecture → game-development → computer-graphics
```

이 트랙에서 `game-development`는 핵심(`required`)이다. 현재 브랜치는 renderer가 소비하는 world/presentation/resource/frame 계약을 제공한다. rasterization, shader와 GPU synchronization은 `computer-graphics`가 소유한다.

## Game Server (`game-server`)

```text
git → web-app → java → backend-spring-boot → database-systems
→ game-development → computer-networks → distributed-services → web-infra
```

이 트랙에서 `game-development`는 권장(`recommended`)이지만 선형 경로에는 게임 상태 문맥을 위해 포함된다. 우선 문서: 05, 09, 11, 13, 16. authoritative session과 game rule을 서비스 상태·DB·운영으로 확장한다.

## Tools / Build / Platform (`game-tools-platform`)

```text
git → python → unix-systems → game-development
→ web-infra → platform-engineering
```

이 트랙에서 `game-development`는 권장(`recommended`)이다. 우선 문서: 04, 06, 09, 12~16. editor workflow, asset pipeline, content validator, build/release와 개발자 self-service를 확장한다.

## Data / Machine Learning (`game-data-ml`)

```text
git → python → algorithms → game-development → database-systems
→ data-engineering → machine-learning
```

이 트랙에서 `game-development`는 권장(`recommended`)이다. 우선 문서: 05, 09, 13, 16. gameplay event semantics를 analytics, feature, model evaluation과 운영 의사결정으로 확장한다.

## Security / Anti-cheat (`game-security-anticheat`)

```text
git → c → cpp → algorithms → game-development
→ computer-architecture → operating-systems → unix-systems → computer-networks → cybersecurity
```

이 트랙에서 `game-development`는 핵심(`required`)이다. 우선 문서: 03, 05, 09, 11~13, 15~16. client trust, process/protocol abuse, server validation, telemetry와 대응을 별도 보안 프로젝트에서 깊게 다룬다.

## 지원 역할: QA Automation / Technical QA

QA Automation / Technical QA는 현재 `main`에 독립 트랙으로 등재된 여덟 번째 경로가 아니다. 위 일곱 트랙의 구현·검증을 지원하는 역할 관점으로 이 가이드를 사용할 수 있다. 우선 문서: 전체 runtime 계약과 특히 09, 12~15. deterministic fixture, record/replay, content validation, target-device matrix와 failure injection을 실제 저장소에 적용한다.
