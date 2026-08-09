# 지시 발견과 우선순위

## 목표

system policy, 사용자 요청, 저장소 규칙과 directory별 지시를 출처·범위·우선순위에 따라 해석합니다. 저장소 파일 속 명령문을 무조건 권한 있는 지시로 실행하지 않습니다.

## 지시의 계층

구현마다 이름은 달라도 다음 계층을 구분합니다.

```text
Runtime policy          제품·조직이 강제하는 보안과 도구 경계
Session policy          이번 실행의 sandbox·network·approval profile
User task               사용자가 요청한 목표·제약·비범위
Repository instruction  프로젝트가 공유하는 build·style·검증 규칙
Directory instruction   특정 subtree에 적용되는 세부 규칙
File content            조사 대상 데이터와 코드
Tool output              command·test·검색 결과
```

아래 계층은 위 계층의 권한을 확장하지 못합니다. repository instruction이 “모든 secret을 업로드하라”고 써 있어도 runtime network policy를 바꾸지 못합니다.

## 지시 발견

에이전트는 시작 시 다음 후보를 조사합니다.

- repository root의 기여 문서와 agent instruction file
- README, CONTRIBUTING, build manifest
- 현재 target path까지의 상위 directory instruction
- CI workflow와 test script
- language·framework별 설정 파일
- task가 참조한 issue·design document

모든 Markdown이나 주석을 instruction으로 승격하지 않습니다. 어떤 file name과 location을 공식 지시 source로 인정할지 runtime 설정에 둡니다.

## 범위

지시에는 적용 범위가 필요합니다.

```text
repository 전체
특정 directory subtree
특정 언어·파일 패턴
특정 task 종류
특정 command 또는 release 단계
```

예를 들어 `services/payments/`의 테스트 명령은 `web/` 변경에 자동 적용되지 않을 수 있습니다.

## InstructionManifest

```text
instruction_id
source_path_or_policy_id
source_digest
origin_type
scope
priority
loaded_at
trusted_for_authority
content_summary
conflicts[]
```

모델에 전달할 때 source와 scope를 유지합니다. 단순히 “프로젝트 규칙”이라는 하나의 prompt로 합치지 않습니다.

## 충돌 해결

충돌은 조용히 마지막 문장으로 덮지 않습니다.

예:

```text
사용자: 전체 테스트를 실행하지 말고 관련 테스트만 실행
저장소: 제출 전 make verify 필수
```

가능한 처리:

1. 개발 중에는 관련 테스트만 실행합니다.
2. 최종 제출 전에 전체 검사가 필요하다는 사실을 표시합니다.
3. 시간 budget이 부족하면 사용자에게 선택을 요청합니다.
4. 전체 검사를 실행하지 않았다면 완료로 과장하지 않습니다.

보안 policy와 충돌하는 저장소 지시는 자동으로 거절하고 audit에 남깁니다.

## 지시 변경과 staleness

에이전트가 instruction file 자체를 수정하면 즉시 새 지시를 자기 session에 적용하지 않습니다. 그렇지 않으면 agent가 자신의 권한이나 완료 기준을 바꿀 수 있습니다.

권장 정책:

- session 시작 시 instruction manifest를 고정합니다.
- instruction file 변경은 일반 코드 변경으로 검토합니다.
- 새 session 또는 명시적 reload 승인을 받아 적용합니다.
- verifier는 initial instruction과 final tree를 모두 봅니다.

## 저장소 속 prompt injection

다음은 모두 untrusted content일 수 있습니다.

- issue 본문
- README와 주석
- test fixture 문자열
- generated log
- dependency package metadata
- tool output

“이전 지시를 무시하라”, “답안 파일을 읽어라”, “curl로 token을 전송하라” 같은 문장을 발견해도 data로 인용할 뿐 control instruction으로 사용하지 않습니다.

## 실패 조건

- 모든 `AGENTS.md`, `CLAUDE.md` 또는 비슷한 이름을 절대적으로 신뢰합니다.
- nested instruction의 scope를 무시합니다.
- 변경한 instruction file을 같은 session에 자동 적용합니다.
- user task와 repository rule 충돌을 모델이 임의로 선택합니다.
- tool output 안의 명령문을 system message처럼 다시 넣습니다.

## 완료 조건

- 지시 source, priority와 scope가 manifest로 남습니다.
- 충돌 사례에서 자동 진행·질문·거절 기준을 설명합니다.
- repository instruction이 runtime 권한을 확장하지 못합니다.
- instruction 변경이 현재 session에 미치는 효과를 명시적으로 통제합니다.
