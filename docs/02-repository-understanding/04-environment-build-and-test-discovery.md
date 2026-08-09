# 환경, build와 test 발견

## 목표

에이전트가 저장소에 들어오자마자 임의 command나 dependency install을 실행하지 않고, 프로젝트가 선언한 실행·검증 계약을 복원합니다.

## 발견할 항목

```text
필요 runtime과 version
package manager와 lockfile
workspace·module·target
build command
test command
lint·format·type-check command
code generation
service·database·container 의존성
환경 변수와 secret 요구
CI에서만 실행되는 gate
platform 제약
```

## 근거 우선순위

일반적인 조사 순서는 다음과 같습니다.

1. repository instruction과 contributing 문서
2. build manifest와 lockfile
3. Makefile·task runner·package script
4. CI workflow
5. test configuration
6. container/devcontainer·toolchain file
7. 최근 성공한 공식 명령의 기록

README의 오래된 예제와 현재 CI가 다르면 충돌로 표시하고 실제 manifest와 maintainer policy를 함께 검토합니다.

## EnvironmentManifest

```text
runtime_requirements[]
package_manager
lockfiles[]
workspaces[]
commands[]
services[]
required_env[]
optional_env[]
network_requirements
cache_paths[]
generated_paths[]
source_evidence[]
confidence
```

command는 자유 문자열 한 개가 아니라 목적과 effect를 가집니다.

```text
command_id
type: build | test | lint | format | generate | run
argv
cwd
env_policy
timeout_profile
network_policy
expected_artifacts
mutates_workspace
source
```

## dependency 준비

dependency 설치는 code execution과 network effect를 포함할 수 있습니다.

- lockfile을 사용합니다.
- script 실행 여부를 확인합니다.
- package source와 registry를 제한합니다.
- cache와 workspace를 분리합니다.
- install 전후 file change를 측정합니다.
- production secret을 전달하지 않습니다.
- install 실패를 코드 실패와 구분합니다.

가능하면 미리 준비된 sandbox image나 project-specific environment를 사용합니다.

## 테스트 범위 발견

에이전트는 다음 레벨을 구분합니다.

```text
재현 command
관련 단위 test
관련 package/module test
lint·type check
전체 test suite
integration·e2e
release verification
```

개발 중에는 좁은 검사를 먼저 실행하고 최종 완료에는 repository policy와 budget에 맞는 넓은 검사를 사용합니다.

## 환경 결함

다음은 코드 결함과 다릅니다.

- runtime version 불일치
- missing tool
- dependency registry 실패
- unavailable service
- architecture/platform mismatch
- stale generated artifact
- insufficient disk·memory
- permission·sandbox block

환경 결함을 코드 수정으로 우회하지 않습니다. 예를 들어 테스트가 DB에 연결하지 못한다고 production validation을 제거하면 안 됩니다.

## 실패 조건

- 모델이 추측한 `npm test`, `pytest`, `make test`를 근거 없이 실행합니다.
- lockfile을 무시하고 최신 dependency를 설치합니다.
- install script가 workspace와 home directory를 바꾸는지 기록하지 않습니다.
- CI-only secret이 없다는 이유로 test를 삭제합니다.
- format command가 전체 저장소를 바꿨는데 agent change로 보고합니다.

## 완료 조건

- fixture 저장소에서 build·test·lint·format command를 source evidence와 함께 manifest로 만듭니다.
- dependency 준비와 실제 task 실행을 다른 phase·permission으로 분리합니다.
- environment failure와 code/test failure를 다른 결과로 반환합니다.
- 최종 보고서에서 실행하지 못한 gate를 명확히 표시합니다.
