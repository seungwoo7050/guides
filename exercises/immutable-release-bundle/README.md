# Immutable Release Bundle

Deterministic application payload, version-pinned non-root Docker image, exact image digest release manifest, rollback compatibility, SBOM, provenance, registry retention, smoke paths를 하나의 release unit으로 묶는다.

## Files

- `app.py`: image가 실행하는 deterministic payload
- `Dockerfile`: explicit base version, OCI labels, non-root runtime, exec-form entrypoint
- `release.yaml`: deployment와 rollback에 사용하는 exact digest contract
- `validate_release.py`: Dockerfile과 manifest의 cross-file invariant validator

## Usage

```sh
python -m pip install -r requirements.txt
python validate_release.py .
python app.py
```

Image build 시 release metadata를 명시한다.

```sh
docker build \
  --build-arg VCS_REF=a1b2c3d4e5f60718293a4b5c6d7e8f9012345678 \
  --build-arg VERSION=1.4.2 \
  --build-arg BUILD_DATE=2026-08-17T02:00:00Z \
  -t notes:1.4.2 .
```

`release.yaml`의 digest는 실제 registry push 결과로 교체해야 한다. 포함된 값은 self-contained validation을 위한 synthetic digest다.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Design decisions

Tag는 사람이 읽는 display identity로만 유지하고 deployment identity는 digest로 고정한다. SBOM과 provenance가 다른 digest를 가리키면 공급망 evidence가 실제 배포 artifact를 설명하지 못하므로 validator가 이를 거부한다. Secret은 release에 필요한 versioned name만 기록하며 값은 image와 manifest에 포함하지 않는다.

## Implementation Order

| Order | Responsibility | Primary anchor |
| ---: | --- | --- |
| 1 | Deterministic application payload | `app.py` |
| 2 | Immutable image build identity | `Dockerfile` |
| 3 | Non-root runtime ownership | `Dockerfile` |
| 4 | Release identity and exact digest | `release.yaml` |
| 5 | Compatibility and rollback contract | `release.yaml` |
| 6 | Supply-chain evidence binding | `release.yaml` |
| 7 | Release bundle validation | `validate_release.py` |
| 8 | Validation regression suite | `tests/test_release.py` |

## Scope and limitations

이 프로젝트는 registry push, signature, 실제 SBOM/provenance 생성, vulnerability scan을 수행하지 않는다. Manifest validator는 evidence binding과 정책 형태를 검사할 뿐 registry에 artifact가 존재하는지 확인하지 않는다.
