# 용량과 업데이트 계획

30일 host·service metric과 component 목록에서 자원 고갈과 업데이트 위험을 판정합니다.

관련 문서: [`docs/16-capacity-resource-limits-and-updates.md`](../../docs/16-capacity-resource-limits-and-updates.md)

## 구현 계약

`workspace/plan.py`의 `analyze(metrics_path, components_path, policy_path)`를 완성합니다.

반환값에는 다음이 필요합니다.

- 최신 memory headroom
- disk 성장률과 임계값까지 남은 일수
- backup staging을 포함한 disk peak
- DB pool과 관리자 reserve를 고려한 connection budget
- OOM·restart 증거
- p95 latency와 오류율 budget 위반
- 지원 종료·오래된 base image 위험
- 각 finding의 severity, evidence, action, owner, deadline, verification, rollback

## 검증

```sh
python3 scripts/new-workspace.py exercises/16-capacity-and-updates
cd exercises/16-capacity-and-updates
./verify.sh workspace
```

작업공간 생성 명령은 저장소 루트에서 실행합니다. 숫자만 계산하지 말고 어떤 조치를 누가 언제까지 수행하며 무엇으로 검증·되돌릴지 연결합니다. 자기 설명까지 마친 뒤에만 `reference/`와 `./verify.sh reference`를 비교합니다.

fixture의 component version과 지원 종료일은 판정 로직을 연습하기 위한 합성 정책 값입니다. 실제 업데이트 판단에서는 공급자 공식 지원 주기와 현재 승인 version을 별도로 수집해 입력합니다.

## 권장 구현 순서

아래 번호는 실제 Git 이력이 아니라 `reference/` 전체의 학습용 construction order입니다. 파일마다 번호를 다시 시작하지 않습니다.

| 번호 | 구현 경계 |
|---:|---|
| 1 | finding/action output schema |
| 2 | input·time-range validation과 derived budget |
| 3 | capacity·OOM·latency·error findings |
| 4 | component support·base rebuild lifecycle |
| 5 | deterministic report projection |

## 완료 기준

- [ ] `./verify.sh workspace`가 통과하고 memory headroom, disk 소진 시점·peak, DB connection budget, p95·오류율을 fixture에서 재계산할 수 있다.
- [ ] 각 finding에 severity와 수치 evidence뿐 아니라 owner, deadline, verification, rollback이 연결된다.
- [ ] 지원 종료와 base image 위험은 합성 fixture와 실제 공급자 공식 지원 자료를 구분해 판단한다.

## 자기 설명

1. 평균 사용량 대신 backup staging을 포함한 peak와 headroom을 함께 봐야 하는 이유는 무엇인가?
2. update 계획에 검증과 rollback을 미리 붙이지 않으면 어떤 상태에서 변경을 중단할지 왜 결정하기 어려운가?
3. component 지원 정책 입력이 오래되었을 때 분석 결과를 신뢰하지 않고 갱신해야 하는 기준은 무엇인가?
