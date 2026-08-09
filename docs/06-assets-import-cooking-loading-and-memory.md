# 자산 import, cooking, loading과 memory residence

## 문제

게임의 texture, mesh, animation, audio, level, scriptable data와 shader는 source repository에 존재한다고 바로 runtime에서 사용할 수 있는 것이 아닙니다. 제작 도구의 source format이 import되고, platform별로 변환·압축·cooking·chunking된 뒤 build manifest에 들어가고, runtime에서 발견·load·instantiate·resident·unload되는 여러 단계를 거칩니다.

```text
source asset
→ import settings
→ derived data
→ validated authored asset
→ dependency graph
→ cooked platform artifact
→ package/chunk/depot
→ runtime discovery
→ asynchronous load
→ object/resource creation
→ memory resident
→ release/unload
```

이 단계를 구분하지 않으면 editor에서는 보이지만 build에 빠지거나, 작은 object reference 하나가 거대한 content bundle을 memory에 올리거나, async completion 뒤 owner가 사라지는 문제가 발생합니다.

## 핵심 상태

### source, authored asset와 runtime resource

| 상태 | 예 | 정본 |
|---|---|---|
| source | PSD, Blender file, WAV, source JSON | DCC/source control |
| imported asset | engine-native texture, mesh, clip | import pipeline |
| derived data | compressed mip, platform shader, cache | 재생성 가능 cache |
| cooked artifact | target platform용 package | build pipeline |
| runtime resource | GPU texture, audio buffer, collision mesh | runtime owner |
| instance | world의 material/mesh component | entity/world |

source file과 runtime instance를 같은 id로 사용하지 않습니다.

### dependency 종류

- hard dependency: parent가 load되면 child도 필요
- soft dependency: identity만 알고 조건부 load
- management dependency: bundle·label·chunk 정책상 함께 관리
- build-only dependency: import/cook 과정에서만 필요
- runtime-generated dependency: downloadable content나 user-generated content에서 발견

### loading state

```text
Unrequested
→ Queued
→ Reading
→ Deserializing
→ CreatingResources
→ Ready
→ Releasing
→ Unloaded
```

실제 engine callback 하나가 `Ready`의 모든 조건을 보장하지 않을 수 있습니다. CPU object, GPU upload, shader compilation과 first use hitch를 구분합니다.

### memory budget

- disk/package size
- compressed download size
- CPU resident memory
- GPU resident memory
- transient staging/upload memory
- duplicated editor/read-write copy
- streaming pool
- peak during transition

“asset 크기 10MB”는 어떤 상태의 크기인지 명시하지 않으면 쓸 수 없는 숫자입니다.

## 설계 계약

### stable asset identity를 둡니다

path나 display name만으로 public identity를 만들지 않습니다. rename과 move 뒤에도 resolve할 stable id, redirect 또는 migration이 필요합니다.

```json
{
  "asset_id": "character.hero.base",
  "type": "character_definition",
  "content_version": 12,
  "dependencies": ["mesh.hero.v4", "animset.hero.base"],
  "load_group": "arena-core"
}
```

### dependency graph를 build 전에 검증합니다

- missing reference
- forbidden layer dependency
- cycle
- duplicate stable id
- development-only asset in release
- oversized bundle
- cross-chunk hard reference
- unsupported format·compression
- platform variant 누락

runtime에서 처음 발견할 수밖에 없는 오류를 줄입니다.

### load request에 owner와 cancellation을 붙입니다

```text
request id
+ requesting world/entity/system
+ asset id and version
+ priority/deadline
+ cancellation token
+ readiness level
+ memory class
```

owner가 unload되면 request를 취소하거나 completion을 무시합니다. completion callback이 strong reference로 owner와 asset을 영구 유지하지 않게 합니다.

### loading screen과 gameplay readiness를 분리합니다

화면 전환이 끝났다고 모든 gameplay asset이 준비된 것은 아닙니다. 다음 readiness를 구분할 수 있습니다.

- boot-critical
- menu-visible
- world-interactive
- cosmetic-ready
- background-prefetched

cosmetic miss가 gameplay block으로 이어지지 않게 fallback을 정합니다.

### unload는 reference graph와 fence를 확인합니다

resource release에는 다음이 필요할 수 있습니다.

- gameplay reference 제거
- render/audio command drain
- outstanding job completion 또는 cancel
- GPU fence
- cache policy
- pool 반환

`UnloadScene()` 호출 직후 memory가 줄어야 한다고 가정하지 않습니다.

### content와 runtime compatibility를 기록합니다

build id, content manifest id, save schema, network protocol과 rule version의 허용 조합을 정합니다. downloadable content가 code보다 새로울 수 있는지, older client가 unknown field를 어떻게 처리하는지 결정합니다.

## 대표 실패

### hard reference가 loading 정책을 무력화합니다

menu icon이 full character prefab을 hard reference해 menu에서 모든 mesh와 animation이 load됩니다. thumbnail/metadata와 runtime definition을 분리합니다.

### editor cache를 release build 성능으로 오인합니다

warm cache와 loose asset 환경은 packaged build의 first load, decompression과 shader preparation을 숨깁니다.

### async load 완료 뒤 world가 바뀝니다

old request가 새 world의 slot을 덮거나 destroyed entity에 component를 붙입니다. request generation과 owner lifetime을 검증합니다.

### unload 뒤에도 static cache·event·material instance가 reference를 유지합니다

memory leak이 engine bug가 아니라 project reference chain일 수 있습니다. reference report와 owner trace가 필요합니다.

### asset version을 save에 path로 저장합니다

rename·DLC 제거·content rollback에서 save가 깨집니다. stable id, fallback과 migration을 둡니다.

### peak memory를 보지 않습니다

old world와 new world가 동시에 resident하고 decompression buffer까지 필요한 transition peak가 steady-state budget을 넘습니다.

## 관찰과 검증

### manifest와 runtime event

```json
{
  "event": "asset_ready",
  "request_id": "req-311",
  "asset_id": "arena.map.01",
  "content_manifest": "content-2026.08.1",
  "owner": "world-load:arena-01",
  "cpu_bytes": 18700000,
  "gpu_bytes": 94200000,
  "duration_ms": 780,
  "source": "local-chunk-2"
}
```

### 필수 검사

- clean cache packaged build에서 boot·world load를 측정합니다.
- manifest에 없는 reference와 forbidden dependency를 build 전에 거부합니다.
- load request 취소 뒤 completion이 상태를 변경하지 않습니다.
- world 반복 진입 뒤 resident asset과 memory가 기준선으로 돌아옵니다.
- low-memory event에서 quality tier 또는 cache eviction이 계약대로 동작합니다.
- content rollback과 missing optional pack에서 fallback이 동작합니다.
- transition peak를 target device에서 측정합니다.

### budget table

| group | disk | download | CPU resident | GPU resident | peak | load deadline | fallback |
|---|---:|---:|---:|---:|---:|---:|---|
| arena-core | ... | ... | ... | ... | ... | before control | block |
| hero-cosmetic | ... | ... | ... | ... | ... | background | default skin |

## 실습 연결

[asset loading 계획 실습](../exercises/04-asset-loading-plan/README.md)에서 dependency manifest와 memory profile을 분석해 load group, preload, cancellation과 unload 조건을 작성합니다.

## 기존 브랜치와 경계

- filesystem, page cache와 I/O 원리는 `operating-systems`가 소유합니다.
- GPU resource 내부와 shader pipeline은 `computer-graphics`가 소유합니다.
- release artifact, registry와 provenance는 `web-infra`·`platform-engineering`이 소유합니다.
- 현재 문서는 game content의 import→cook→resident 수명과 runtime owner를 소유합니다.

## 완료 기준

- source, imported, cooked, runtime resource와 instance를 구분합니다.
- hard/soft/management dependency와 stable asset id를 설계합니다.
- async load의 owner·cancel·readiness·unload 계약을 작성합니다.
- disk·CPU·GPU·transient·transition peak를 target build에서 검증합니다.
