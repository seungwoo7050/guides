# replay divergence 예시 해설

## determinism 범위

- platform/build: 두 trace 모두 `relay-client@1.0.0`; platform과 runtime 세부 정보는 fixture에 없어 cross-platform determinism을 주장하지 않는다.
- content manifest: 둘 다 `arena-rules@17`.
- fixed step: 둘 다 `16667us`.
- compared state fields: fixture가 제공하는 checkpoint state hash 전체. canonical field 목록은 제공되지 않았다.
- excluded presentation state: replay fixture에 presentation field가 없으므로 gameplay checkpoint 밖 상태는 비교 대상이 아니다.

## 비교 결과

- last equal checkpoint: tick `5`, hash `h5-f110`.
- first unequal checkpoint: tick `10`; A=`h10-8bb2`, B=`h10-5c99`.
- first candidate command/event: sequence `3`, tick `8`, `move`; A value=`[0,1000]`, B value=`[0,900]`.
- confirmed first diverging tick: fixture hash만으로 직접 확정 가능한 지점은 tick `10` checkpoint다. tick `8`은 유일한 첫 입력 차이이므로 earliest affected tick이며, tick-level runner/hash로 8..10 구간을 확인해야 한다.
- affected subsystem: move command decoding/integration과 그 결과를 포함하는 canonical gameplay state.

두 replay의 initial hash, build, content, fixed step, sequence 1–2 command와 tick 5 checkpoint가 같으므로 content mismatch나 초기 상태 차이를 첫 원인으로 들 수 없다.

## 가능한 원인과 반증

| hypothesis | supporting evidence | counter-evidence | next probe | status |
|---|---|---|---|---|
| command payload changed | sequence 3의 Y 값이 `1000` 대 `900`이고 이후 첫 checkpoint가 다름 | 없음 | tick 8 직전 snapshot에서 sequence 3만 각각 적용해 tick별 hash 비교 | confirmed input difference / causal candidate |
| unordered iteration | hash divergence 형태만으로는 일반적으로 가능 | first differing serialized input이 이미 존재 | 두 trace에 같은 sequence 3 payload를 넣은 control run | unsupported by fixture |
| random stream drift | random state가 canonical state에 있다면 가능 | seed/random event가 fixture에 없고 명시적 command 차이가 먼저 보임 | random stream id/counter를 checkpoint에 추가 | unsupported by fixture |
| content version mismatch | content 차이는 divergence를 만들 수 있음 | 두 trace 모두 `arena-rules@17` | actual loaded manifest hash를 trace에 추가 | ruled out at declared version level |

## 최소 재현

- initial snapshot: tick 5 hash `h5-f110`; payload snapshot은 fixture에 없어 runner에서 export해야 한다.
- command slice: sequence 3, tick 8 `move` 하나만 A=`[0,1000]`, B=`[0,900]`으로 비교한다.
- expected hash sequence: tick 5 `h5-f110` → tick 10 `h10-8bb2` → tick 15 `h15-224e`.
- actual hash sequence: tick 5 `h5-f110` → tick 10 `h10-5c99` → tick 15 `h15-943a`.
- narrowing evidence: tick 6–10을 매 tick hash하고 command-consumption event에 tick/sequence/value를 남긴다.

## 사람 검토 rubric

- 마지막 equal과 첫 unequal checkpoint를 각각 5와 10으로 찾았는가?
- sequence 3/tick 8의 payload 차이를 첫 candidate로 찾았는가?
- checkpoint tick 10을 “첫 diverging tick 10”으로 단정하지 않고 관측 해상도의 한계를 밝혔는가?
- 같은 build/content/fixed step이라는 반증으로 불필요한 가설을 좁혔는가?
- presentation과 cross-platform bit determinism을 fixture 근거 없이 주장하지 않는가?
