# 자산 loading 계획 예시 해설

이 파일은 유일한 문장 정답이 아니라 fixture에서 반드시 재현돼야 하는 계산과 판단의 한 예다. 입력에 timing, transient allocation과 실제 release fence 측정값이 없으므로 그 값은 추측하지 않는다.

## identity와 pipeline

```text
authoring source
→ importer가 만든 platform artifact
→ manifest의 stable logical id
→ target별 cooked package/load group
→ request id + owner generation에 묶인 runtime handle
→ CPU/GPU/audio resident resource
```

- save/replay/network에는 `scene.arena.core`, `cosmetic.player.gold` 같은 stable id와 `arena-content@17`을 기록한다.
- source path, bundle offset와 runtime pointer는 persistent identity가 아니다.
- request 완료는 resource가 resident하다는 뜻이지 요청 owner가 아직 유효하다는 뜻은 아니다.

## load graph와 gate

Transitive closure와 추가 resident 합계는 다음과 같다.

| 집합 | 포함 asset | CPU MiB | GPU MiB |
|---|---|---:|---:|
| scene closure | `scene.arena.core`, `mesh.arena.floor`, `material.arena.floor`, `texture.arena.floor`, `rules.arena.default` | 13 | 87 |
| player closure | `player.base`, `anim.player.base`, `audio.player.core` | 31 | 14 |
| control-ready union | scene closure + player closure | 44 | 101 |
| agent-ready union | control-ready + `nav.arena` | 64 | 101 |
| cosmetic-only addition | `music.arena`, `cosmetic.player.gold`, `vfx.gold.trail` | 78 | 76 |
| full cold-entry union | manifest의 12개 asset 전부 | 142 | 177 |

- **control-ready:** scene closure와 player closure가 성공하고 rule data가 검증돼야 한다. `rules.arena.default`는 scene closure에 이미 포함되므로 중복 합산하지 않는다.
- **agent-ready:** control-ready 뒤 `nav.arena`가 generation이 같은 world에 연결됐을 때 연다. 그 전 agent는 idle fallback이다.
- **cosmetic-ready:** music과 gold cosmetic은 control을 막지 않는다. 누락되면 default material/VFX 없음/무음 또는 기본 cue로 저하한다.
- **background/preload:** desktop에서는 cosmetic을 control-ready 이후 가져온다. handheld에서는 예산을 만족하는 별도 quality-tier asset이 manifest에 추가되기 전에는 optional group을 요청하지 않는다.

## scenario별 계획

| scenario | critical path | defer/skip | peak transient | cancellation cleanup | player-visible result |
|---|---|---|---|---|---|
| cold-entry | scene closure → player closure → control-ready | nav, music, cosmetic | fixture에 측정값 없음 | 해당 없음 | desktop은 먼저 조작 가능, 나머지는 늦게 준비 |
| cancel-at-40ms | 완료된 critical request까지만 추적 | 모든 미완료 request | fixture에 측정값 없음 | cancel flag → owner generation invalidate → late completion discard → GPU/audio release fence 뒤 해제 | frontend로 복귀; arena object가 나타나지 않음 |
| low-memory-entry | control-ready 후보 44/101 MiB | nav, music, cosmetic | fixture에 측정값 없음 | 미사용 request를 취소하고 reference chain을 해제 | 현재 handheld GPU 합계 155 MiB가 128 MiB 예산을 넘으므로 entry 차단; lower-tier critical asset 필요 |
| missing-cosmetic | scene/player/rules | missing cosmetic과 전용 `vfx.gold.trail`; music도 budget에 따라 지연 | fixture에 측정값 없음 | optional failure를 request 종료로 기록 | gameplay는 default presentation으로 계속되지만 handheld resident budget 문제는 별도로 남음 |

desktop full set은 baseline 포함 CPU `190 + 142 = 332 MiB`, GPU `70 + 177 = 247 MiB`로 resident 예산 `512/256 MiB` 안이다. GPU headroom이 9 MiB뿐이고 transient/p95가 없으므로 conditional pass다.

handheld full set은 CPU `120 + 142 = 262 MiB`, GPU `54 + 177 = 231 MiB`로 `180/128 MiB`를 모두 초과한다. optional을 모두 빼도 control-ready GPU는 `54 + 101 = 155 MiB`이므로 “cosmetic만 지연하면 통과”라고 결론내리면 안 된다.

## async completion 계약

- request identity: `(manifest_version, asset_id, request_id)`.
- owner identity: `(arena_session_id, world_generation)`을 completion과 함께 비교한다.
- cancel: 새 attach를 막고 outstanding child request에 취소를 전파한다. 취소 API 반환만으로 GPU/audio 해제를 주장하지 않는다.
- stale completion: generation 불일치면 world에 attach하지 않고 handle을 release queue로 보낸다.
- release: renderer/audio가 사용을 끝냈다는 fence/acknowledgement 뒤 resident counter가 기준선으로 돌아왔는지 측정한다.

## content compatibility

- stable id rename/removal은 alias 또는 명시적 fallback 표가 있어야 하며 path rename으로 암묵 처리하지 않는다.
- save/replay는 `arena-content@17`과 stable asset id를 함께 기록한다.
- network join은 gameplay-critical manifest/rule 호환성을 먼저 검사하고 cosmetic 차이는 허용 목록으로 분리한다.
- manifest에 없는 lower-tier critical asset은 존재한다고 가정하지 않는다. handheld 해결은 새 content와 같은 계산/검증을 요구한다.

## 검토 근거

- 모든 합계는 dependency를 transitive closure로 펼친 뒤 unique asset을 한 번만 더한 값인가?
- baseline, added resident와 transition transient를 구분했는가?
- `unknown` transient와 load p95를 pass로 바꾸지 않았는가?
- missing optional과 missing critical의 사용자 결과가 다른가?
- cancel/stale completion이 새 generation을 변경하지 않고 기준선 복귀 evidence를 요구하는가?
