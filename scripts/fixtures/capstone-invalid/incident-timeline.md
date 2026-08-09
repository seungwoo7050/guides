# Meta Incident Timeline

## Incident 범위
검사기 false acceptance 한 건을 합성 사건으로 다룹니다.

## Timeline
FACT 10:00 invalid가 통과했습니다. HYPOTHESIS 10:01 source count 검사가 없습니다. DECISION 10:02 release를 중단합니다. ACTION 10:03 검사를 추가합니다. RESULT 10:04 invalid가 거부됩니다.

## 증거 보존
fixture와 종료 코드, error 출력을 임시 log에 보존합니다.

## Containment
잘못된 검사기 배포를 중단하고 이전 version을 유지합니다.

## Eradication
누락된 validation과 같은 schema 경로를 수정합니다.

## Recovery와 검증
valid·invalid·template meta-test가 예상대로 동작하는지 확인합니다.

## Communication
검사 한계와 수정 결과를 contributor에게 알립니다.

## 미확인과 후속 Owner
기술 판단 검증은 범위 밖이며 guide maintainer가 후속 검토합니다.
