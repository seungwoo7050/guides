# 애니메이션, 오디오, VFX와 표현 경계

## 문제

플레이어가 보는 게임은 animation, audio, VFX, camera, haptic과 UI가 함께 만든 결과입니다. 이 표현 계층은 gameplay state를 풍부하게 전달하지만, 규칙 정본이 되면 frame rate, asset, localization과 network 조건에 따라 결과가 달라집니다.

대표적인 위험은 다음과 같습니다.

- animation notify가 유일한 damage source입니다.
- particle이 끝나야 entity가 despawn합니다.
- audio 재생 완료 callback이 phase transition을 결정합니다.
- cosmetic asset miss가 gameplay initialization을 block합니다.
- server가 camera shake와 footstep audio까지 replication합니다.
- presentation event를 retry해 sound/VFX가 중복됩니다.

표현 계층은 **authoritative event를 소비하고, 필요한 player feedback을 생성하며, 실패해도 규칙 상태를 보존**해야 합니다.

## 핵심 상태

### simulation state와 presentation state

| simulation | presentation |
|---|---|
| health = 0 | death animation, fade, sound |
| attack phase/tick | montage position, trail VFX |
| velocity/grounded | locomotion blend, footsteps |
| objective captured | banner, music transition, haptic |
| cooldown expiry tick | radial UI animation |

presentation은 local frame, quality setting과 player option에 따라 달라질 수 있습니다.

### event 종류

- domain event: `DamageApplied`, `EntityDied`, `ObjectiveCaptured`
- authored marker: foot plant, weapon release frame, camera cut marker
- presentation command: play effect, blend animation, show message
- presentation completion: cinematic ended, transition faded
- acknowledgement: loading screen hidden, user skipped cinematic

모든 event가 reliable하거나 replayable할 필요는 없습니다. 역할을 구분합니다.

### animation 상태

- gameplay intent/state
- animation graph state와 parameter
- clip time/blend history
- root motion delta
- skeletal pose
- event/marker cursor

save·network·replay에서 어느 층까지 보존할지 결정합니다.

### audio와 VFX 수명

- one-shot vs looping
- world-attached vs UI/non-spatial
- owner death 뒤 tail 허용 여부
- priority·voice limit·stealing
- quality tier와 pooling
- listener/camera transition

## 설계 계약

### domain event를 의미 단위로 만듭니다

```json
{
  "event": "damage_applied",
  "tick": 441,
  "source": "player-1",
  "target": "enemy-7",
  "amount": 25,
  "kind": "melee",
  "event_id": "m12:441:17"
}
```

presentation은 event를 받아 local option과 visibility에 맞게 표현합니다. event id는 duplicate suppression과 trace correlation에 사용할 수 있습니다.

### animation-driven gameplay의 범위를 정합니다

두 방향이 있습니다.

1. simulation이 timing을 정하고 animation이 따라갑니다.
2. authored animation marker가 gameplay window를 제안하고 simulation이 검증·적용합니다.

어느 쪽이든 network/replay에서 marker version과 tick mapping을 보장해야 합니다. clip 재생 callback이 rule commit을 직접 수행하지 않게 합니다.

### root motion owner를 명시합니다

- animation이 desired delta를 생성
- movement system이 collision·authority를 검증
- accepted delta를 canonical pose에 적용
- render pose가 interpolation과 correction을 표현

root motion delta를 world transform에 두 번 적용하지 않게 합니다.

### presentation failure policy를 둡니다

- missing cosmetic: default asset 사용
- audio device unavailable: gameplay 계속
- VFX budget 초과: drop/LOD
- animation asset miss: safe fallback pose
- cinematic skip: completion event를 idempotent하게 처리

### user option을 rule과 분리합니다

camera shake, motion blur, subtitle, haptic, color treatment, audio mix와 screen flash option은 presentation을 바꾸되 gameplay advantage와 정보 손실을 검토해야 합니다.

## 대표 실패

### notify가 누락되면 damage가 발생하지 않습니다

content edit가 correctness를 깨뜨립니다. marker를 validator와 test로 검사하거나 simulation timing을 정본으로 둡니다.

### domain event와 visual event가 같은 bus에서 무제한 broadcast됩니다

중요도·delivery·lifetime이 달라 debugging이 어렵습니다. typed channel과 owner를 둡니다.

### pause에서 audio·animation·gameplay clock이 불일치합니다

menu pause 뒤 sound와 marker가 진행돼 resume 때 event가 몰립니다. system별 clock policy를 정합니다.

### pooled VFX가 이전 owner와 parameter를 유지합니다

새 spawn에서 잘못된 color, target과 callback이 남습니다. reset contract와 generation을 둡니다.

### local prediction event가 correction 뒤 중복 재생됩니다

예측 hit sound와 authoritative event가 모두 재생됩니다. predicted/confirmed event id와 reconciliation policy를 둡니다.

## 관찰과 검증

### event trace

```text
Tick 441 AttackWindowOpened
Tick 442 DamageApplied event_id=...
Frame 903 PresentationConsumed animation=attack_02 vfx=slash_A
Frame 904 AudioStarted voice=77
```

simulation tick과 render frame을 함께 기록하되 같은 식별자로 오인하지 않습니다.

### 검사 시나리오

- VFX/audio를 완전히 비활성화해도 gameplay 결과가 같습니다.
- missing animation/cosmetic asset에서 fallback이 동작합니다.
- pause·slow motion·skip에서 completion이 한 번만 발생합니다.
- replay에서 domain event sequence가 같고 presentation은 option에 따라 달라도 됩니다.
- prediction rollback 뒤 one-shot effect가 중복되지 않습니다.
- animation marker가 content validator와 test fixture에 의해 존재·순서 검사를 받습니다.
- low quality tier에서 정보 전달이 사라지지 않습니다.

### 품질 판단

correctness와 feel을 분리합니다.

- 자동 검사: event, state, marker, duplicate, fallback
- playtest: readability, timing feel, motion sickness, audio clarity
- profile: animation evaluation, skinning, particles, voices, overdraw

## 실습 연결

Capstone의 `presentation-contract.md`에서 gameplay event와 animation/audio/VFX/UI consumer를 연결하고 fallback·duplicate suppression을 정의합니다.

## 기존 브랜치와 경계

- animation compression, rendering과 shader의 상세는 `computer-graphics` 심화입니다.
- audio system 내부 DSP 구현은 현재 범위가 아닙니다.
- 현재 문서는 gameplay rule과 presentation의 owner·event·time·failure 경계를 소유합니다.

## 완료 기준

- authoritative state와 animation/audio/VFX/UI state를 분리합니다.
- domain event, authored marker, presentation command와 completion을 구분합니다.
- root motion, pause, pooling과 prediction에서 중복·stale 상태를 방지합니다.
- 표현 계층이 실패하거나 품질이 낮아져도 gameplay invariant가 유지됨을 검증합니다.
