# LedgerLab 시나리오 자료

다음 순서로 읽습니다.

1. [`system-context.md`](system-context.md)
2. [`asset-register.json`](asset-register.json)
3. [`identity-policy.json`](identity-policy.json)
4. [`route-and-authorization-notes.md`](route-and-authorization-notes.md)
5. [`package-proxy-policy.json`](package-proxy-policy.json)
6. [`release-manifest.json`](release-manifest.json)
7. [`candidate-findings.json`](candidate-findings.json)
8. [`verification-observations.json`](verification-observations.json)
9. [`event-dictionary.md`](event-dictionary.md)
10. [`event-log.jsonl`](event-log.jsonl)
11. [`operator-notes.md`](operator-notes.md)
12. [`incident-runbook-excerpt.md`](incident-runbook-excerpt.md)

## 자료 해석 규칙

- 같은 주장에 자료가 충돌하면 source와 시각을 기록합니다.
- 설계 의도와 runtime state를 구분합니다.
- candidate finding은 확정 판정이 아닙니다.
- evidence가 없으면 안전 또는 침해를 단정하지 않습니다.
- 합성 observation은 지정한 환경과 입력만 대표합니다.
- 실제 provider·production 상태로 일반화하지 않습니다.

## 기준 시각

시나리오 검토 기준은 `2026-08-09T00:00:00Z`입니다. 그 이후 상태는 알 수 없습니다.
