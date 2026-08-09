# Sandbox, network, secret과 dependency

## 목표

모델과 policy가 실수해도 file·process·network·credential 경계를 실행 환경이 강제하도록 sandbox profile을 설계합니다.

## sandbox의 층

```text
Filesystem sandbox
Process/user isolation
Resource limits
Network policy
Credential boundary
Dependency/source policy
Artifact and verifier separation
```

container 하나를 쓴다는 사실만으로 모든 층이 해결되지 않습니다.

## filesystem

- repository snapshot은 필요에 따라 read-only base로 mount합니다.
- agent workspace만 write 가능하게 합니다.
- home, SSH, cloud config, host socket을 mount하지 않습니다.
- verifier와 hidden test는 agent namespace에서 보이지 않게 합니다.
- `/tmp`와 cache를 session별로 분리합니다.
- symlink·mount·file descriptor를 통한 escape를 고려합니다.
- Git object database를 공유할 때 write 범위를 검토합니다.

## process

- non-root principal
- privilege escalation 금지
- namespace 또는 OS sandbox
- process count·CPU·memory·file size 제한
- device access 제한
- host daemon socket 금지
- seccomp/system call profile 또는 platform equivalent
- process tree cleanup

sandbox 내부 root가 host root는 아니어도 mount와 socket이 잘못되면 위험합니다.

## network

기본 profile:

```text
external network deny
loopback 제한
DNS 기록
필요 destination allowlist
connection·byte budget
```

network를 허용해야 하는 경우를 분리합니다.

- model provider 호출은 runtime host가 수행하고 sandbox에서 분리
- package registry
- repository-defined local service
- documentation fetch
- remote Git operation

하나의 `network=true`로 모두 열지 않습니다.

## secret

- source tree의 `.env`를 자동 읽지 않습니다.
- credential broker가 command identity와 scope를 확인합니다.
- short-lived token을 file보다 pipe·fd·environment로 제한적으로 전달합니다.
- stdout/stderr와 trace에서 redaction합니다.
- 모델에게 secret value를 반환하지 않습니다.
- crash artifact와 core dump를 관리합니다.

secret을 redaction했다고 외부 전송이 안전해지는 것은 아닙니다. network policy가 우선입니다.

## dependency install

package manager는 임의 code 실행기가 될 수 있습니다.

- lockfile과 exact version
- trusted registry/mirror
- install script 실행 정책
- checksum/signature/provenance
- cache isolation
- dependency diff와 lockfile 변화
- network와 time budget
- native build toolchain

가능하면 task image를 사전 준비하고 session 중 install을 줄입니다.

## build와 test sandbox

저장소 code를 실행하므로 일반 read permission보다 강한 격리가 필요합니다.

- clean environment
- fake/non-production service
- 제한된 test data
- no host credential
- bounded network
- ephemeral database
- artifact path 제한
- timeout과 process cleanup

## sandbox profile 예시

```text
READ_ONLY_ANALYSIS
WORKSPACE_EDIT_NO_EXEC
WORKSPACE_EXEC_NO_NETWORK
DEPENDENCY_PREP_ALLOWED_REGISTRY
LOCAL_SERVICE_TEST
DISPOSABLE_FULL_ACCESS
```

각 profile의 writable roots, executable policy, network, credential와 resource limit을 문서화합니다.

## 실패 조건

- Docker socket이나 SSH agent를 편의상 mount합니다.
- test 실행에 사용자 전체 환경과 cloud credential을 전달합니다.
- dependency install과 test를 같은 permission으로 처리합니다.
- network allow가 destination·byte·time 제한 없이 열립니다.
- hidden verifier가 workspace 안에 존재합니다.
- sandbox가 실패하면 host에서 자동 재실행합니다.

## 완료 조건

- file, process, network, secret과 dependency를 별도 경계로 설계합니다.
- 최소 세 개의 sandbox profile과 전환 조건이 있습니다.
- malicious repository가 host credential과 verifier에 접근하지 못합니다.
- sandbox failure가 권한 확대가 아니라 명시적 block으로 끝납니다.
