# TLS Lifecycle

Local CA를 사용해 service certificate의 issue, renewal, hostname verification, expiry threshold, private-key permission, atomic current pointer 전환을 재현하는 shell CLI다.

## Usage

```sh
./tls-lifecycle.sh issue ./state api.local.test 30
./tls-lifecycle.sh verify ./state api.local.test 7
./tls-lifecycle.sh renew ./state api.local.test 90
```

`issue`와 `renew`는 `state/versions/` 아래에 새 key/certificate candidate를 만들고 chain, hostname, expiry, key mode를 검증한 뒤에만 `state/current` symlink를 원자적으로 교체한다. `state/server.key`와 `state/server.crt`는 current version을 가리키는 stable symlink다.

## Verification

```sh
./tests/test.sh
```

Test는 올바른 hostname 성공, hostname mismatch 거부, 최소 남은 기간 거부, renewal serial 변경, key mode `0600`, 이전 certificate version 보존을 검사한다.

## Design decisions

Certificate와 private key를 각각 current path로 `mv`하면 두 파일 사이에 inconsistent window가 생긴다. 이 프로젝트는 검증이 끝난 version directory 전체를 먼저 공개하고 하나의 `current` symlink만 교체한다. 실패한 candidate는 current state를 변경하지 않는다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | CLI input and hostname contract | `tls-lifecycle.sh` |
| 2 | Portable private-key mode check | `tls-lifecycle.sh` |
| 3 | Local CA ownership | `tls-lifecycle.sh` |
| 4 | Versioned certificate candidate | `tls-lifecycle.sh` |
| 5 | Candidate trust verification | `tls-lifecycle.sh` |
| 6 | Atomic current certificate publication | `tls-lifecycle.sh` |
| 7 | Lifecycle command dispatch | `tls-lifecycle.sh` |
| 8 | Lifecycle regression suite | `tests/test.sh` |

## Scope and limitations

Local CA는 lifecycle와 trust verification을 재현하기 위한 project-local asset이다. Public service certificate 발급, ACME challenge, external CA account, HSM, distributed renewal coordination은 제공하지 않는다. CA private key와 service key가 같은 host에 있으므로 실제 public PKI 운영 모델로 사용하면 안 된다.
