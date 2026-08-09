# 성능 예산 검토 예시 해설

이 해설은 fixture에 대한 한 가지 유효한 판정 예시다. percentile은 **nearest-rank**(`ceil(p × N)`) 방식으로 계산했다. 실제 프로젝트에서는 profiler의 표본 방식과 percentile 정의를 capture metadata에 함께 고정해야 한다.

## capture 신뢰성

- target hardware: `handheld-low`, 1280×720, 60 Hz
- build/configuration: `relay-client@1.0.0-profile`, `development-profile`, content `arena-rules@17`
- workload: warm/balanced 상태에서 90초, player 1, agent 12, hazard 24, medium VFX
- 한계: 표본이 12 frame과 5 load run으로 작고 GPU counter의 세부 pass, thermal drift, retail build, 다른 scene을 대표하지 않는다.

## frame 분석

- 정렬한 `frame_ms`의 p50/p95/p99는 각각 `16.4 / 55.4 / 55.4 ms`다.
- worst hitch는 `55.4 ms`의 `checkpoint_save`이며 50 ms 단일 hitch budget도 넘는다.
- 이 hitch는 main thread `52.0 ms`가 GPU `18.4 ms`보다 길어 CPU critical이다. 반대로 `full_screen_vfx` 표본은 GPU `26.5 ms`가 main `13.4 ms`보다 길다.
- `stream_complete`는 fixed step 2개, `checkpoint_save`는 3개를 실행한다. 장시간 frame이 더 많은 simulation work를 유발하므로 catch-up 상한과 dropped-time telemetry를 함께 확인해야 한다.

## memory와 loading

- cosmetic-ready resident는 CPU 650 + GPU 390 = `1040 MiB`로 900 MiB resident budget을 넘는다.
- agent-wave peak는 resident 720 + 420 = `1140 MiB`, transient까지 합치면 `1350 MiB`로 1100 MiB peak budget을 넘는다.
- post-exit은 `520 MiB / 9 bundles`로 frontend의 `430 MiB / 8 bundles`에 돌아오지 않는다. 90 MiB와 bundle 1개의 잔류 원인을 snapshot diff로 좁혀야 한다.
- cold total load nearest-rank p95는 `5520 ms`로 5000 ms budget을 넘는다. control-ready 최악은 3490 ms이며 missing cosmetic도 3300 ms에 control-ready가 되고 degraded-success로 끝난다.

## 변경 가설

| hypothesis | expected metric change | profile/trace to collect | possible regression | decision |
|---|---|---|---|---|
| result save를 fixed tick/render critical path 밖의 bounded commit queue로 이동 | checkpoint-save main time과 frame p95/p99 감소 | main-thread call tree, queue duration, result commit id trace | suspend 전 commit 유실·중복 | prototype 후 suspend fault와 함께 재측정 |
| optional cosmetic bundle을 control-ready 뒤로 지연하고 exit owner를 명시 | resident/peak와 cold-load p95 감소, post-exit baseline 복귀 | bundle refcount diff, load waterfall, memory snapshots | cosmetic pop-in·늦은 audio | low tier에서 적용하고 fallback UX 확인 |

## scalability 계약

| tier | target | changed systems | preserved gameplay/accessibility | expected budget |
|---|---|---|---|---|
| low | handheld-low | cosmetic preload 지연, VFX density 감소, agent presentation LOD | rule tick, collision, subtitles, remap 유지 | p95 ≤16.67 ms, resident ≤900 MiB |
| medium | handheld-mid | medium VFX와 bounded cosmetic preload | 같은 gameplay command와 accessibility 유지 | p95 ≤16.67 ms, peak ≤1100 MiB |
| high | desktop/high-end | higher presentation density와 optional cosmetic preload | gameplay result와 input semantics 동일 | device-specific budget 별도 기록 |

자동 검사는 계산과 budget 판정만 확인한다. 가설의 실제 효과, 화질과 사용자 경험은 target build 재측정과 사람 검토가 필요하다.
