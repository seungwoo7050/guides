# OpenTofu state와 drift 실습

로컬 file resource 또는 폐기 가능한 sandbox provider를 사용해 configuration, state와 실제 resource의 차이를 관찰합니다. OpenTofu를 예로 들며 Terraform도 같은 핵심 경계를 관찰할 수 있습니다.

## 목표

- configuration과 state가 같은 것이 아님을 확인합니다.
- resource address와 외부 object identity를 구분합니다.
- plan이 현재 refresh 결과에 의존한다는 사실을 봅니다.
- out-of-band 변경과 drift를 탐지합니다.
- state move/import/remove가 실제 resource 수명과 어떻게 다른지 확인합니다.

## 안전 기준

- local file 또는 비용 없는 sandbox resource를 사용합니다.
- production backend와 credential을 사용하지 않습니다.
- state에는 민감 값이 포함될 수 있으므로 Git에 추가하지 않습니다.
- backend 변경 전 backup과 복원 경로를 확인합니다.

## 도구와 workspace 준비

OpenTofu 1.6 이상 또는 Terraform 1.5 이상 중 하나를 사용합니다. 예제는 built-in `terraform_data`만 사용하므로 provider credential과 cloud resource가 필요하지 않습니다.

```sh
if command -v tofu >/dev/null 2>&1; then IAC=tofu; elif command -v terraform >/dev/null 2>&1; then IAC=terraform; else echo 'SKIP: tofu/terraform unavailable'; exit 3; fi
"$IAC" version
test ! -e .workspace/iac-state
mkdir -p .workspace/iac-state
cp -R examples/optional-labs/iac/. .workspace/iac-state/
cd .workspace/iac-state
"$IAC" init -backend=false
"$IAC" fmt -check main.tf
"$IAC" plan -out=plan-v1.bin
"$IAC" apply plan-v1.bin
"$IAC" state list
"$IAC" show -json > show-v1.json
```

`show-v1.json`은 generated evidence이며 저장소 source가 아닙니다. JSON 안의 `external_id`, desired version과 observed file hash가 state에 어떻게 기록됐는지 확인합니다.

## Drift·stale plan·state migration

학습자 workspace의 관측 파일만 바꿔 configuration/state/actual의 차이를 만듭니다.

```sh
printf '%s\n' 'manual-v2' > observed.txt
"$IAC" plan -out=drift.bin
"$IAC" show drift.bin
"$IAC" plan -out=stale.bin
printf '%s\n' 'manual-v3' > observed.txt
(
  set +e
  "$IAC" apply stale.bin
  stale_status=$?
  set -e
  test "$stale_status" -ne 0
  printf 'EXPECTED_FAILURE stale-plan exit=%s\n' "$stale_status"
)
"$IAC" plan -out=fresh.bin
"$IAC" apply fresh.bin
"$IAC" plan -detailed-exitcode
```

`stale.bin`은 plan 뒤 입력 파일이 달라졌으므로 적용에 실패해야 합니다. Terraform 1.5.7의 built-in provider에서는 `Provider produced inconsistent final plan`과 nonzero exit가 관찰됩니다. 도구가 stale plan을 성공시킨다면 예상 밖 결과로 표시하고 다음 단계를 진행하지 않습니다. 실패를 확인한 뒤 fresh plan을 새로 만들고 적용하며, 마지막 `-detailed-exitcode`가 `0`인지 확인합니다. 이 결과와 state를 보고 plan freshness, 자동 되돌림 여부와 사람 승인 조건을 기록합니다. 다음으로 versioned configuration과 `moved` block을 사용해 address migration을 수행합니다.

```sh
cp main-v2.tf.example main.tf
"$IAC" fmt -check main.tf
"$IAC" plan -out=migration.bin
"$IAC" apply migration.bin
"$IAC" state list
"$IAC" state pull > state-backup.json
"$IAC" state rm terraform_data.environment_state
"$IAC" plan
```

`state rm` 뒤 실제 관측 파일은 남지만 state mapping이 사라지는 점을 확인합니다. 먼저 저장한 `state-backup.json`과 migration evidence 없이 shared backend에서 이 명령을 실행하지 않습니다.

## 관측 질문

- State는 desired state입니까, observed mapping입니까?
- State lock이 없을 때 동시에 apply하면 어떤 race가 생깁니까?
- Drift를 자동 수정해야 합니까, 조사 후 승인해야 합니까?
- Resource를 rename할 때 replace가 발생하면 어떤 data와 endpoint가 영향을 받습니까?
- State만 제거하면 실제 resource와 비용은 어떻게 됩니까?

## Evidence

- configuration revision
- plan identity와 생성 시점
- apply 결과
- state resource address와 external ID
- drift 전후 plan
- migration 명령과 backup
- destroy/cleanup 결과

## Cleanup

state mapping을 제거했다면 configuration을 다시 import할 일반 방법이 없는 합성 resource이므로 workspace 전체를 폐기하는 것이 복구입니다. state를 제거하지 않았다면 먼저 destroy 결과를 확인합니다.

```sh
"$IAC" destroy -auto-approve
cd ../..
test -d .workspace/iac-state
```

실습 뒤 `.terraform`, `.tofu`, state, plan, backup과 관측 파일은 `.workspace/iac-state` 안에만 있어야 합니다. evidence를 보존한 뒤 학습자가 이 디렉터리를 명시적으로 삭제합니다. 도구가 없다면 `python3 examples/optional-labs/check_profiles.py`의 `iac/normal-state`와 `iac/out-of-band-drift`만 확인하고 실제 locking·plan freshness·state command를 관찰하지 못했다고 기록합니다.
