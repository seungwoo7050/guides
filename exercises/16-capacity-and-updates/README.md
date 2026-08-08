# 용량과 업데이트 계획

30일 host·service metric과 component 목록에서 자원 고갈과 업데이트 위험을 판정합니다.

관련 문서: [`docs/16-capacity-resource-limits-and-updates.md`](../../docs/16-capacity-resource-limits-and-updates.md)

## 구현 계약

`skeleton/plan.py`의 `analyze(metrics_path, components_path, policy_path)`를 완성합니다.

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
cd exercises/16-capacity-and-updates
./verify.sh skeleton
./verify.sh reference
```

숫자만 계산하지 말고 어떤 조치를 누가 언제까지 수행하며 무엇으로 검증·되돌릴지 연결합니다.

fixture의 component version과 지원 종료일은 판정 로직을 연습하기 위한 합성 정책 값입니다. 실제 업데이트 판단에서는 공급자 공식 지원 주기와 현재 승인 version을 별도로 수집해 입력합니다.
