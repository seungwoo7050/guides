# 실습 02 — 자산, 신뢰 경계와 위협 모델

위협 모델은 공격 이름의 목록이 아니라 **보호할 상태, 행위자 능력, 경계를 넘는 흐름과 실패 결과**를 연결한 모델입니다.

## 초기 자료

- [`inputs/system-context.md`](inputs/system-context.md)
- [`inputs/asset-register.json`](inputs/asset-register.json)
- [`template/threat-model.md`](template/threat-model.md)

## 작업공간과 시작 상태

저장소 루트에서 다음을 실행합니다.

```sh
python3 scripts/new_workspace.py exercise 02-threat-model
```

작업 경로는 `exercises/02-threat-model/work/`입니다. 생성된 `threat-model.md`는 자산·흐름·위협 ID 한 건의 빈 틀만 제공하며, 입력의 자산을 자동으로 위협이나 severity로 판정하지 않습니다. `inputs/`의 합성 자료와 미완성 템플릿을 출발점으로 사용합니다.

## 상황

`BuildBoard`는 개발자가 source archive를 제출하면 build runner가 결과물을 만들고 artifact store에 올리는 합성 시스템입니다. build runner는 일시적이어야 하지만 package mirror와 artifact store에 접근할 수 있습니다.

## 작업

1. 사용자에게 보이는 기능과 보호할 보안 상태를 한 문장으로 정의합니다.
2. asset별 confidentiality·integrity·availability·accountability 목표를 작성합니다.
3. actor의 초기 capability와 얻을 수 있는 capability를 분리합니다.
4. data flow마다 source, destination, identity, validation, stored evidence를 기록합니다.
5. 최소 다섯 개의 threat statement를 다음 형식으로 작성합니다.

```text
[능력을 가진 행위자]가
[전제 조건]에서
[경계/흐름]을 이용해
[보호할 상태]를 [원하지 않는 상태]로 바꿀 수 있다.
관찰 가능한 결과는 [evidence]다.
```

6. 최소 하나의 다단계 attack path를 작성합니다.
7. 각 path의 choke point와 남는 우회 경로를 설명합니다.
8. assumption과 unknown을 따로 기록합니다.

각 상태의 업무·위험 소유자, 상태 정본 소유자, 경계의 enforcement owner와 관측 evidence의 custodian을 구분합니다. 한 팀 이름으로 모든 역할을 뭉뚱그리지 않습니다.

## 제한

- package format, network protocol과 container isolation 자체를 다시 설명하지 않습니다.
- “악성 사용자”, “injection 가능”처럼 capability와 상태 변화가 없는 표현을 사용하지 않습니다.
- 모든 threat를 같은 severity로 두지 않습니다.
- 로그가 있다는 사실을 탐지 가능성과 동일시하지 않습니다.

## 제출 evidence

- `work/threat-model.md`: 보호 상태, actor capability, trust boundary와 최소 다섯 threat를 연결한 모델
- flow별 source·destination·identity·validation owner·남는 evidence와 unknown
- 최소 한 개의 다단계 attack path와 단계별 capability 변화
- choke point 적용 전후에도 남는 우회 경로와 모델의 관측 한계

## 반드시 검토할 사례

| 종류 | 사례 | 기대하는 판단 |
|---|---|---|
| 정상 | 승인된 source가 job-scoped identity로 빌드되고 같은 job의 artifact만 기록 | 허용 상태와 이를 입증할 flow·identity·artifact evidence를 연결한다. |
| 경계 | credential이 유효하지만 다른 job 또는 유사한 artifact prefix에 사용됨 | 문자열 유사성이 아니라 job·owner 경계를 기준으로 capability 확대 여부를 분석한다. |
| 실패 | 제출 archive가 runner 경계를 넘어 credential 또는 다른 job artifact에 영향을 줌 | 각 단계의 새 capability, 깨진 불변식, 관측 가능한 결과와 남는 경로를 기록한다. |

## 완료 rubric

- [ ] asset이 기술 구성요소가 아니라 보호할 상태까지 포함합니다.
- [ ] identity와 credential의 전달 경로가 있습니다.
- [ ] trust boundary를 넘는 모든 흐름에 검증 주체가 있습니다.
- [ ] threat마다 precondition과 observable evidence가 있습니다.
- [ ] 공격 경로의 각 단계가 capability의 변화로 연결됩니다.
- [ ] choke point 하나를 막아도 남는 경로를 검토했습니다.
- [ ] 가정과 확인되지 않은 사실을 구분했습니다.

## 사람 검토와 자동화 한계

Reviewer는 “자산이 단순 component 목록을 넘어 보호할 상태를 표현하는가?”, “각 단계의 capability가 앞 단계 결과로 실제 생기는가?”, “enforcement owner와 evidence custodian이 혼동되지 않았는가?”, “choke point 뒤 우회 경로가 빠지지 않았는가?”를 질문합니다. 자동 검사는 ID·링크·필수 표의 형식은 확인할 수 있지만 threat의 현실성, severity, 모델 완전성을 인증하지 않습니다.
