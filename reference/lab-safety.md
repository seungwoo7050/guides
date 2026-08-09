# 실습 안전·정리 계약

이 저장소의 필수 자동 경로는 Python 표준 라이브러리로 실행하는 fixture 분석과 in-memory 결정적 simulation입니다. root 권한, Docker daemon, 실제 network interface, 다른 process, 실제 disk fault 또는 cloud account를 사용하지 않습니다.

문서에서 production·staging fault injection을 설명하더라도 해당 명령을 현재 저장소가 자동 실행하거나 실행 권한을 부여하는 것은 아닙니다.

## 필수 경로가 만드는 상태

| 명령 | 생성·변경 가능한 상태 | 만들지 않는 것 |
|---|---|---|
| `make prepare` | `.guide/distributed-systems/prepared.json` | package 설치, network 요청, 추적 source 변경 |
| `make check` | stdout 검사 결과; bytecode는 비활성화 | host network·process·disk fault |
| `make verify` | 저장소 밖 `VERIFY_LOG`, 저장소 밖 임시 copy·Python cache | Docker·VM·cloud resource, learner solution 채점 |
| `./scripts/new-capstone-workspace.sh` | 기본값 `.workspace/replicated-kv` | 기존 target 덮어쓰기 |
| `make clean` | `.guide/distributed-systems/` 제거 | `.workspace/` learner source 또는 다른 cache 제거 |

`make clean`은 learner source와 그 안의 cache를 모두 건드리지 않습니다. cache를 제출 evidence로 사용하지 않으며, 필요하면 정확한 경로를 확인한 뒤 사람이 별도로 정리합니다.

## 작업 공간 보존

capstone 작업 공간은 다음 명령으로 한 번만 만듭니다.

```sh
./scripts/new-capstone-workspace.sh
```

기본 target이 이미 존재하면 helper는 중단합니다. 기존 workspace를 갱신하려고 삭제하거나 다시 복사하지 않습니다. 새 starter와 비교하려면 별도 target을 명시합니다.

```sh
./scripts/new-capstone-workspace.sh .workspace/replicated-kv-new
```

검사할 learner 구현은 반드시 `CAPSTONE_ROOT`로 지정합니다.

```sh
CAPSTONE_ROOT="$PWD/.workspace/replicated-kv" \
  python3 -m unittest discover -s capstone/tests -v
```

환경 변수를 생략하면 canonical starter를 검사합니다. 이를 learner 구현 통과 근거로 기록하지 않습니다.

## 로그와 trace 보호

- `VERIFY_LOG`는 저장소 밖 절대 경로를 사용합니다.
- trace에는 credential, token, cookie, 실제 사용자 data와 production payload를 넣지 않습니다.
- source·config identity는 commit·digest로 기록하고 환경 변수 전체를 dump하지 않습니다.
- 실패 trace를 정리하기 전에 최소 counterexample와 report의 digest를 확정합니다.
- 공개 issue나 저장소에 production log·pcap·snapshot을 첨부하지 않습니다.

[trace schema](trace-schema.md)의 run manifest와 data safety 규칙을 함께 적용합니다.

## 실제 fault adapter로 확장할 때

`tc`, `iptables`, network namespace, process signal, filesystem mount, disk pressure, Docker·VM과 cloud resource는 이 저장소의 필수 실습이 아닙니다. 별도 adapter를 만들 때는 다음 조건을 모두 먼저 충족합니다.

1. 개인 disposable VM 또는 run별 전용 container처럼 명확한 격리 경계를 사용합니다.
2. host 기본 route, VPN, SSH 경로, 공유 firewall와 production process를 target으로 삼지 않습니다.
3. 실행별 고유 resource ID와 소유 label을 사용합니다.
4. CPU·memory·disk·시간·요청량과 비용 상한을 고정합니다.
5. fault 적용 전 baseline과 독립적인 실제 적용 evidence를 수집합니다.
6. abort condition, signal·실패 cleanup과 수동 recovery를 문서화합니다.
7. 자신이 만든 resource만 정리하고 이름이 비슷한 기존 resource를 삭제하지 않습니다.
8. cleanup 실패를 protocol 결과와 분리해 보고합니다.

root 또는 cloud 권한이 없으면 deterministic simulator 경로를 사용합니다. 이 대체 경로는 protocol event ordering과 state invariant를 재현하지만 실제 kernel routing, scheduler, socket, filesystem flush, clock drift와 provider control plane을 검증하지 않습니다.

## 외부 비용과 서비스

정식 준비·검증·capstone core에는 유료 service나 외부 account가 필요하지 않습니다. cloud 또는 managed database 실험을 추가하더라도 이 가이드의 완료 조건으로 만들지 않으며, 명시적인 별도 승인 없이 resource를 생성하지 않습니다.

## 중단·복구 점검표

결정적 로컬 경로가 중단되면 다음 순서로 확인합니다.

```sh
git status --short
find .guide -maxdepth 3 -type f -print 2>/dev/null
find .workspace -maxdepth 2 -type d -print 2>/dev/null
```

- 추적 source가 바뀌었다면 자동 정리로 되돌리지 말고 diff와 변경 주체를 먼저 확인합니다.
- 준비 marker만 다시 만들려면 `make prepare`를 재실행합니다.
- 준비 marker만 정리하려면 `make clean`을 사용합니다. Python cache는 이 명령의 소유 범위가 아닙니다.
- learner workspace를 삭제해야 한다면 target과 backup을 사람이 확인한 뒤 별도 작업으로 수행합니다. 이 저장소의 자동 정리 명령은 learner workspace 삭제를 맡지 않습니다.

## 자동 검증의 한계

가이드 검증 통과는 다음을 증명하지 않습니다.

- learner capstone의 전체 protocol 완성
- 모든 message ordering과 crash point의 탐색
- 실제 network partition·leader process 교체·disk durability
- performance, availability 또는 production recovery 목표
- 사람 검토가 필요한 liveness 가정과 membership·sharding 설계의 타당성

자동 결과에는 실제 실행한 검사와 bounded scope를 기록하고, 나머지는 [완료 근거 루브릭](completion-evidence-rubric.md)의 사람 검토 항목으로 남깁니다.
