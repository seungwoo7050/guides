# 선택 확장

핵심 Capstone을 완성하기 전에 다음 기능을 추가하지 않습니다. 각 확장은 새로운 상태·권한·실패 모델이 생기므로 별도의 프로젝트 또는 후속 문서로 다룹니다.

## IDE integration

추가 책임:

- editor buffer와 disk file 차이
- unsaved change
- selection·cursor·diagnostic
- language server 연결
- inline diff와 undo
- 여러 workspace folder
- extension host 권한

CLI runtime을 IDE API에 직접 결합하지 않고 interface adapter로 연결합니다.

## Code intelligence와 LSP

- symbol·reference·rename
- incremental index
- compilation database
- stale index
- generated code
- language server crash

text search의 대체가 아니라 추가 evidence source입니다.

## Remote Git과 PR

- user/agent/service identity
- short-lived token
- remote ref race
- branch·commit·push receipt
- PR body와 review comment
- CI 결과와 merge gate
- force push·protected branch
- rollback과 audit

기본 local change set이 검증된 뒤에만 추가합니다.

## Hosted/cloud runner

- repository clone과 credential
- isolated image
- cache poisoning
- queue·scheduling·quota
- artifact upload
- task cancellation
- multi-tenant separation
- region·data retention
- environment reproducibility

이는 `platform-engineering`과 `web-infra`의 영역과 연결됩니다.

## MCP와 외부 tool

MCP 같은 protocol은 tool discovery와 invocation을 표준화할 수 있지만 다음을 대신하지 않습니다.

- server trust
- tool permission
- argument validation
- credential scope
- sandbox
- effect ledger
- verifier

외부 tool은 built-in tool과 같은 registry·policy·receipt contract로 mapping합니다.

## Multi-agent

가능한 역할:

```text
investigator
implementer
reviewer
test analyst
security reviewer
```

추가 문제:

- shared workspace race
- authority와 budget 분배
- conflicting plans
- message provenance
- duplicate effect
- consensus와 final owner

단일 agent의 상태와 tool contract가 안정된 뒤에만 확장합니다.

## Web·desktop control center

- 여러 session 표시
- streaming event
- approval inbox
- diff·artifact viewer
- notification
- auth·tenant
- resume와 handoff

이 UI가 runtime state의 정본이 되지 않게 합니다.

## Browser·GUI·visual task

- screenshot와 DOM/accessibility tree
- browser sandbox
- local dev server
- click/type effect
- visual regression
- credential·cookie
- image context budget

웹 프런트엔드 수정의 실제 검증에 유용하지만 별도 tool·evaluation이 필요합니다.

## Model routing과 specialist

- task/phase별 model 선택
- cost·latency·quality trade-off
- provider outage
- context compatibility
- privacy·data location
- result attribution

모델을 바꿔도 action·tool·verifier contract는 유지합니다.

## 자동 commit·merge·deploy

이 단계는 코딩 에이전트에서 소프트웨어 delivery agent로 범위를 넓힙니다.

필수 추가 사항:

- release authority
- CI/CD gate
- environment promotion
- rollback
- production secret
- incident response
- change window

`web-infra`, `distributed-services`, `platform-engineering`, `cybersecurity`와 함께 설계합니다.
