# 산출물 검토 체크리스트

## 상태·소유권 문서

- [ ] state의 scope와 최종 writer가 있다.
- [ ] stable id, runtime instance와 generation이 구분된다.
- [ ] create, activate, disable, destroy와 unload가 구분된다.
- [ ] partial failure와 cleanup owner가 있다.
- [ ] presentation/cache/telemetry view를 정본과 구분한다.

## 시간·입력 문서

- [ ] real/game/fixed/render/server clock을 구분한다.
- [ ] input sampling과 simulation consumption이 분리된다.
- [ ] frame에 step이 0개/여러 개인 경우를 다룬다.
- [ ] pause reason과 system별 policy가 있다.
- [ ] focus loss/device disconnect cleanup이 있다.
- [ ] command가 device-independent intent다.

## 콘텐츠·자산 문서

- [ ] source/import/cooked/logical id/runtime resource를 구분한다.
- [ ] critical/optional dependency와 ready gate가 있다.
- [ ] target별 resident·transient·loading budget이 있다.
- [ ] stale async completion과 cancellation을 처리한다.
- [ ] stable id rename/removal과 fallback이 있다.

## gameplay·presentation 문서

- [ ] command precondition과 accepted/rejected result가 있다.
- [ ] gameplay invariant가 testable하다.
- [ ] presentation one-shot의 dedup/correction 정책이 있다.
- [ ] animation/audio/VFX/UI가 authoritative rule을 몰래 소유하지 않는다.
- [ ] 핵심 cue에 접근성 대안이 있다.

## save·replay 문서

- [ ] save envelope에 format/schema/build/content identity가 있다.
- [ ] versioned decoder와 migration 단계가 있다.
- [ ] atomic write와 previous known-good generation이 있다.
- [ ] newer/corrupt/missing-content case가 있다.
- [ ] determinism 범위와 canonical state field가 있다.
- [ ] first-divergence checkpoint/trace가 있다.

## multiplayer 문서

- [ ] client intent와 authoritative result가 분리된다.
- [ ] command/session/snapshot identity가 있다.
- [ ] duplicate, stale, reorder와 non-owner가 거부된다.
- [ ] prediction 가능한 state와 기다릴 state가 구분된다.
- [ ] correction 뒤 presentation 중복 정책이 있다.
- [ ] protocol/content compatibility gate가 있다.

## 성능 문서

- [ ] target hardware, build, workload와 thermal/power 상태가 있다.
- [ ] 평균 외에 p95/p99/worst hitch가 있다.
- [ ] CPU/GPU critical path 근거가 있다.
- [ ] resident, peak와 transient memory가 구분된다.
- [ ] control-ready/cosmetic-ready loading 지표가 있다.
- [ ] 변경 가설과 전후 같은 profile이 있다.

## release 문서

- [ ] candidate build/content/save/replay/protocol identity가 일치한다.
- [ ] pass/fail/unknown/stale를 구분한다.
- [ ] accessibility, input, suspend/resume와 storage가 gate에 있다.
- [ ] known issue에 impact, owner, fallback과 re-review trigger가 있다.
- [ ] rollback/feature-disable와 post-release telemetry가 있다.
- [ ] evidence가 정확한 candidate와 target에서 수집됐다.
