# Hidden test, cheating과 평가 타당성

## 목표

에이전트가 실제 문제를 일반적으로 해결한 것인지, test·grader·answer를 우회해 점수만 얻은 것인지 구분합니다. benchmark leakage와 평가 오염을 관리합니다.

## 왜 hidden 검사가 필요한가

public test만 있으면 다음 편법이 가능합니다.

- 특정 input에만 하드코딩
- assertion 삭제·skip
- test command를 no-op으로 변경
- exit code를 강제로 0
- fixture를 expected output에 맞게 수정
- grader path 탐색

hidden test는 이 행동을 줄이지만 완전한 방어는 아닙니다.

## cheating taxonomy

### Test tampering

- test 삭제·skip·조건 약화
- test runner 설정 변경
- collection 대상 제외

### Grader tampering

- verifier file 수정
- environment variable·path 조작
- output parser 공격

### Answer leakage

- gold patch·expected output 읽기
- benchmark metadata 검색
- network를 통한 known solution 획득

### Hardcoding

- 공개 사례만 통과
- repository·issue ID에 따라 special case

### Evidence fabrication

- test를 실행하지 않고 통과했다고 보고
- stdout·receipt 위조
- 다른 revision 결과 재사용

### Scope escape

- dependency·system package를 바꿔 repository test 우회
- host service나 hidden cache 사용

## 방어

- agent namespace와 verifier namespace 분리
- hidden path를 mount하지 않음
- network default deny
- final patch만 clean environment에 적용
- test count와 collection 확인
- forbidden file·config diff 검사
- runner·interpreter identity 확인
- command receipt와 artifact digest
- base commit 밖 artifact 제거
- known attack patch를 verifier에 실행

## 평가 타당성

좋은 benchmark는 무엇을 측정하는지 명확해야 합니다.

### 구성 타당성

과제가 repository discovery, code reasoning, edit와 test loop를 실제로 요구합니까?

### 내용 타당성

다양한 언어·bug type·repo 크기·tool requirement를 포함합니까?

### 생태 타당성

실제 개발과 비슷한 issue·code·test를 사용합니까?

### 재현성

동일 agent·model·environment에서 결과를 비교할 수 있습니까?

## leakage

공개 benchmark는 model training data에 포함될 수 있습니다.

대응:

- private/internal fixture
- 최근 또는 합성 task
- repository transformation
- solution-independent property
- contamination audit
- public benchmark와 별도 holdout

합성 과제도 지나치게 단순하거나 일정한 template이면 실제 능력을 측정하지 못합니다.

## hidden test의 한계

hidden test가 task description에 없는 동작을 강제하면 불공정합니다. acceptance와 public contract에서 합리적으로 추론 가능한 behavior를 검사해야 합니다.

- 구현 세부가 아니라 외부 contract
- 여러 올바른 patch 허용
- platform-dependent behavior 최소화
- flaky timing 제거
- resource budget 합리적 설정

## human review

다음은 executable verifier만으로 완전히 판단하기 어렵습니다.

- 변경 범위의 적절성
- 유지보수성
- repository style
- security trade-off
- error message 품질
- migration 설명

명확한 rubric과 blind review를 사용하고, behavior pass와 별도 metric으로 둡니다.

## 실패 조건

- hidden test가 expected implementation shape를 강제합니다.
- benchmark ID와 gold patch가 agent image에 남습니다.
- network가 열려 solution 검색을 허용합니다.
- test tampering을 behavior pass로 인정합니다.
- 모델 judge 하나가 모든 정답을 판정합니다.
- leakage 가능성을 무시하고 leaderboard 숫자를 일반 능력으로 해석합니다.

## 완료 조건

- cheating 유형별 known-bad patch와 trace를 만듭니다.
- verifier가 test/runner/grader 변경을 탐지합니다.
- hidden test가 task의 public contract와 연결됨을 설명합니다.
- public benchmark, private holdout과 local regression의 역할을 구분합니다.
