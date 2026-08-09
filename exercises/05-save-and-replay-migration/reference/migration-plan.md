# save migration 계획 예시 해설

이 예시는 fixture에서 확인 가능한 v1→v2 변환과 실패 원칙을 보여 준다. production checksum 알고리즘과 storage API의 durability는 입력에 없으므로 별도 확인 항목으로 남긴다.

## envelope validation

- format: `relay-arena-save`가 아니면 decode 전에 거부한다.
- checksum: `fixture-valid-v1`은 합성 fixture의 valid 표식이다. 실제 구현은 payload를 runtime object로 만들기 전에 versioned checksum 알고리즘으로 검증한다.
- supported version: v1은 전용 decoder 뒤 v2로 migration하고, v2는 현재 decoder로 읽는다.
- newer version rejection: v3 이상은 downgrade decode를 시도하지 않고 actionable error와 원본 보존 경로를 제공한다.
- original generation retention: migration 성공, v2 invariant 검증과 durable replace가 끝날 때까지 v1 원본/previous known-good를 유지한다.

## v1 → v2 field mapping

| v1 field | v2 field | conversion | default/fallback | invariant | failure action |
|---|---|---|---|---|---|
| `bestTimeSeconds=54.21` | `best_time_ms=54210` | finite non-negative seconds × 1000을 정수 millisecond로 변환 | 값이 없으면 `null` | null 또는 0 이상의 integer | invalid number면 migration 중단, 원본 유지 |
| `unlockedSkins` | `unlocked_cosmetics` | alias 표로 `skin.default`→`cosmetic.player.default`, `skin.founder-blue`→`cosmetic.player.founder-blue` | `removed` 표의 `skin.test-red`만 default로 교체하고 안내 | stable id 배열, 중복 제거 정책 명시 | 알 수 없는 id를 조용히 삭제하지 않고 migration 중단/복구 UI로 보냄 |
| `input.dashKey` | `input_settings.bindings.Dash` | `LeftShift`를 logical `Dash` binding으로 옮기고 `bindings_version=2` 기록 | binding 누락 시 current default를 사용하되 변경 사실 표시 | 알려진 logical action만 참조 | 충돌/알 수 없는 control이면 default + actionable warning 또는 사용자 재설정 |
| `input.holdToDash=true` | `accessibility.dash_mode=hold` | old boolean 의미를 enum으로 변환 | schema default `hold` | 허용 enum만 사용 | invalid type이면 default를 적용하고 migration warning 기록 |
| v1에 없음 | `accessibility.camera_shake_scale=1.0` | 없음 | schema default | 허용 범위는 runtime schema가 검증 | 범위 밖이면 migration 실패 또는 documented clamp |
| `audio.master=0.8` | `audio_settings.master=0.8` | 단위를 유지해 object 이름만 변경 | field 누락 시 project default | 0..1 범위 | 범위 밖이면 migration 실패 또는 documented clamp |

Fixture의 정상 변환 결과에서 필수 payload field는 `best_time_ms`, `unlocked_cosmetics`, `input_settings`, `accessibility`, `audio_settings` 다섯 개다.

## atomic commit

```text
read original generation
→ envelope format/version/checksum validate
→ decode with v1 decoder
→ pure v1→v2 migration
→ validate all v2 required fields and invariants
→ write a sibling temporary generation
→ flush according to the platform storage contract
→ read back and validate checksum/schema
→ atomically replace current pointer/file where supported
→ retain previous known-good generation by policy
```

어느 단계에서든 실패하면 temporary만 폐기하고 v1 원본과 previous known-good를 선택 가능하게 유지한다. platform의 rename/fsync/cloud 보장은 입력에 없으므로 실제 target에서 failure injection으로 확인한다.

## compatibility matrix

| input | expected | user-visible action | evidence |
|---|---|---|---|
| valid v1 fixture | v2로 변환; `54210`, 두 aliased cosmetic, binding/accessibility/audio 보존 | migration 완료 후 정상 시작 | 변환 전후 field assertion + v2 validator |
| valid v2 | migration 없이 v2 decoder와 invariant 검증 | 정상 시작 | schema version 2와 required field 검사 |
| v3/newer | 안전하게 거부; 원본 변경 없음 | 더 최신 build 필요 메시지 | unsupported-version result와 unchanged source hash |
| checksum mismatch | decode/runtime object 생성 전 거부 | backup 선택 또는 손상 안내 | checksum failure와 previous-generation hash |
| explicit removed cosmetic id | `removed` policy에 따라 default로 교체하고 메시지 | 지원 종료 cosmetic 안내 | alias/removal decision event |
| unknown cosmetic id | 조용히 삭제하지 않음; 정책이 없으므로 migration을 중단 | 복구/지원 경로 제시 | unresolved stable-id error와 원본 보존 |
| storage full during write | temporary write 실패, current/previous 유지 | 공간 확보 후 재시도 | injected ENOSPC/quota failure와 old generation read-back |
| interruption before replace | old current가 계속 유효 | 재시작 때 incomplete temporary 정리 | crash-point matrix와 current pointer 검사 |

## 사람 검토 rubric

- decoder와 migration이 분리돼 있고 runtime object 생성 전에 envelope를 검증하는가?
- `54.21`을 `54210`으로 옮기고 두 alias를 정확히 resolve하는가?
- schema default를 적용한 field와 fixture에서 보존한 field를 구분하는가?
- unknown/removed id의 정책을 혼동하거나 사용자 데이터를 조용히 삭제하지 않는가?
- 실패 지점마다 어떤 generation이 읽히는지와 증거를 제시하는가?
