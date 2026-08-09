# Edit, patch와 diff engine

## 목표

모델이 제안한 여러 파일 변경을 stale state, 부분 적용, newline·encoding 손상 없이 준비·검토·적용·복구합니다.

## 편집은 두 단계로 나눈다

```text
PREPARE
현재 file identity를 기준으로 change proposal 생성

APPLY
precondition·permission·approval을 다시 검사하고 workspace에 effect 수행
```

모델이 patch text를 만들었다고 실제 file이 바뀌지 않습니다.

## 변경 표현

### Whole-file replacement

작은 file에는 단순하지만 unrelated content와 newline을 손상할 수 있습니다.

### Line patch

human review와 diff에 적합하지만 문맥 mismatch와 offset 문제가 있습니다.

### Structured edit

symbol·AST·JSON path·config key를 대상으로 합니다. language/tool 지원이 필요하지만 의도가 명확합니다.

### Generated transformation

formatter, codemod, migration tool을 실행합니다. 실제 변경 범위를 command receipt로 확인해야 합니다.

하나의 engine이 모든 방식을 숨기지 말고 edit kind를 기록합니다.

## PatchArtifact

```text
patch_id
repository_snapshot_id
base_change_set_id
operations[]
expected_before_digests
predicted_paths
created_by_model_request
created_at
approval_requirement
```

operation 예시:

```text
MODIFY path before_digest patch
CREATE path expected_absent content
DELETE path before_digest
RENAME from_path to_path before_digest
```

## multi-file 적용

다음 순서를 사용합니다.

1. 모든 target의 canonical path와 permission을 확인합니다.
2. 모든 before precondition을 검사합니다.
3. 임시 영역에 결과를 생성합니다.
4. parse·basic invariant를 검사합니다.
5. 적용 중 실패 시 복구할 journal을 준비합니다.
6. change set 단위로 반영합니다.
7. 실제 after digest와 diff를 receipt에 기록합니다.

filesystem이 원자적 multi-file transaction을 제공하지 않으므로 rollback 가능성과 crash recovery를 설계해야 합니다.

## conflict와 stale edit

before digest가 다르면 자동 fuzzy apply를 기본값으로 사용하지 않습니다.

```text
STALE_FILE
→ 현재 source 재읽기
→ 기존 제안의 의도와 새 code 비교
→ patch 재생성
```

fuzzy apply가 필요하면 어떤 hunk가 다른 위치에 적용됐는지 명시적 review를 요구합니다.

## formatter와 generator

patch 뒤 formatter가 추가 변경을 만들 수 있습니다.

- target path 범위를 제한합니다.
- formatter 전후 diff를 분리합니다.
- generated source의 정본을 확인합니다.
- 전체 repository format을 암묵적으로 실행하지 않습니다.
- formatter failure 뒤 partial change를 기록합니다.

## rollback

rollback은 `git reset --hard`와 동일하지 않습니다. session 시작 전 사용자 변경을 보존해야 합니다.

가능한 방법:

- agent change set의 inverse patch
- 별도 worktree 폐기
- copy-on-write snapshot 복구
- file별 before content artifact

rollback 후 digest와 Git status를 검증합니다.

## diff review

사용자에게 다음을 보여 줍니다.

- 변경 file 목록과 kind
- agent가 의도한 변경과 formatter/generated 변경 구분
- before/after 또는 unified diff
- binary·large diff 요약
- test와 연결되는 이유
- 삭제·rename·permission mode 변경

## 실패 조건

- 모델이 읽지 않은 최신 file에 patch를 적용합니다.
- 여러 file 중 일부만 바뀌고 session은 성공처럼 계속합니다.
- encoding과 executable bit를 잃습니다.
- formatter가 만든 광범위한 변경을 숨깁니다.
- rollback이 사용자 초기 변경까지 지웁니다.
- patch artifact와 실제 workspace diff가 다릅니다.

## 완료 조건

- create·modify·delete·rename을 precondition과 receipt로 표현합니다.
- stale patch와 partial apply를 별도 실패로 처리합니다.
- 여러 file 변경을 change set으로 검토하고 복구합니다.
- final diff가 session 시작 baseline과 정확히 비교됩니다.
