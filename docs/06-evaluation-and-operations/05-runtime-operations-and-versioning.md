# Runtime 운영과 versioning

## 목표

코딩 에이전트를 개인 CLI에서 반복 사용 가능한 소프트웨어로 운영할 때 session·artifact·tool·policy·checkpoint의 수명과 호환성을 관리합니다.

## version identity

한 session에는 다음 version을 고정합니다.

```text
runtime release
model provider·model snapshot·profile
model adapter
instruction bundle
context/compaction schema
tool catalog와 각 tool implementation
policy bundle
sandbox image/profile
repository environment image
verifier/evaluation schema
```

“최신 모델” 같은 mutable alias만 저장하지 않습니다.

## configuration 계층

```text
built-in safe default
organization policy
user configuration
repository configuration
session override
```

낮은 계층이 상위 deny를 해제하지 못합니다. effective configuration과 source를 session 시작 시 사용자에게 보여 줍니다.

## artifact 수명

- transcript
- event log
- checkpoint
- source excerpt와 command log
- patch·diff
- test artifact
- crash dump
- credential receipt

각 artifact에 retention, sensitivity, encryption, access와 deletion 정책을 둡니다. source 전체를 무기한 저장하지 않습니다.

## session concurrency

같은 repository에서 여러 session이 실행될 수 있습니다.

- worktree·branch·port·cache·container identity 분리
- shared dependency cache의 read/write 정책
- Git object database lock
- local service 충돌
- 사용자 승인 UI에서 session 구분
- resource quota와 fairness

multi-agent coordination을 하지 않아도 여러 독립 session의 운영 문제는 존재합니다.

## model·tool 장애

- provider rate limit과 outage
- stream 중단
- tool executable 변경
- package registry 장애
- sandbox unavailable
- disk/cache 고갈

fallback model이나 tool을 자동 선택할 때 contract와 quality가 같은지 확인합니다. 다른 model로 이어갈 경우 context와 action compatibility를 보존합니다.

## checkpoint migration

migration 단계:

1. old schema 읽기
2. 필수 identity와 digest 검증
3. 새 schema로 변환
4. unsupported field와 loss 기록
5. dry-run report
6. backup 보존
7. resume 가능성 판정

권한·effect ledger·approval을 잃는 migration은 자동 resume하면 안 됩니다.

## telemetry와 alert

- session success/failure category
- policy deny·approval rate
- tool error·schema error
- process leak·cleanup failure
- cost·latency·queue
- context overflow·compaction
- checkpoint/resume failure
- unexpected changed path
- network/secret alert

metric이 source나 secret을 label에 포함하지 않게 합니다.

## release artifact

코딩 에이전트 release에는 다음을 묶습니다.

```text
runtime binary/package
configuration schema
instruction bundle
built-in tool catalog
sandbox profile/image identity
migration tool
release notes
known limitations
regression report
rollback procedure
```

model provider의 external change도 compatibility event로 취급합니다.

## 사용자 데이터와 삭제

사용자는 session과 저장 artifact를 조회·export·삭제할 수 있어야 합니다. 삭제 요청이 backup과 audit retention에 미치는 예외를 명시합니다.

local CLI도 home directory에 어떤 파일을 남기는지 문서화합니다.

## 실패 조건

- session에 mutable model alias만 기록합니다.
- repository configuration이 조직 security deny를 덮습니다.
- 여러 session이 같은 worktree와 port를 공유합니다.
- checkpoint migration이 approval과 effect state를 누락합니다.
- telemetry label에 path·source·secret이 들어갑니다.
- runtime update 뒤 old session이 조용히 다른 policy로 재개됩니다.

## 완료 조건

- effective configuration과 모든 version identity를 session에 고정합니다.
- artifact retention과 삭제 정책을 정의합니다.
- concurrent session의 workspace·process·cache 충돌을 막습니다.
- runtime release에 regression evidence와 rollback 경로가 포함됩니다.
