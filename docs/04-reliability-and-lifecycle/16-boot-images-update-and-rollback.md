# boot image, update와 rollback

현장 update는 새 binary를 flash에 복사하는 작업이 아닙니다. bootloader, image slot, persistent schema, self-test, confirmation과 rollback이 reset과 power loss 속에서도 일관된 상태를 유지해야 합니다. 이 장은 image authenticity algorithm보다 **firmware lifecycle 상태 기계와 복구 계약**에 집중합니다.

## 학습 목표

- boot ROM, bootloader, secure component와 application image의 책임을 구분합니다.
- primary/secondary slot, pending, trial, confirmed와 revert 상태를 설명합니다.
- download, install, boot, self-test, confirm과 rollback의 cut point를 설계합니다.
- application·bootloader·persistent data의 compatibility 계약을 검토합니다.
- signature validation 결과와 lifecycle correctness를 분리합니다.

## boot chain

```text
immutable/ROM boot
→ first-stage bootloader
→ optional secure firmware
→ image selector/validator
→ application
```

각 단계는 다음 단계의 address, format, authenticity와 execution environment를 결정할 수 있습니다. bootloader에서 application으로 넘길 때 vector table, stack, interrupt, clock, memory protection와 retained reason을 정리해야 합니다.

## image inventory

```text
bootloader region
primary slot
secondary slot 또는 download area
scratch/status trailer
persistent data
factory/recovery image optional
```

각 region의 address, size, erase unit와 owner를 고정합니다. application linker script와 bootloader partition map이 같은 계약을 사용해야 합니다.

## update 상태 기계

대표 상태:

```text
CONFIRMED(v1)
→ download v2
→ CANDIDATE(v2)
→ validate/install
→ TRIAL(v2, previous=v1)
   ├─ self-test + confirm → CONFIRMED(v2)
   └─ reset/timeout/fail → REVERT(v1)
→ CONFIRMED(v1)
```

구현은 swap, overwrite, direct-XIP 등으로 다를 수 있지만 trial과 confirmation의 의미를 분명히 합니다.

## download 완료와 install 가능을 구분합니다

candidate metadata:

- image size와 target slot
- version/build ID
- hardware compatibility
- required bootloader/version
- hash/signature validation result
- dependency images
- persistent schema compatibility
- download completeness

network/file transfer 성공만으로 boot 가능한 image가 아닙니다.

## trial boot

새 image를 영구 확정하기 전에 제한된 self-test를 수행합니다.

- startup과 critical driver readiness
- persistent data decode/migration
- required sensor/storage identity
- watchdog supervisor 시작
- communication 최소 경로
- safety output와 configuration

모든 기능을 긴 시간 검증할 수는 없습니다. confirmation deadline와 required checks를 정합니다.

application이 너무 일찍 confirm하면 boot 직후 잠시만 동작하는 image가 영구화됩니다. 너무 늦으면 정상 동작 중 reset에도 반복 revert될 수 있습니다.

## confirmation은 durable transition입니다

```text
trial application running
→ self-test evidence complete
→ boot metadata confirm write
→ read-back/verify
→ 다음 reset에서도 same image selected
```

confirm write 중 power loss를 고려합니다. boot metadata format과 atomicity는 bootloader contract입니다.

## rollback가 가능한 조건

- previous image가 보존돼 있습니다.
- bootloader가 previous slot을 선택할 수 있습니다.
- persistent data가 previous image와 호환됩니다.
- external component firmware/configuration도 호환됩니다.
- anti-rollback security policy가 허용합니다.
- repeated failure counter와 recovery mode가 있습니다.

binary slot만 남아 있다고 functional rollback이 보장되는 것은 아닙니다.

## multi-image update

application core, network core, radio firmware와 secure component가 함께 바뀔 수 있습니다.

필요한 것:

- dependency manifest
- compatible version set
- install ordering
- partial success recovery
- cross-image confirmation
- shared persistent schema

각 image를 독립적으로 confirm하면 호환되지 않는 조합이 남을 수 있습니다. bundle 또는 coordinated state machine을 사용합니다.

## power-loss cut point

- download metadata write
- candidate payload write
- validation metadata write
- slot swap/copy
- boot status update
- first trial boot
- self-test 중
- confirmation write
- revert copy/swap

모든 cut point 뒤 bootloader는 최소 하나의 bootable image와 판별 가능한 metadata를 찾아야 합니다.

## authenticity와 lifecycle correctness

signature 검증은 image가 허가된 signer에서 왔고 byte가 변하지 않았다는 근거가 될 수 있습니다. 다음을 자동으로 보장하지 않습니다.

- image가 해당 hardware와 compatible
- application이 self-test 통과
- storage migration이 rollback-compatible
- boot metadata가 power-loss-safe
- signing key가 안전하게 provision됨
- debug interface와 downgrade policy가 안전

보안 위협 모델과 key lifecycle은 `cybersecurity` 심화 영역입니다.

## build ID와 현장 evidence

모든 crash/update report에 최소한 다음을 연결합니다.

- bootloader version
- selected image version/build ID/hash
- slot와 trial/confirmed state
- reset cause
- update attempt counter
- rollback reason
- persistent schema version

ELF와 exact configuration을 release artifact로 보존합니다.

## failure와 검증

- corrupted candidate
- wrong board/hardware ID
- oversized image
- trial image immediate crash
- trial image late watchdog reset
- confirm write 중 power loss
- previous image + new schema incompatibility
- repeated rollback loop
- multi-image partial install

작은 상태 모델은 [`examples/update-state-model`](../../examples/update-state-model/README.md)에서 관찰합니다.

## 실습 연결

[update와 rollback 모델](../../exercises/06-update-rollback-model/README.md)은 candidate, trial, confirm, reset와 revert를 deterministic event sequence로 설계합니다.

## 직접 확인할 문제

1. signature가 유효해도 wrong-board image를 boot하면 안 되는 이유를 설명해 보세요.
2. trial image가 storage schema를 irreversible하게 변경하면 rollback이 깨지는 trace를 작성해 보세요.
3. confirmation을 너무 일찍/늦게 하는 위험을 비교해 보세요.
4. multi-image update에서 각 image를 독립 confirm할 때 생기는 incompatible set를 예로 들어 보세요.

## 이 장이 보장하지 않는 것

cryptographic primitive, PKI, key provisioning, secure element와 anti-rollback fuse 설계를 완결하지 않습니다. MCUboot 같은 구현을 사용할 때도 사용하는 mode와 release의 공식 design 문서를 확인합니다.
