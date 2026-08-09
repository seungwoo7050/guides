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

템플릿은 정답 문구를 강제하지 않는다. 자동 검사는 초기 fixture의 구조와 교차 참조만 검사하며, 작성한 판단이 타당한지는 상태·실패·근거를 읽을 수 있는 다른 사람이 검토해야 한다.

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
