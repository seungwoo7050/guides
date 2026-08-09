# 게임 개발 시스템 가이드

게임을 단순히 화면에 무언가를 움직이는 프로그램으로 다루지 않고, **시간에 따라 상태가 변하고 입력·시뮬레이션·표현·자산·저장·네트워크·플랫폼 제약이 한 프레임 안에서 만나는 시스템**으로 다루는 가이드입니다.

```text
플레이어 의도
→ 입력과 명령
→ 게임 규칙과 시뮬레이션
→ 월드·엔티티 상태 변화
→ 애니메이션·오디오·VFX·UI 표현
→ 저장·리플레이·네트워크·텔레메트리
→ 다음 프레임과 다음 빌드
```

이 브랜치의 목적은 Unity, Unreal Engine, Godot 중 하나의 메뉴와 API를 외우게 하는 것이 아닙니다. 어떤 엔진과 프로젝트에 들어가더라도 다음 질문을 할 수 있게 만드는 것이 목적입니다.

- 이 시스템에서 게임의 정본 상태는 무엇입니까?
- 한 프레임과 한 simulation step은 언제 시작하고 끝납니까?
- 입력은 장치 신호에서 게임 명령으로 어디에서 변환됩니까?
- 객체·장면·자산은 누가 만들고 언제 파괴하거나 unload합니까?
- 게임 규칙과 화면 표현은 어느 경계에서 분리됩니까?
- save, replay, network replication은 같은 상태를 어떤 서로 다른 목적으로 직렬화합니까?
- frame time, memory, loading, bandwidth 예산을 어떤 실제 기기에서 검증합니까?
- 디자이너·아티스트·QA·서버·도구 개발자와 어떤 데이터 계약으로 협업합니까?

처음에는 [게임 개발 로드맵](docs/00-roadmap.md)을 읽으세요. 선행 가이드, 직무별 선택 경로, 문서 순서, 실습과 Capstone 완료 기준을 한곳에서 확인할 수 있습니다.

`main` 카탈로그에서 이 가이드는 **분야 진입(`field-entry`)** 브랜치입니다. 한 문장 계약은 다음과 같습니다.

> 게임 루프·시간·입력·장면·엔티티·자산·물리·애니메이션·오디오·네트워크 경계를 연결해 게임 코드베이스에 진입한다.

## 정본 종료 능력

이 가이드가 게임 개발 전문가나 특정 엔진 전문가를 한 번에 완성하지는 않습니다. 완료 판단은 `main`이 선언한 다음 세 능력으로 고정합니다.

1. 기존 엔진 프로젝트의 update·render·asset·tool 경계를 복원한다.
2. 입력부터 상태·표현·저장까지 이어지는 작은 게임플레이 기능을 구현한다.
3. frame·resource·simulation 실패를 재현하고 profiling 근거로 수정한다.

아래 항목은 별도의 종료 능력을 추가하는 목록이 아니라, 위 세 능력을 판단할 때 찾을 세부 근거입니다.

- 처음 보는 게임 저장소에서 부팅, 메뉴, 월드 진입, 플레이, 종료까지 runtime 경계를 추적합니다.
- variable frame과 fixed simulation을 구분하고 긴 frame, pause, slow motion, catch-up 실패를 설명합니다.
- raw input을 재매핑 가능한 action과 결정적인 gameplay command로 변환합니다.
- scene, entity, component, subsystem의 수명과 cross-reference를 조사합니다.
- gameplay rule, progression, economy, presentation state의 owner를 구분합니다.
- asset dependency, import, cooking, asynchronous loading, unload와 memory resident 상태를 설계합니다.
- collision·physics·movement·animation 사이의 정본과 적용 순서를 설명합니다.
- save schema를 versioning하고 replay divergence를 최소 입력으로 재현합니다.
- client prediction과 server authority를 구분하고 latency·loss·reordering에서 사용자 경험과 보안을 검토합니다.
- 자동 테스트, deterministic fixture, record/replay, telemetry와 profiler로 버그와 성능 문제를 재현합니다.
- target hardware에서 frame time·memory·loading·network 예산을 측정하고 품질 단계별 scalability를 결정합니다.
- 하나의 vertical slice를 기능, 실패, 접근성, 빌드와 운영 근거까지 연결합니다.

## 이 브랜치가 소유하는 범위

`main`의 `owns`를 그대로 구현 범위로 사용합니다.

1. 고정·가변 시간 단계와 game loop
2. 입력·카메라·장면·엔티티·컴포넌트의 상태 경계
3. 자산 로딩·직렬화·resource lifetime과 editor workflow
4. 물리·애니메이션·오디오·렌더링 하위 시스템의 게임 계층 통합
5. 게임플레이 기능의 상태 전이·저장·재현·테스트
6. frame budget·profiling·client/server authoritative 경계의 게임 맥락

게임 AI·navigation, 접근성·release, telemetry와 팀 변경 장은 별도의 소유 범위를 추가하지 않습니다. 위 여섯 범위가 agent, target platform, 협업과 실패 상황에서도 유지되는지 확인하는 **통합 사례와 지원 근거**입니다.

### 브랜치 관계

선형 직무 경로와 브랜치 자체의 직접 필수 조건을 구분합니다. 이 브랜치의 `requires`는 비어 있으므로 다른 가이드 완료를 시작 조건으로 강제하지 않습니다.

| 관계 | 브랜치 |
|---|---|
| `requires` | 없음 |
| `recommends` | [`algorithms`](https://github.com/seungwoo7050/guides/tree/algorithms), [`cpp`](https://github.com/seungwoo7050/guides/tree/cpp), [`operating-systems`](https://github.com/seungwoo7050/guides/tree/operating-systems), [`computer-networks`](https://github.com/seungwoo7050/guides/tree/computer-networks) |
| `connects` | [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity), [`platform-engineering`](https://github.com/seungwoo7050/guides/tree/platform-engineering) |
| `continues_to` | [`computer-graphics`](https://github.com/seungwoo7050/guides/tree/computer-graphics), [`distributed-services`](https://github.com/seungwoo7050/guides/tree/distributed-services), [`machine-learning`](https://github.com/seungwoo7050/guides/tree/machine-learning), [`cybersecurity`](https://github.com/seungwoo7050/guides/tree/cybersecurity) |

트랙별 선형 경로에는 `computer-architecture`, `web-app`, `database-systems`, `web-infra` 같은 추가 기반이 포함될 수 있습니다. 이는 해당 직무의 권장 순서이지 `game-development`의 직접 필수 관계를 바꾸지 않습니다. 일곱 경로의 정확한 순서는 [직무별 진입 지도](reference/role-entry-map.md)에 있습니다.

### 이 브랜치가 소유하지 않는 범위

`main`의 `excludes`는 다음 네 항목입니다.

1. GPU 렌더링 파이프라인과 shader 내부구조
2. 운영체제·네트워크 프로토콜·분산 합의의 일반 원리
3. 특정 상용 엔진 API 전체
4. 게임 기획·아트·사운드 제작 직무 교육

이 브랜치는 위 원리를 다시 가르치지 않습니다. **게임이라는 실행 환경에서 해당 기반들이 언제 충돌하고 어떤 계약이 필요한지**에 집중합니다.

## 학습 구조

### Part I. 게임 runtime과 상태

1. [게임 제품과 runtime 계약](docs/01-game-product-and-runtime-contract.md)
2. [게임 루프, 시간과 프레임](docs/02-game-loop-time-and-frames.md)
3. [입력, 명령, 카메라와 게임 UI](docs/03-input-command-camera-and-ui.md)
4. [월드, 장면, 엔티티와 컴포넌트 수명](docs/04-world-scene-entity-component-lifecycles.md)
5. [게임 규칙, 진행 상태와 data-driven 설계](docs/05-gameplay-rules-progression-and-data.md)

### Part II. 콘텐츠와 시뮬레이션

6. [자산 import, cooking, loading과 memory residence](docs/06-assets-import-cooking-loading-and-memory.md)
7. [충돌, 물리, 이동과 좌표 계약](docs/07-collision-physics-movement-and-space.md)
8. [애니메이션, 오디오, VFX와 표현 경계](docs/08-animation-audio-vfx-and-presentation.md)
9. [저장, migration, replay와 determinism](docs/09-save-migration-replay-and-determinism.md)
10. [게임 AI, navigation과 behavior 통합](docs/10-game-ai-navigation-and-behavior.md)

### Part III. 온라인·품질·생산

11. [네트워크 권위, replication과 latency](docs/11-network-authority-replication-and-latency.md)
12. [에디터 도구, 빌드와 콘텐츠 검증](docs/12-tools-editor-builds-and-content-validation.md)
13. [테스트, 디버깅, telemetry와 재현](docs/13-testing-debugging-telemetry-and-reproduction.md)
14. [성능 예산, profiling과 scalability](docs/14-performance-budgets-profiling-and-scalability.md)
15. [플랫폼 입력, 접근성, 저장 수명과 release](docs/15-platform-accessibility-lifecycle-and-release.md)
16. [게임 팀 경계와 안전한 변경](docs/16-game-team-interfaces-and-change-management.md)
17. [Vertical Slice Capstone](docs/17-capstone.md)
18. [엔진 교차표와 공식 자료 지도](docs/90-engine-and-source-map.md)

## 단계 실습

실습은 특정 엔진 프로젝트를 요구하지 않습니다. 제공된 system brief, trace, manifest와 profile을 분석해 **상태·수명·실패·검증 산출물**을 작성합니다.

| 실습 | 핵심 결과물 |
|---|---|
| [01 시간 단계 분석](exercises/01-time-step-analysis/README.md) | variable frame에서 fixed step, catch-up, pause와 overload 판정 |
| [02 입력과 명령](exercises/02-input-command-contract/README.md) | device event에서 action·command·UI focus로 이어지는 계약 |
| [03 월드와 객체 수명](exercises/03-world-lifecycle-review/README.md) | create·activate·stream·destroy와 cross-reference 위험 분석 |
| [04 자산과 loading](exercises/04-asset-loading-plan/README.md) | dependency·bundle·preload·unload·memory budget 계획 |
| [05 save와 replay](exercises/05-save-and-replay-migration/README.md) | schema migration, unknown field, replay divergence 조사 |
| [06 네트워크 권위](exercises/06-authority-and-latency/README.md) | client intent, server validation, prediction·correction 계약 |
| [07 성능 예산](exercises/07-performance-budget-review/README.md) | target device profile에서 CPU·GPU·memory·loading 병목 판정 |
| [08 릴리스 검토](exercises/08-release-readiness/README.md) | 입력·접근성·save·crash·telemetry·content validation release gate |

정답 구현을 복사하는 구조는 제공하지 않습니다. 각 실습은 초기 자료, 템플릿, 대표 오답과 사람 검토 질문을 제공하며 자동 검사는 제출 문장의 정답을 판정하지 않습니다.

## 실행 예제

[`examples/fixed-step-replay`](examples/fixed-step-replay/README.md)는 Python 표준 라이브러리만으로 작은 결정적 simulation을 실행하고 같은 input trace에서 같은 state hash가 나오는지 확인합니다. 이 예제는 게임 엔진을 대신하지 않고 다음 계약만 관찰합니다.

```text
render frame duration
→ accumulator
→ bounded fixed step
→ command consumption
→ canonical state serialization
→ replay hash
```

## Capstone

[`projects/relay-arena-vertical-slice`](projects/relay-arena-vertical-slice/README.md)는 1~2명이 구현할 수 있는 작은 arena game을 가정합니다.

필수 profile은 엔진 구현이 아니라 다음 산출물을 완성합니다.

```text
runtime·state ownership map
→ fixed-step·input command trace
→ scene/entity lifecycle
→ asset manifest와 loading plan
→ save/replay schema
→ authority·latency model
→ test·telemetry·performance budget
→ release decision
```

Profile A는 설계·검토 근거를 완성합니다. 두 번째 종료 능력까지 입증하려면 Unity, Unreal Engine, Godot, 자체 framework의 Profile B 또는 기존 엔진 프로젝트의 동등한 작은 기능 변경 근거가 추가로 필요합니다. 엔진별 API가 아니라 동일한 상태·실패·검증 계약을 만족하는지가 평가 기준이며, network Profile C는 선택 심화입니다.

## 준비와 검증

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 Python 버전과 저장소 구조를 확인하고 일회성 준비 marker를 만듭니다. 시스템 패키지를 설치하거나 사용자 파일을 수정하지 않습니다.

`verify.sh`는 다음을 검사합니다.

- 필수 문서·실습·Capstone 구조
- Markdown 상대 링크
- JSON fixture의 schema와 교차 참조
- 문서 공통 절과 ownership 경계
- fixed-step replay 예제의 deterministic state hash
- 검사기 자체가 깨진 fixture를 실제로 거부하는 meta-check
- 검증 전후 원본 source snapshot 불변성

빠른 개발 검사는 다음과 같습니다.

```sh
make check
make example
make fixtures
```

## 학습 방식과 한계

- 문서와 공통 fixture는 엔진 독립적이며, 선택한 엔진·언어의 설치와 API는 해당 공식 자료에서 확인합니다.
- Capstone은 범용 게임 엔진이나 상용 수준 게임의 완성을 요구하지 않습니다.
- “60 FPS”, “deterministic”, “server authoritative” 같은 표현은 측정 환경·보장 범위·실패 조건과 함께만 근거로 사용합니다.
- 자동 검사는 구조와 공개 행동을 확인하지만 설명의 정확성이나 교육적 완성을 대신 판정하지 않습니다.

이 가이드의 종료점은 특정 엔진의 인증서가 아니라, 게임 프로젝트의 한 기능을 **시간·상태·자산·표현·저장·네트워크·성능·릴리스 계약**으로 분해하고 실제 코드베이스에서 작은 변경을 완성할 수 있는 상태입니다.
