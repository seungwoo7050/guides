# 단계 실습

실습은 특정 엔진 API를 맞히는 문제가 아니다. 제공된 합성 자료에서 게임 상태의 소유자, 전이 사건, 수명, 실패와 검증 근거를 찾아 **다른 개발자가 구현 문제로 분해할 수 있는 산출물**을 만든다.

## 공통 진행 순서

```text
README의 범위와 완료 조건 확인
→ inputs에서 사실과 식별자 추출
→ template을 복사해 자신의 작업 디렉터리에서 작성
→ 대표 오답을 스스로 반증
→ 사람 검토 질문으로 누락 확인
→ Capstone에서 같은 계약을 다시 사용
```

각 실습의 `template/`은 의도적으로 미완성이고 `reference/`는 fixture가 결정하는 관측값과 한 가지 완성 해설을 제공한다. reference는 복사할 문장 정답이 아니라 계산·상태 전이·trace·gate를 비교할 기준이다. 공통 검사기는 같은 계약으로 reference 통과, template와 대표 오답 거부를 확인한다. 작성한 설계 판단은 상태·실패·근거를 읽을 수 있는 다른 사람이 별도로 검토한다.

## 실습 목록

| 순서 | 실습 | 중심 문서 | 누적 결과 |
|---|---|---|---|
| 01 | [시간 단계 분석](01-time-step-analysis/README.md) | `02-game-loop-time-and-frames` | clock·fixed step·overload 정책 |
| 02 | [입력과 명령 계약](02-input-command-contract/README.md) | `03-input-command-camera-and-ui` | device→action→command→result 경계 |
| 03 | [월드 수명 검토](03-world-lifecycle-review/README.md) | `04-world-scene-entity-component-lifecycles` | owner·reference·cleanup 지도 |
| 04 | [자산 loading 계획](04-asset-loading-plan/README.md) | `06-assets-import-cooking-loading-and-memory` | dependency·resident set·fallback |
| 05 | [save와 replay migration](05-save-and-replay-migration/README.md) | `09-save-migration-replay-and-determinism` | schema 전환과 first divergence |
| 06 | [authority와 latency](06-authority-and-latency/README.md) | `11-network-authority-replication-and-latency` | intent·validation·prediction·correction |
| 07 | [성능 예산 검토](07-performance-budget-review/README.md) | `14-performance-budgets-profiling-and-scalability` | target workload·critical path·품질 단계 |
| 08 | [release readiness](08-release-readiness/README.md) | `15-platform-accessibility-lifecycle-and-release` | 증거 기반 release gate |

## 제출 원칙

- fixture에 없는 의도를 만들어 내지 않는다.
- 사실, 가설, 결정과 미확인 항목을 구분한다.
- 평균만 제시하지 않고 경계·최악·실패 사례를 포함한다.
- “엔진이 처리한다”는 문장 대신 프로젝트가 확인해야 할 보장을 쓴다.
- 구현하지 않은 범위와 후속 전문 브랜치를 명시한다.

## 격리·검증 순서

저장소 root에서 존재하지 않는 외부 절대 경로를 지정한다.

```sh
WORK_PARENT="$(mktemp -d)"
./scripts/new-workspace.sh "$WORK_PARENT/game-development"
```

각 `submission/` 복사본을 작성한 뒤 공통 검사기에 실습 ID와 경로를 전달한다.

```sh
python3 scripts/check_submission.py \
  --exercise 01 \
  --submission "$WORK_PARENT/game-development/exercises/01-time-step-analysis/submission"
```

기계 판정 가능한 결과가 맞으면 `AUTOMATED_OK`가 출력된다. 이어지는 `MANUAL_REVIEW_REQUIRED`는 성공을 취소하는 오류가 아니라, 자동 검사가 판단하지 않는 trade-off·근거·한계 질문이다. 해당 답과 증거가 없으면 실습을 교육적으로 완료했다고 보지 않는다.

검사기 방향 자체는 다음 명령으로 확인한다.

```sh
python3 scripts/check_submission.py --self-test
```

이 meta-test는 8개 reference 통과, 8개 template 거부와 실습별 known-bad mutant 거부를 요구한다. 검사기는 추적 source나 외부 learner workspace를 수정·정리하지 않는다.
