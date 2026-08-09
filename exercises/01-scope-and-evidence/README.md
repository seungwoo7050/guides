# 실습 01 — 평가 범위와 증거

보안 평가는 취약점을 찾기 전에 **무엇을 어떤 권한으로 어디까지 확인할 수 있는지**를 고정해야 합니다. 이 실습에서는 서로 다른 팀이 작성한 짧은 시스템 설명과 보안 주장을 평가 계약으로 정리합니다.

## 초기 자료

- [`inputs/system-brief.md`](inputs/system-brief.md): 서비스와 제3자 경계
- [`inputs/claims.json`](inputs/claims.json): 확인되지 않은 보안 주장과 현재 근거
- [`template/assessment-charter.md`](template/assessment-charter.md): 작성 시작점

## 작업공간과 시작 상태

저장소 루트에서 다음을 실행합니다.

```sh
python3 scripts/new_workspace.py exercise 01-scope-and-evidence
```

작업 경로는 `exercises/01-scope-and-evidence/work/`입니다. 생성된 `assessment-charter.md`에는 `TODO`와 예시 claim 한 건만 있으며, 허가 상태나 결론은 채워져 있지 않습니다. 이 미완성 파일과 `inputs/`의 합성 입력만 사용하고 원본 `inputs/`·`template/`는 수정하지 않습니다.

## 상황

`NoteRelay`는 사용자가 문서를 업로드하면 변환 worker가 미리보기를 만들고 object storage에 저장하는 합성 서비스입니다. 제품 팀은 “내부 worker는 인터넷에 접근하지 못하며, 사용자별 문서는 서로 격리된다”고 주장합니다. 그러나 현재 자료는 설계 문서, 설정 일부와 운영자 설명이 섞여 있습니다.

## 작업

생성된 `work/assessment-charter.md`에 다음 내용을 작성합니다.

1. 평가 목적과 성공 조건
2. 명시적 허가 주체와 유효 기간
3. in-scope asset·identity·environment
4. out-of-scope 제3자와 production 경계
5. 허용 행동과 금지 행동
6. 요청 수·데이터 크기·시간 예산
7. stop condition과 연락 경로
8. 수집할 evidence와 보존·삭제 규칙
9. claim별 현재 상태
   - `verified`
   - `partially-supported`
   - `unsupported`
   - `contradicted`
   - `unknown`
10. claim을 확인하기 위한 최소 추가 증거
11. 허가의 버전과 `draft → approved → active → paused/revised → expired/revoked` 전이
12. scope·identity·시간·허용 행동이 달라질 때 평가를 멈추고 재승인하는 조건

## 제한

- 실제 object storage provider를 시험하지 않습니다.
- 계정 추측, 대량 요청, 실제 파일 업로드와 데이터 반출을 제안하지 않습니다.
- 구성 파일이 존재한다는 사실만으로 runtime 적용을 단정하지 않습니다.
- 운영자 설명은 유용한 단서지만 독립된 runtime evidence와 구분합니다.

## 반드시 거부할 결론

- “private subnet이므로 안전하다.”
- “문서에 egress deny가 적혀 있으므로 외부 통신이 불가능하다.”
- “UUID를 사용하므로 다른 사용자의 문서를 찾을 수 없다.”
- “로그가 없으므로 공격도 없었다.”
- “테스트 계정이므로 허가 없이 production과 같은 provider를 시험해도 된다.”

## 제출 evidence

- `work/assessment-charter.md`: 모든 `TODO`를 사실·가설·미확인으로 구분해 완성한 평가 계약
- 각 claim의 source, 관찰 시각 또는 evidence age, 현재 판정과 최소 추가 evidence
- 허가 version·상태·승인 주체·유효 기간과 상태를 바꾸는 사건
- stop condition이 발동했을 때 남길 기록, 연락, credential·fixture·log 정리 계획

## 반드시 검토할 사례

| 종류 | 사례 | 기대하는 판단 |
|---|---|---|
| 정상 | 승인된 합성 fixture를 유효 시간 안에 허용된 identity로 읽기 전용 검토 | `active` 허가와 예산 안에서 진행하고 evidence를 기록한다. |
| 경계 | 같은 asset이지만 identity, 시간대 또는 요청 행동 하나가 승인본과 달라짐 | 기존 승인을 확대 해석하지 않고 `paused/revised`로 전환해 재승인을 요구한다. |
| 실패 | 만료된 승인이나 운영자의 구두 설명만으로 제3자·production 검사를 진행하려 함 | 검사를 시작하지 않고 금지 범위와 필요한 authority를 기록한다. |

## 완료 rubric

- [ ] 허가와 기술적 scope를 구분했습니다.
- [ ] 제3자 asset을 명시적으로 제외했습니다.
- [ ] 각 claim에 source와 evidence age를 기록했습니다.
- [ ] 사실·가설·결론이 섞이지 않았습니다.
- [ ] stop condition이 관찰 가능한 상태로 작성됐습니다.
- [ ] 추가 증거가 최소 영향 원칙을 따릅니다.
- [ ] 평가 종료 뒤 credential·fixture·log 정리 방법이 있습니다.

## 사람 검토와 자동화 한계

Reviewer는 “이 주체가 실제로 이 범위를 승인할 authority가 있는가?”, “어떤 사건이 허가 version을 무효화하는가?”, “claim의 근거가 서로 독립적인가?”, “stop condition이 관찰 가능하고 즉시 실행 가능한가?”를 질문합니다. 자동 검사는 파일과 필수 섹션의 존재는 확인할 수 있지만, 승인 권한의 적법성, evidence의 독립성, 최소 영향 판단을 보장하지 않습니다.
