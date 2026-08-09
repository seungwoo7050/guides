# 사람 검토 가이드

자동 검사는 파일·schema·링크와 합성 행동의 일부만 확인합니다. 이 문서는 저자 외 검토자가 단계 실습과 Capstone의 교육적 완성도를 판단할 때 사용할 공통 질문과 제출 증거를 정의합니다. 모든 질문에 같은 결론을 강제하지 않지만, 판단의 근거와 한계는 재검토 가능해야 합니다.

## 공통 증거 묶음

학습자는 다음 항목에서 실제로 사용한 파일 경로, ID, timestamp와 policy 또는 implementation version을 가리킵니다.

1. 실행 전 보호 상태와 불변식
2. 허가 version, actor, resource, 허용 행동, 중단·정리 조건
3. 관찰 사실, 수집 source, 수집 시각과 독립성·한계
4. 정상, 경계, 대표 실패 또는 known-bad 결과
5. 변경 전후 diff와 실행 뒤 보호 상태
6. 미확인 범위, 증거 유효 기간과 재검토 trigger

실제 credential·개인정보·production log와 외부 target 결과는 제출하지 않습니다. 필요한 경우 합성값으로 치환하고 치환 범위를 명시합니다.

## 단계 실습 검토

| 실습 | 제출 증거 | 핵심 사람 검토 질문 |
|---|---|---|
| 01 범위와 증거 | versioned charter, claim별 evidence·blind spot, stop·cleanup 기록 | 허가와 상태 정본 owner가 구분되는가? scope 변화가 재승인 사건으로 연결되는가? |
| 02 위협 모델 | asset·flow·boundary·threat ID, 정상·오용 경로, E2E 미확인 범위 | 독립 edge 근거를 전체 공격 경로 성공으로 과장하지 않았는가? 빠진 identity·recovery 경계는 없는가? |
| 03 취약점 검증 | candidate별 세 상태 축, proof 또는 반증, limitation·reopen trigger | root cause가 관찰에서 인과적으로 지지되는가? false positive·unknown에 원인과 수정을 지어내지 않았는가? |
| 04 보안 요구사항 | THR→REQ→test trace, 정상·경계·known-bad oracle | 요구사항이 구현 모양이 아니라 보호 상태를 정의하는가? N/A 통제의 근거와 우회 경로를 검토했는가? |
| 05 탐지 | event schema, positive·benign·duplicate·out-of-order fixture 결과 | precision·recall과 조사 가치 yield를 구분하는가? pipeline 누락·지연·privacy 비용을 기록했는가? |
| 06 사고 timeline | event·ingest·discovery time, 사실·가설·결정, containment·recovery evidence | 증거 보존과 containment를 구분했는가? trusted recovery source가 손상 경로와 독립적인가? |
| 07 격리 attack path | 취약 proof, patch diff, 정상·경계·known-bad 결과, deny event·alert, cleanup | patch가 가장 작은 문자열 변경이 아니라 모든 적용 경로의 불변식을 복원하는 최소 change set인가? prefix·identity·시간 우회가 남지 않았는가? |

자동 검사가 문장 품질, threat의 현실성, root cause의 인과성, 패치 최소성이나 탐지 운영 가치를 판정하지 않는다는 점을 각 실습 피드백에 남깁니다.

## Capstone 종료 능력 검토

### 1. 허가된 환경에서 공격 경로를 증명한다

- 허가 version과 synthetic target만 사용했는가?
- 각 edge의 precondition과 postcondition이 실제 관찰 ID에 연결되는가?
- 취약 구현 실행 전후의 state oracle이 보호 상태 변화를 보여 주는가?
- 한 edge의 성공과 전체 경로의 결론을 구분하고, stop·cleanup 증거를 남겼는가?

### 2. root cause와 최소 패치를 만든다

- root cause가 단순 누락 위치가 아니라 그 누락을 허용한 state·owner·enforcement 계약으로 설명되는가?
- patch diff가 정상 owner·job 접근을 보존하면서 foreign owner, cross-job, expired·revoked, missing context와 prefix 경계를 모두 복원하는가?
- 같은 invariant를 적용하는 경로를 조사했는가? 더 작은 변경이 거부된 이유와 남은 우회 가능성을 설명하는가?
- 구현 fingerprint와 실제 재실행 결과가 제출 evidence와 일치하는가?

### 3. 동일 공격의 차단과 탐지를 검증한다

- 취약 proof와 수정 뒤 deny가 같은 actor·resource·action·correlation을 재사용하는가?
- deny event가 actor/effective actor, credential, tenant/job, decision/reason, policy version을 조사 가능하게 남기는가?
- detector가 같은 시도를 positive로 찾고 benign·duplicate·out-of-order 입력을 구분하는가?
- 탐지되지 않는 경계, 예상 false positive와 pipeline failure가 잔여 위험에 반영되는가?

## Incident와 release 결정

- containment, eradication, recovery의 owner와 완료 oracle이 서로 다른가?
- backup·artifact·signer·builder·trust root가 순환 논리 없이 신뢰 재수립 근거가 되는가?
- 합성 post-release 검증 결과와 승인된 production validation **계획**을 구분하는가?
- 기술 reviewer의 권고와 조직이 지정한 risk acceptance authority의 결정을 구분하는가?
- `conditional-go`에서 monitoring을 예방 통제의 대체물로 사용하지 않았는가?
- 잔여 위험의 owner·authority·expiry·compensating control·monitoring·review trigger가 모두 있는가?

## 알려진 자동화 한계

- 기준 구현 통과는 다른 endpoint, concurrency, language runtime, production 배포의 안전성을 증명하지 않습니다.
- 격리 행동 checker는 학습자 Python module을 현재 process에 import하며 OS sandbox·egress 차단을 제공하지 않습니다. 검토한 자기 구현만 실행해야 합니다.
- ID trace 존재는 threat·severity·release 판단이 기술적으로 옳다는 뜻이 아닙니다.
- 합성 event의 탐지 결과는 실제 telemetry의 completeness·latency·retention·privacy를 보장하지 않습니다.
- source fingerprint는 준비 뒤 학습 source drift를 찾지만 Git history, 외부 링크의 최신성이나 저자 외 review를 대체하지 않습니다.

검토자는 위 질문별로 `충족 | 보완 필요 | 범위 밖`과 근거 경로를 기록합니다. 자동 검사 통과만으로 `stable`을 승인하지 않으며, 모든 종료 능력의 근거와 알려진 한계를 검토한 뒤 별도로 판단합니다.
