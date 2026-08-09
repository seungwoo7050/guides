# 저장, migration, replay와 determinism

## 문제

save와 replay는 둘 다 게임 상태를 기록하지만 목적과 필요한 정보가 다릅니다.

- save: 나중에 사용자가 계속 플레이할 수 있는 durable state
- checkpoint: 빠른 재시작을 위한 제한된 snapshot
- replay: input/event를 다시 적용해 같은 경험 또는 조사 가능한 결과를 재구성
- crash recovery: 중단 직전 안전한 상태로 복귀
- network snapshot: 현재 authoritative state를 client에 전달
- telemetry: 분석용 event로 정본 복원이 보장되지 않음

하나의 serialization 함수를 모든 용도에 재사용하면 local pointer, presentation cache와 transient state가 저장되거나, 필요한 rule version과 random state가 빠져 복구·replay가 실패합니다.

## 핵심 상태

### save envelope

```json
{
  "format": "relay-arena-save",
  "schema_version": 3,
  "game_build": "2026.08.1",
  "content_version": "arena-rules@17",
  "profile_id": "local-profile-1",
  "created_at": "...",
  "payload": {},
  "checksum": "..."
}
```

payload 외에 어떤 code/content로 해석해야 하는지 기록합니다.

### durable과 transient

저장 후보:

- progression, unlock, settings
- stable entity/item id와 semantic state
- quest/objective state
- world modification 중 프로젝트가 보존하기로 한 것

일반적으로 재생성 가능한 것:

- raw pointer, component address
- render/animation cache
- navigation path와 physics contact cache
- active async request
- open file/socket
- frame-local event queue

### migration

```text
read envelope
→ validate checksum/type
→ select versioned decoder
→ migrate step by step
→ validate invariants
→ resolve content ids/fallback
→ construct runtime state
→ atomic commit or reject
```

migration은 부분 성공 상태를 사용자 save 위에 덮어쓰지 않습니다.

### replay 구성

- initial snapshot 또는 deterministic seed
- ordered command/event stream
- tick/sequence
- rule/content/build version
- subsystem random streams
- periodic state hash/checkpoint
- nondeterministic external result의 기록 또는 stub

## 설계 계약

### save write를 atomic하게 만듭니다

대표 순서:

```text
serialize to temporary file
→ flush and validate
→ write/flush metadata if separate
→ atomic rename/replace
→ retain previous known-good generation
```

platform storage API의 실제 보장을 확인합니다. cloud sync와 quota failure를 별도 상태로 다룹니다.

### version migration을 누적 함수로 관리합니다

`v1 -> latest` 하나보다 `v1→v2`, `v2→v3`의 작은 순차 migration이 검토하기 쉽습니다. 각 단계는 input을 보존하거나 명시적으로 변환하고 invariant를 검증합니다.

### unknown과 missing을 구분합니다

- unknown field: forward compatibility를 위해 보존/무시 가능
- missing required field: default 또는 migration 필요
- unknown stable id: content removal/rename이므로 fallback·refund·reject 정책 필요
- newer schema: older runtime이 열지 못하도록 안전하게 거부

### replay determinism 범위를 문서화합니다

예:

```text
같은 platform, executable hash, content manifest와 command trace에서
매 60 tick canonical gameplay state hash가 동일해야 한다.
rendering, audio와 cosmetic particle state는 비교하지 않는다.
```

필요한 범위보다 강한 bit-exact cross-platform 결정을 주장하지 않습니다.

### canonical serialization을 사용합니다

hash를 만들 때 map iteration, float formatting, unordered component order가 결과를 바꾸지 않게 정렬·quantization·field policy를 둡니다.

### save와 backend authority를 구분합니다

온라인 economy, entitlement와 competitive result는 local save를 정본으로 두지 않습니다. local cache와 authoritative service state의 merge/recovery 정책을 정합니다.

## 대표 실패

### struct memory를 그대로 dump합니다

padding, pointer, endianness, compiler와 version에 종속됩니다. schema와 field semantics를 사용합니다.

### 최신 code로 old save를 바로 deserialize합니다

field rename·type change와 removed content에서 silent corruption이 발생합니다. versioned decoder와 migration을 둡니다.

### save 실패 뒤 기존 파일을 손상시킵니다

in-place write 중 process 종료나 storage full이 발생합니다. temporary + atomic replace와 previous generation을 둡니다.

### replay hash가 다르지만 마지막 state만 비교합니다

첫 divergence tick을 찾을 수 없습니다. periodic hash와 subsystem trace를 둡니다.

### global random stream 하나를 공유합니다

cosmetic particle 호출 수가 gameplay random 결과를 바꿉니다. subsystem/semantic stream을 분리합니다.

### content version을 기록하지 않습니다

같은 command가 다른 rule table과 collision asset에서 다른 결과를 만듭니다.

## 관찰과 검증

### save matrix

| writer | reader | expected |
|---|---|---|
| v1 | current | migration success |
| current | current | exact semantic round trip |
| current+1 | current | safe unsupported rejection |
| corrupted | current | reject, previous generation retained |
| missing DLC | current | defined fallback or explicit block |

### replay 검사

- same fixture를 여러 번 실행해 state hash가 같습니다.
- command 하나를 바꾸면 예상 tick 이후에만 hash가 달라집니다.
- render FPS와 presentation option을 바꿔도 gameplay hash가 같습니다.
- unordered collection 순서를 바꿔도 canonical hash가 같습니다.
- old content manifest를 사용할 수 없으면 replay를 명시적으로 거부합니다.
- first diverging tick과 관련 subsystem을 report합니다.

### failure injection

- write 중 process termination
- disk full/quota
- checksum mismatch
- cloud/local conflict
- unknown item/quest id
- migration 중 exception
- newer schema

## 실습 연결

[save와 replay migration 실습](../exercises/05-save-and-replay-migration/README.md)에서 old save, new schema와 diverging trace를 분석합니다. [`fixed-step-replay`](../examples/fixed-step-replay/README.md)는 canonical state hash의 작은 예제입니다.

## 기존 브랜치와 경계

- file descriptor, flush와 filesystem durability의 원리는 `operating-systems`가 소유합니다.
- DB transaction과 distributed sync는 `database-systems`·`distributed-services`가 소유합니다.
- 현재 문서는 game save semantics, content migration, replay input/state hash와 deterministic scope를 소유합니다.

## 완료 기준

- save, checkpoint, replay, network snapshot과 telemetry를 다른 목적의 기록으로 구분합니다.
- atomic write, versioned decoder, migration과 fallback을 설계합니다.
- deterministic 범위를 build/content/tick/state field 수준으로 제한해 정의합니다.
- corrupted/newer/missing-content save와 first replay divergence를 fixture로 검증합니다.
