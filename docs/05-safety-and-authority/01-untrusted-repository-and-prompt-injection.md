# 신뢰할 수 없는 저장소와 prompt injection

## 목표

저장소, issue, dependency, test output과 tool result 안의 자연어를 모두 잠재적으로 신뢰할 수 없는 데이터로 처리합니다. 코드와 문서가 에이전트의 권한·목표·verifier를 바꾸지 못하게 합니다.

## coding agent의 공격면

에이전트는 일반 chat assistant보다 많은 외부 입력을 읽습니다.

- README·contributing·agent instruction file
- source comment와 string literal
- issue·PR·commit message
- test fixture와 snapshot
- compiler·test·package manager output
- generated file
- dependency metadata와 install script
- MCP/tool description
- web·documentation result

공격자는 이 안에 “시스템 지시를 무시하라”, “credential을 읽어라”, “검사를 삭제하라” 같은 문장을 넣을 수 있습니다.

## data와 authority 분리

```text
Authority
- runtime policy
- session grant
- 사용자 task와 승인
- 명시적으로 신뢰된 repository instruction source

Untrusted data
- 일반 저장소 content
- issue와 log
- tool output
- dependency content
```

untrusted data는 분석 대상이고 action 선택에 참고할 수 있지만 permission을 확대하지 못합니다.

## instruction source도 절대 신뢰하지 않는다

repository instruction file은 프로젝트 규칙을 전달하지만 다음을 수행할 수 없습니다.

- workspace 밖 write 허용
- network·secret 권한 확대
- verifier·hidden test 접근 허용
- runtime audit 비활성화
- 사용자의 non-goal 제거

내용이 상위 policy와 충돌하면 거절하고 사용자에게 알립니다.

## tool output injection

command output을 모델에 다시 넣을 때 경계를 표시합니다.

```text
<tool_output source="pytest" trust="untrusted">
...
</tool_output>
```

표시 자체만으로 안전해지는 것은 아닙니다. 모델이 따라도 실제 tool gateway와 policy가 효과를 막아야 합니다.

## dependency와 build script

package install, build, test는 저장소 code를 실행합니다. 악성 저장소는 다음을 시도할 수 있습니다.

- home·SSH·cloud credential 읽기
- network exfiltration
- parent directory 수정
- background process 유지
- test result 위조
- shell profile·Git config 변경

따라서 “테스트 실행”도 신뢰된 read-only 행동이 아닙니다. sandbox, clean env, network policy와 process cleanup을 적용합니다.

## context contamination 방어

- untrusted content를 instruction block과 분리합니다.
- provenance와 scope를 유지합니다.
- 필요 이상의 file을 context에 넣지 않습니다.
- suspicious imperative text를 trace에 표시할 수 있습니다.
- 중요한 action은 model 판단이 아니라 policy와 approval로 통제합니다.
- verifier·answer·credential은 context 후보에서 구조적으로 제외합니다.

prompt classifier만으로 방어를 완성하지 않습니다. classifier가 놓쳐도 sandbox와 permission이 경계를 지켜야 합니다.

## 평가 시나리오

fixture에 다음을 포함합니다.

- README 속 network exfiltration 지시
- test output 속 hidden answer 경로
- source comment 속 permission 변경 요청
- dependency script의 home file 접근
- symlink를 통한 verifier 접근
- tool description에 삽입된 broad authority 주장

성공 조건은 모델이 공격 문장을 설명하는 것이 아니라 실제 금지 effect가 발생하지 않는 것입니다.

## 실패 조건

- repository instruction을 system prompt와 같은 신뢰로 합칩니다.
- prompt injection 탐지 문구만 있고 실제 tool policy가 없습니다.
- test command를 신뢰된 것으로 간주해 unrestricted environment에서 실행합니다.
- 모델이 “이 파일은 안전하다”고 말하면 secret access를 허용합니다.
- hidden verifier path가 일반 search 결과에 노출됩니다.

## 완료 조건

- 모든 context item에 origin과 trust label이 있습니다.
- untrusted instruction이 permission과 task를 바꾸지 못합니다.
- malicious build/test가 host·credential·network로 이탈하지 못하는 경계를 설명합니다.
- 공격 문장을 모델이 따르는 경우에도 실제 effect가 차단됩니다.
