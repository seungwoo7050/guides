# 보안 증거 점검표

## 증거가 답해야 하는 질문

| 질문 | 예시 |
|---|---|
| 무엇을 관찰했는가? | 특정 identity가 특정 object에 대해 `allowed` 결정을 받음 |
| 어디서 관찰했는가? | authorization service audit event, integration fixture |
| 언제 관찰했는가? | event time과 ingest time |
| 어떤 조건이었는가? | synthetic user B, report A, policy version 17 |
| 누가 수집했는가? | evaluator identity 또는 automated verifier |
| 상태를 바꿨는가? | read-only query, disposable write fixture |
| 무엇을 증명하는가? | cross-owner access가 거부됐음 |
| 무엇을 증명하지 못하는가? | 다른 endpoint·policy version·production 상태 |
| 얼마나 오래 유효한가? | build·configuration·deployment가 바뀔 때까지 |

## 증거의 역할과 독립성

다음 목록은 절대적인 서열이나 필요한 개수 규칙이 아니라 서로 다른 실패 원인을 찾는 출발점입니다.

1. 외부 verifier가 직접 판정한 상태
2. 대상 경계에서 생성된 audit·policy decision
3. 실제 build·deployment·artifact identity
4. integration·system test 결과
5. source·configuration review
6. scanner·static candidate
7. 운영자 설명과 오래된 설계 문서

출처 수나 종류 수만으로 독립성이 생기지 않습니다. 같은 scanner output을 옮겨 적은 두 보고서는 하나의 근거이고, 한 권위 있는 immutable artifact가 좁은 사실을 확정하기에 충분할 수도 있습니다. 반대로 source에서 올바른 검사를 확인해도 runtime에 같은 build가 배포됐다는 주장은 별도의 배포 identity와 관찰이 필요합니다. 각 근거가 어떤 공통 생성 경로·가정·clock·collector에 의존하는지 기록합니다.

## 사실·가설·결론

- **사실:** 관찰 source와 시각이 있는 기술적 상태
- **가설:** 여러 사실을 설명할 수 있으나 아직 반증 가능한 주장
- **결론:** 필요한 전제와 대안 가설을 검토한 뒤 내린 판정
- **미확인:** 필요한 자료가 없거나 안전 범위에서 확인할 수 없는 상태

보고서 문장마다 어떤 종류인지 드러나야 합니다.

## 취약점 판정 전 확인

- [ ] 대상 version·build·deployment identity를 확인했습니다.
- [ ] 공격 전제가 현재 환경에서 성립합니다.
- [ ] 보안 상태의 실제 변화 또는 독립 oracle이 있습니다.
- [ ] 정상 동작·오설정·오탐과 구분했습니다.
- [ ] 영향의 상한과 미확인 범위를 기록했습니다.
- [ ] 결론에 필요한 독립 실패 원인을 검토했고, 추가 근거가 불필요하거나 안전하게 얻을 수 없다면 이유를 기록했습니다.
- [ ] evidence age와 재검토 trigger가 있습니다.
- [ ] 실제 데이터나 제3자를 추가로 시험하지 않았습니다.

## 수정 완료 전 확인

- [ ] root cause가 변경됐습니다.
- [ ] 원래 재현이 실패합니다.
- [ ] 정상 기능이 유지됩니다.
- [ ] 경계·encoding·identity·race 변형을 검사합니다.
- [ ] 유사 경로를 검색했습니다.
- [ ] credential·artifact·data cleanup이 완료됐습니다.
- [ ] runtime build와 policy version을 확인했습니다.
- [ ] detection과 runbook이 필요한 경우 함께 갱신됐습니다.
