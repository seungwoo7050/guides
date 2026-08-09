# 에디터 도구, 빌드와 콘텐츠 검증

## 문제

게임 코드는 개발자가 작성하지만 게임의 큰 부분은 디자이너·아티스트·애니메이터·오디오·QA가 에디터와 asset pipeline에서 만듭니다. runtime이 견고해도 제작 도구가 느리고 오류를 늦게 발견하면 팀 전체의 전달 속도와 품질이 떨어집니다.

게임 도구의 목적은 편리한 버튼을 추가하는 것이 아니라 다음을 자동화하는 것입니다.

```text
의도한 data 입력
→ schema와 제약 검증
→ preview와 빠른 feedback
→ deterministic transform/build
→ diff·review 가능한 산출물
→ runtime-compatible artifact
→ 오류 위치와 수정 방법
```

## 핵심 상태

### 제작 데이터 수명

```text
Draft
→ LocallyValid
→ Reviewed
→ Integrated
→ Cooked
→ Packaged
→ Released
→ Deprecated/Migrated
```

branch에 들어갔다는 사실과 target build에 들어간 사실은 다릅니다.

### 도구 종류

- editor extension: custom inspector, scene tool, graph editor
- content validator: schema, reference, naming, budget, platform rule
- importer/exporter: DCC/source ↔ engine asset
- batch processor: resize, compress, cook, generate metadata
- build orchestrator: code+content version을 artifact로 묶음
- test launcher: representative scene와 multi-instance 실행
- report/visualization: dependency, memory, performance, compatibility

### 정본과 generated file

각 파일을 다음으로 분류합니다.

- human-authored source
- generated but tracked
- generated and reproducible cache
- machine/local state
- release artifact

generated file을 사람이 수정하면 다음 generation에서 사라집니다. source와 output owner를 README와 tool message에 드러냅니다.

### binary asset와 collaboration

binary asset은 line merge가 어렵습니다. 다음 정책이 필요할 수 있습니다.

- file locking 또는 ownership
- scene/prefab 분할
- text serialization 가능한 metadata
- stable id와 deterministic ordering
- generated preview/diff report
- large file storage
- rename/move redirect

## 설계 계약

### validator는 오류 위치와 계약을 반환합니다

나쁜 오류:

```text
Invalid asset.
```

좋은 오류:

```text
characters/hero.asset: ability[2].icon
unknown asset id 'ui.icon.hero_dash'
rule: all release abilities require an existing menu-safe icon
suggestion: add the icon to ui-core or mark the ability development-only
```

validator id, severity, asset id, field path와 remediation을 포함합니다.

### validator와 fixer를 분리합니다

자동 수정이 가능한 경우에도 먼저 변경 계획을 출력하고 diff를 검토할 수 있게 합니다. destructive rename, reimport와 mass migration은 dry-run, backup/branch와 rollback을 가집니다.

### build input을 versioned manifest로 고정합니다

```text
source commit
engine/runtime version
content manifest
toolchain/importer version
platform profile
feature flags
localization set
signing/release channel
```

같은 이름의 “latest content”를 build 중 동적으로 읽지 않습니다.

### incremental build의 invalidation을 검증합니다

cache key가 input을 빠뜨리면 stale artifact가 성공으로 보입니다. tool version, import setting, dependency와 platform profile을 key에 포함합니다. clean build와 incremental build 결과를 주기적으로 비교합니다.

### headless와 interactive path를 맞춥니다

에디터에서만 가능한 검사를 CI가 재현할 수 없으면 release 전에 누락됩니다. 가능한 validator와 import/cook test는 command-line/headless로 실행합니다. UI tool은 동일 core logic을 호출합니다.

### tool UX도 제품 계약입니다

- 진행률과 현재 asset
- 취소 가능 여부
- 실패 뒤 partial output
- 로그와 report 위치
- safe retry
- undo/rollback
- 대형 작업의 memory/time budget

도구가 hang처럼 보이면 사용자는 강제 종료해 asset을 손상시킬 수 있습니다.

## 대표 실패

### validation이 build 마지막에만 실행됩니다

오류를 만든 시점과 발견 시점이 멀어집니다. local save/import, pre-submit, CI와 release gate에 비용별 validator를 배치합니다.

### editor code와 build code가 다른 schema를 해석합니다

preview는 성공하지만 runtime load가 실패합니다. shared schema/version과 compatibility test를 둡니다.

### asset processor가 nondeterministic output을 만듭니다

file order, locale, timestamp와 random id가 output을 바꿔 cache miss와 noisy diff가 생깁니다.

### 한 giant scene/prefab에 여러 직무가 동시에 작업합니다

merge conflict와 implicit dependency가 커집니다. ownership unit과 composition boundary를 재설계합니다.

### warning이 너무 많아 무시됩니다

actionability 없는 warning과 known debt를 구분하고 budget/waiver에 owner·expiry를 둡니다.

### local machine path와 tool installation을 암묵적으로 기대합니다

새 개발자와 CI에서 build가 실패합니다. environment contract와 version probe를 둡니다.

## 관찰과 검증

### tool telemetry

개인 성과 감시에 사용하지 않고 workflow 개선을 위해 집계합니다.

- validation failures by rule
- time to first error
- import/cook duration distribution
- cache hit/miss
- cancellation/failure rate
- clean vs incremental output hash
- asset churn and dependency fan-out

### meta-test

검사기가 실제로 잘못된 content를 거부하는지 확인합니다.

1. valid fixture가 통과합니다.
2. reference를 삭제하면 missing-reference rule이 실패합니다.
3. duplicate id를 넣으면 uniqueness rule이 실패합니다.
4. development asset을 release group에 넣으면 실패합니다.
5. validator를 비활성화하면 meta-test가 실패합니다.

### build reproducibility

완전한 bit reproducibility가 어려워도 최소한 다음을 비교합니다.

- manifest와 input hash
- included asset set
- code/content version
- platform settings
- known nondeterministic field를 제외한 semantic output

## 실습 연결

[asset loading 실습](../exercises/04-asset-loading-plan/README.md)은 manifest와 validator 요구사항을 포함합니다. [release readiness 실습](../exercises/08-release-readiness/README.md)에서는 build/content gate를 검토합니다.

## 기존 브랜치와 경계

- 일반 Git collaboration은 `git`이 소유합니다.
- CI/CD, artifact provenance와 deployment는 `web-infra`·`platform-engineering`이 소유합니다.
- 현재 문서는 game editor workflow, content schema, importer/cook, binary asset collaboration과 target build input 계약을 소유합니다.

## 완료 기준

- authored source, generated cache와 release artifact의 owner를 구분합니다.
- actionable content validator와 safe fixer를 설계합니다.
- build input을 versioned manifest로 고정하고 incremental invalidation을 검증합니다.
- editor와 headless path가 같은 schema와 core validation을 사용하게 합니다.
