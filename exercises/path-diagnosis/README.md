# 계층별 경로 진단 실습

한 요청이 실패했을 때 화면에 보이는 마지막 오류만 보고 원인을 정하면 DNS, 경로, 이웃 해석, MTU, 전송, TLS와 HTTP 경계를 섞기 쉽습니다. 이 실습에서는 각 계층의 관찰을 정해진 순서로 기록하고, 마지막 성공 계층과 첫 실패 계층을 결정한 뒤 다음 검사를 제안하는 작은 진단기를 구현합니다.

실습은 실제 네트워크를 변경하지 않습니다. 결정적인 JSON fixture만 사용하므로 Linux 관리자 권한이나 외부 네트워크 없이 실행할 수 있습니다.

## 목표

계층별 관찰을 순서가 있는 trace로 검증하고 마지막 성공, 첫 실패, 구체적 진단 코드와 다음 검사를 과장 없이 도출합니다.

```text
skeleton/path_diagnosis/   수정하지 않는 미완성 시작점과 공개 계약
workspace/path_diagnosis/  생성 뒤 학습자가 수정하는 유일한 구현
reference/path_diagnosis/  기준 구현
broken/path_diagnosis/     검사 품질을 확인하는 의도적 오답
tests/                     세 구현에 공통인 동작 검사
fixtures/                  정상 경로와 계층별 실패 증거
```

## 권장 구현 순서

아래 번호는 `reference/path_diagnosis/` 프로젝트 전체의 학습 지향 권장 구현 순서입니다. 파일의 줄 순서나 실제 과거 작성 순서를 뜻하지 않습니다. 학습자는 같은 책임을 `workspace/`에 구현하고, 통과한 뒤에만 reference source의 annotation과 비교합니다.

| 번호 | 파일·symbol | 먼저 고정하는 책임 |
|---:|---|---|
| 1 | `model.py::RequestContext` | 요청 이름·port·transport·application 입력 계약 |
| 1-1 | `model.py::StageEvidence` | 한 계층의 status, observation과 구조화 facts |
| 1-2 | `model.py::Trace` | 일곱 단계 순서와 첫 실패 전후 progression invariant |
| 1-3 | `model.py::load_trace` | 파일·JSON·구조 오류의 공개 예외 정규화 |
| 2 | `diagnose.py::Diagnosis` | 자동화와 사람이 공유하는 결과 계약 |
| 2-1 | `diagnose.py::diagnose` | 첫 실패·마지막 성공과 classifier dispatch |
| 2-2 | `diagnose.py::render_text` | machine 결과와 일치하는 안정적 text 표현 |
| 2-3 | `diagnose.py::_classify_*` | 관찰 facts보다 구체적으로 과장하지 않는 계층별 정책 |
| 3 | `cli.py::build_parser` | trace 경로와 출력 형식 CLI 계약 |
| 3-1 | `cli.py::main` | 입력 오류, 출력 채널과 exit status 경계 |

먼저 저장소 루트에서 workspace를 한 번 만듭니다. 기존 workspace는 덮어쓰지 않습니다.

```sh
scripts/new-workspace.sh exercises/path-diagnosis
```

## 진단 단계

모든 trace는 다음 단계를 정확히 한 번씩 같은 순서로 기록합니다.

```text
dns
→ route
→ neighbor
→ path
→ transport
→ tls
→ http
```

각 단계의 상태는 다음 셋 중 하나입니다.

| 상태 | 의미 |
|---|---|
| `ok` | 해당 단계의 계약이 관찰한 범위에서 성립했습니다. |
| `failed` | 이 단계에서 처음으로 진행을 막는 실패 증거를 확인했습니다. |
| `not-run` | 앞선 실패 때문에 이 단계까지 도달하지 않았습니다. |

정상 trace는 모든 단계가 `ok`여야 합니다. 실패 trace는 `failed`가 정확히 하나이고, 그 뒤 단계는 모두 `not-run`이어야 합니다. `route`가 실패했는데 `tls`가 성공했다고 기록하는 trace처럼 계층 순서와 모순되는 입력은 `TraceFormatError`로 거부합니다.

## fixture가 담는 증거

| fixture | 첫 실패 | 진단 코드 |
|---|---|---|
| `healthy.json` | 없음 | `HEALTHY` |
| `dns-nxdomain.json` | DNS | `DNS_NAME_NOT_FOUND` |
| `route-missing.json` | route | `NO_ROUTE` |
| `neighbor-unresolved.json` | neighbor | `NEIGHBOR_UNRESOLVED` |
| `mtu-black-hole.json` | path | `MTU_BLACK_HOLE` |
| `transport-timeout.json` | transport | `TRANSPORT_TIMEOUT` |
| `tls-name-mismatch.json` | TLS | `TLS_NAME_MISMATCH` |
| `http-forbidden.json` | HTTP | `HTTP_FORBIDDEN` |

진단기는 fixture 안에 기대 진단 코드를 저장해 두고 그대로 반환하지 않습니다. `rcode`, 선택 route, neighbor 상태, 크기별 전달 결과, SYN 응답, 인증서 이름 일치와 HTTP 상태 같은 관찰값에서 결과를 도출해야 합니다.

## 구현 단계

### 1. 입력 계약과 상태 진행을 검증합니다

`workspace/path_diagnosis/model.py`에서 다음을 구현합니다.

- 요청 이름, 포트, 전송 방식과 응용 프로토콜을 검증합니다.
- 일곱 단계가 빠짐없이 올바른 순서인지 확인합니다.
- 상태가 `ok`, `failed`, `not-run` 가운데 하나인지 확인합니다.
- 첫 실패 전에는 `ok`, 첫 실패 뒤에는 `not-run`만 허용합니다.
- 관찰 설명과 구조화된 `facts`를 보존합니다.

잘못된 JSON 구문, 누락된 필드와 모순된 단계 진행은 모두 `TraceFormatError`로 변환합니다. 내부 `KeyError`나 `TypeError`를 그대로 노출하지 않습니다.

### 2. 첫 실패와 세부 원인을 분리합니다

`workspace/path_diagnosis/diagnose.py`에서 다음을 구현합니다.

```text
첫 실패 단계 결정
→ 그 직전의 마지막 성공 단계 결정
→ 단계별 facts에서 구체적 진단 코드 선택
→ 핵심 증거와 다음 검사 생성
```

예를 들어 `path` 단계가 실패했다는 사실만으로 MTU 문제를 확정하면 안 됩니다. 작은 패킷은 성공하고 큰 패킷은 실패하며 필요한 ICMP도 관찰되지 않았을 때 `MTU_BLACK_HOLE`로 분류합니다. 그 밖의 path 실패는 더 일반적인 `PATH_FAILURE`로 남겨야 합니다.

첫 두 단계를 구현한 시점에는 아직 CLI 전체 검사를 실행하지 않습니다. model과 diagnosis의 공개 계약만 먼저 확인합니다.

```sh
cd exercises/path-diagnosis
PYTHONPATH=workspace python3 -m unittest tests.test_model tests.test_diagnose -v
```

### 3. CLI 계약을 구현합니다

`workspace/path_diagnosis/cli.py`에서 다음 명령과 출력 경계를 구현합니다.

```sh
cd exercises/path-diagnosis
PYTHONPATH=workspace python3 -m path_diagnosis fixtures/healthy.json
PYTHONPATH=workspace python3 -m path_diagnosis fixtures/mtu-black-hole.json --format json
```

종료 상태는 다음과 같습니다.

```text
0  유효한 trace이며 모든 단계가 정상
1  유효한 trace이며 실패를 진단함
2  입력 파일·JSON·trace 계약이 잘못됨
```

텍스트 출력과 JSON 출력은 같은 진단 내용을 표현해야 합니다. 자동화에서는 JSON과 종료 상태를 사용하고, 사람이 조사할 때는 텍스트의 증거와 다음 검사를 사용합니다.

## 구현 중 검사

저장소 루트에서 학습자 구현 전체를 검사합니다.

```sh
make PATH_EXERCISE_IMPL=workspace path-diagnosis-check
```

검사를 모두 통과한 뒤에만 기준 구현의 책임 배치와 출력 계약을 비교합니다.

```sh
make PATH_EXERCISE_IMPL=reference path-diagnosis-check
diff -ru exercises/path-diagnosis/workspace exercises/path-diagnosis/reference
```

저장소 전체에서는 다음 두 검사가 추가로 실행됩니다.

```sh
python3 scripts/check_skeleton.py
python3 scripts/check_test_quality.py
```

첫 검사는 skeleton이 import 오류가 아니라 의도한 `NotImplementedError`에서 실패하는지 확인합니다. 두 번째 검사는 모든 요청을 정상으로 분류하는 `broken` 구현이 공개 검사에 의해 거부되는지 확인합니다.

## 완료 기준

다음 조건을 모두 만족하면 완료입니다.

- 모든 정상·실패 fixture의 진단 코드가 맞습니다.
- 마지막 성공 단계와 첫 실패 단계가 정확합니다.
- 계층 진행이 모순된 trace를 거부합니다.
- fixture에 존재하지 않는 일반 실패에도 단계별 fallback 코드를 반환합니다.
- CLI의 텍스트·JSON 출력과 종료 상태가 일치합니다.
- reference를 보지 않고 workspace 검사를 통과한 뒤 구현 차이를 비교합니다.

이 진단기는 실제 패킷 캡처나 운영체제 상태를 수집하지 않습니다. 입력 증거가 틀리거나 캡처 위치가 불명확하면 결과도 틀릴 수 있습니다. 자동 분류 결과는 조사 시작점이며, 실제 변경 전에는 원본 명령 출력과 수집 위치를 다시 확인해야 합니다.

## 자기 설명

- 마지막 성공과 첫 실패를 하나의 원인 이름보다 먼저 고정해야 하는 이유는 무엇인가요?
- 큰 packet만 실패한다는 사실만으로 MTU black hole을 확정할 수 없는 이유는 무엇인가요?
- 유효한 실패 trace와 형식 자체가 모순된 trace의 종료 상태가 달라야 하는 이유는 무엇인가요?

## 검증

```sh
make PATH_EXERCISE_IMPL=workspace path-diagnosis-check
python3 scripts/check_skeleton.py
python3 scripts/check_test_quality.py
```

학습자 workspace와 기준 구현은 통과하고 skeleton과 알려진 오답은 의도한 계약에서 실패해야 합니다. 기준 구현 검사는 workspace 통과 뒤 비교 단계 또는 저장소 전체 `make reference-check`에서 실행합니다.
