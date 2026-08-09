# 실습 04 — 위협에서 보안 요구사항과 검사로

“입력을 검증한다”, “최소 권한을 적용한다”는 방향이지 검증 가능한 요구사항이 아닙니다. 이 실습은 threat statement를 구현·테스트·운영 증거가 연결된 requirement로 바꿉니다.

## 초기 자료

- [`inputs/threats.json`](inputs/threats.json)
- [`inputs/current-controls.json`](inputs/current-controls.json)
- [`template/security-requirements.md`](template/security-requirements.md)

## 작업공간과 시작 상태

저장소 루트에서 다음을 실행합니다.

```sh
python3 scripts/new_workspace.py exercise 04-security-requirements
```

작업 경로는 `exercises/04-security-requirements/work/`입니다. 생성된 `security-requirements.md`는 `THR-001`과 `REQ-TODO`를 연결하는 미완성 한 행만 포함합니다. 입력 control은 현재 주장이지 요구사항 충족의 증거가 아니므로 모든 threat와 control을 다시 추적합니다.

## 작업

각 threat에 대해 최소 하나의 예방, 탐지 또는 복구 requirement를 작성합니다. 모든 위협에 세 종류가 모두 필요한 것은 아니지만, path 전체에는 세 기능이 모두 있어야 합니다.

좋은 requirement는 다음을 포함합니다.

```text
적용 대상
+ 허용할 상태
+ 거부할 상태
+ enforcement owner
+ failure behavior
+ test oracle
+ runtime evidence
+ 예외와 만료
```

정상·경계·실패 matrix를 만들고 최소 하나의 known-bad mutation을 설계합니다. 검사기는 구현 세부나 특정 오류 문자열보다 보안 상태를 판정해야 합니다.

여기서 최소 수정은 가장 작은 diff가 아니라, 정상 기능을 보존하면서 깨진 불변식을 **모든 적용 경로에서** 복원하는 최소 change set입니다. 같은 결정을 수행하는 우회 경로와 control 장애 시 동작도 검사 범위에 포함합니다.

## 대표 오답

- “안전한 library를 사용한다.”
- “민감 정보는 암호화한다.”
- “관리자만 접근한다.”
- “모든 이벤트를 로깅한다.”
- “비정상 요청을 AI로 탐지한다.”

어떤 자산, identity, 상태, 실패 결과와 증거인지 없으면 완료되지 않습니다.

## 제출 evidence

- `work/security-requirements.md`: threat↔requirement 양방향 추적표와 검증 가능한 요구사항
- 정상·경계·거부 사례, failure behavior와 독립 oracle을 담은 test matrix
- 최소 한 개의 known-bad mutation이 기대한 이유로 거부되는 증거
- runtime evidence의 source·custodian·retention과 예외의 owner·expiry·review trigger

## 반드시 검토할 사례

| 종류 | 사례 | 기대하는 판단 |
|---|---|---|
| 정상 | 올바른 owner와 job context의 요청이 허용되고 보호 상태가 보존됨 | 사용자 기능과 보안 상태를 함께 보는 oracle을 정의한다. |
| 경계 | owner prefix가 비슷하거나 credential이 만료 직전·직후인 요청 | 문자열·status code가 아니라 정확한 identity, 시간, resource 경계로 판정한다. |
| 실패 | enforcement가 누락되거나 장애 시 fail-open되어 다른 owner 상태를 변경함 | known-bad mutation으로 같은 위협 경로가 거부되지 않음을 검출한다. |

## 완료 rubric

- [ ] threat와 requirement ID가 양방향으로 추적됩니다.
- [ ] enforcement owner가 코드·gateway·identity provider 등으로 구체적입니다.
- [ ] control failure가 fail-open인지 fail-closed인지 정했습니다.
- [ ] 정상·경계·거부 사례가 있습니다.
- [ ] test oracle이 status code 하나에만 의존하지 않습니다.
- [ ] runtime evidence와 evidence retention이 있습니다.
- [ ] 예외에는 owner·근거·expiry·재검토 trigger가 있습니다.

## 사람 검토와 자동화 한계

Reviewer는 “요구사항이 어느 상태를 누가 강제하는지 말하는가?”, “oracle이 정상 기능과 보호 상태를 함께 보는가?”, “최소 수정이 우회 경로를 남기지 않는가?”, “예외 승인 주체와 만료가 실제 운영 절차에 연결되는가?”를 질문합니다. 자동 검사는 ID 추적과 필수 행의 존재는 확인할 수 있지만 요구사항의 충분성, oracle 독립성, 패치 최소성을 인증하지 않습니다.
