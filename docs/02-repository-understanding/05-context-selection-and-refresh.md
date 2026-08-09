# Context 선택과 갱신

## 목표

저장소 조사 결과 중 현재 행동에 필요한 근거만 모델에 전달하고, 파일 변경·명령 실행·새 실패가 발생할 때 context를 갱신합니다.

## context는 작업 가설을 지원해야 한다

많이 읽는 것이 목표가 아닙니다. 각 context item은 다음 질문 중 하나에 답해야 합니다.

- 문제가 어디에서 재현됩니까?
- 상태 또는 값이 어디에서 만들어집니까?
- invariant를 누가 소유합니까?
- 어떤 test가 현재 동작을 규정합니까?
- 변경이 영향을 줄 call site는 어디입니까?
- 어떤 build·style 규칙을 따라야 합니까?

답하지 못하는 item은 우선순위를 낮춥니다.

## context packet

한 model turn에 전달하는 packet 예시:

```text
Task summary
Applicable instructions
Current phase and budget
Confirmed facts
Open hypotheses
Selected source excerpts
Recent tool receipts
Current diff summary
Allowed actions
Expected response contract
```

전체 transcript와 모든 command output을 매번 다시 보내지 않습니다.

## source excerpt 원칙

- 함수 중간만 잘라 invariant의 caller·return contract를 잃지 않습니다.
- line number와 file digest를 포함합니다.
- 생략 부분을 명시합니다.
- 관련 test와 production code를 함께 제공합니다.
- 같은 이름의 다른 symbol을 구분합니다.
- binary·generated·vendored content는 필요성이 명확할 때만 포함합니다.

## 변경 뒤 refresh

파일을 수정하면 다음을 수행합니다.

1. before digest와 after digest를 receipt에 기록합니다.
2. 수정한 file의 이전 excerpt를 stale 처리합니다.
3. formatter나 generator가 추가로 바꾼 file을 발견합니다.
4. symbol·reference·test 영향 범위를 다시 조사합니다.
5. 현재 plan과 acceptance가 여전히 맞는지 확인합니다.
6. 다음 model call에는 변경 후 source를 사용합니다.

## command 뒤 refresh

새 test failure는 단순 문자열이 아니라 새로운 evidence입니다.

- failing target·test·file·line
- exit status·signal·timeout
- first causal error와 후속 noise
- generated artifact 또는 workspace change
- environment manifest 변경

실패가 현재 가설을 반증하면 plan을 갱신하고 관련 context를 교체합니다.

## summary와 원문

요약은 context 절약에 유용하지만 다음 원문 identity를 유지합니다.

```text
summary_id
source_item_ids[]
source_digests[]
created_by
summary_schema_version
known_omissions
```

중요한 patch나 verifier 결과는 요약만으로 판정하지 않습니다.

## context pollution

다음은 pollution을 일으킵니다.

- 관련 없는 대형 log
- 중복 file excerpt
- 폐기된 계획을 현재 계획처럼 유지
- stale source와 수정 후 source 혼합
- hidden answer나 verifier implementation
- repository 속 공격 지시
- 모델이 만든 확인되지 않은 “사실”

working context에는 fact, hypothesis, decision, user instruction을 다른 type으로 보존합니다.

## 실패 조건

- 처음 읽은 file을 task 끝까지 다시 읽지 않습니다.
- diff만 보내고 주변 contract와 test를 제거합니다.
- 새 failure가 생겨도 원래 계획을 강제로 완료합니다.
- 모델 요약이 source reference를 잃습니다.
- current context에 초기 코드와 수정 코드가 구분 없이 함께 있습니다.

## 완료 조건

- action마다 필요한 context와 불필요한 context를 설명할 수 있습니다.
- edit·format·generate·branch change·test failure에 대한 invalidation 규칙이 있습니다.
- summary에서 원 source로 돌아갈 수 있습니다.
- context manifest로 특정 action이 어떤 repository revision을 보았는지 재현합니다.
