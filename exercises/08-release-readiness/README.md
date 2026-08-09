# 08. release readiness

## 목표

build manifest와 분야별 evidence를 읽고 “기능이 플레이된다”를 release 가능 상태와 구분한다. 플랫폼 수명, 입력·접근성, save/content/protocol compatibility, crash context, telemetry와 rollback을 gate로 만든다.

## 입력

- [`inputs/build-manifest.json`](inputs/build-manifest.json)
- [`inputs/release-evidence.json`](inputs/release-evidence.json)
- [`inputs/platform-checks.csv`](inputs/platform-checks.csv)

## 제출

- [`template/release-review.md`](template/release-review.md)
- [`template/gate-matrix.csv`](template/gate-matrix.csv)

`template/`은 의도적으로 미완성이다. candidate identity와 gate 판정의 한 가지 유효한 예시는 [`reference/release-review.md`](reference/release-review.md)와 [`reference/gate-matrix.csv`](reference/gate-matrix.csv)에 있다. waiver와 residual-risk 결정은 조직 권한을 가진 사람이 별도로 승인해야 한다.

## 대표 오답

- editor에서 한 번 플레이했으므로 ship한다.
- open known issue에 owner·영향·fallback·재검토 trigger가 없다.
- content manifest와 save/protocol version을 build identity에 연결하지 않는다.
- remap·subtitles·contrast·pause/suspend를 선택 품질로 취급한다.
- crash dump와 telemetry가 build/content/session 식별자를 포함하지 않는다.

## 사람 검토 질문

1. evidence가 정확한 candidate build에서 수집됐는가?
2. target platform별 save path, suspend/resume, controller 변화가 검증됐는가?
3. known issue의 residual risk owner와 ship/block 기준이 있는가?
4. release 뒤 문제를 식별하고 rollback/disable할 수 있는가?
5. missing content, old save, incompatible protocol이 안전하게 거부/저하되는가?

## 완료 기준

- 각 gate를 pass/fail/waived/unknown으로 판정한다.
- unknown을 pass로 취급하지 않는다.
- block 또는 conditional ship 결정을 근거와 owner로 제출한다.

제출 검사기는 candidate, evidence status/build, stale·unknown·fail 처리와 blocking gate를 자동 확인한다. 실제 ship 권한, waiver와 사용자 영향 평가는 자동화하지 않는다.
