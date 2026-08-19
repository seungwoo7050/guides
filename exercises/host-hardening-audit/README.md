# Host Hardening Audit

Declarative JSON snapshot을 읽어 Linux host의 SSH, Docker control plane, public network, time synchronization, disk alert, backup boundary를 감사하는 CLI다. 실제 host를 자동으로 변경하지 않으며, 각 finding에 evidence, remediation, safe operation order를 함께 반환한다.

## Usage

```sh
python host_audit.py examples/insecure.json
python host_audit.py --fail-on-findings examples/secure.json
```

`--fail-on-findings`를 사용하면 finding이 하나라도 있을 때 exit code `1`을 반환한다. Input schema가 잘못된 경우 CLI usage error로 종료한다.

## Finding coverage

- shared administrator SSH key
- password authentication과 direct root login
- unrestricted SSH source
- unprotected Docker TCP listener
- application container의 Docker socket mount
- non-administrator docker group membership
- unexpected public service port
- unreviewed IPv6 firewall
- disabled time synchronization
- missing disk alert threshold
- local-only backup

## Tests

```sh
python -m unittest discover -s tests -v
```

## Design decisions

Docker group과 Docker socket은 host root에 준하는 control boundary로 취급한다. Remediation만 제시하지 않고 safe order를 별도 field로 제공해 SSH lockout, automation interruption, backup promotion 실패처럼 변경 과정에서 발생할 수 있는 2차 장애를 드러낸다. Snapshot에 없는 runtime fact는 추측하지 않는다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Stable finding schema | `host_audit.py` |
| 2 | Snapshot input boundary | `host_audit.py` |
| 3 | User role and shared key normalization | `host_audit.py` |
| 4 | SSH access boundary | `host_audit.py` |
| 5 | Docker control plane boundary | `host_audit.py` |
| 6 | Network, time, and storage recovery boundary | `host_audit.py` |
| 7 | Deterministic JSON CLI projection | `host_audit.py` |
| 8 | Audit regression suite | `tests/test_host_audit.py` |

## Scope and limitations

Snapshot은 선언된 상태만 표현한다. Running process, effective firewall rules, current listeners, package vulnerability, filesystem ACL, kernel hardening을 직접 수집하지 않는다. 이 도구의 결과는 live inspection을 대체하지 않으며, snapshot 생성 책임은 caller에게 있다.
