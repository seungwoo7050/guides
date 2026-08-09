# Report Worker Incident Runbook 발췌

## Trigger

- report generation error rate가 10분 동안 5%를 초과함
- worker queue age가 15분을 초과함
- security operations가 worker credential alert를 전달함

## Immediate action

1. 현재 `stable` tag를 이전 release tag로 되돌립니다.
2. worker deployment를 재시작합니다.
3. `/ready`와 synthetic report smoke를 확인합니다.
4. 문제가 계속되면 report queue 소비를 중지합니다.

## Credential action

- 의심 credential ID를 credential broker에서 revoke합니다.
- 새 worker deployment가 새 credential을 받았는지 확인합니다.

## Recovery complete

다음 조건을 모두 만족하면 recovery를 선언합니다.

- worker instance가 ready입니다.
- synthetic report smoke가 성공합니다.
- queue age가 감소합니다.
- error rate가 정상 범위로 돌아옵니다.

## 현재 문서에 없는 항목

이 목록은 source 자료의 누락을 명시하기 위한 것으로, 곧 finding 판정이라는 뜻은 아닙니다.

- runtime artifact digest 확인
- package resolution과 provenance 재검증
- object read scope review
- audit pipeline completeness 확인
- trusted rebuild 기준
- potentially affected data owner communication
