# Unix 시스템 관찰과 진단 가이드

Unix 사용자 공간에서 경로·파일 디스크립터·프로세스·권한·메모리·네트워크 엔드포인트·서비스 상태를 관찰하고, 증상을 근거로 실패 계층을 좁히는 가이드입니다.

이 저장소는 C로 POSIX 기능을 다시 구현하는 과정이 아닙니다. 터미널 화면에 나타난 결과를 다음 상태 모델과 연결하는 데 집중합니다.

```text
입력과 실행 문맥
→ 경로와 자원
→ 프로세스와 수명
→ 메모리와 네트워크 상태
→ 서비스 준비 상태
→ 가설·반증·복구 검증
```

## 시작

Overlay를 적용한 저장소 루트에서 먼저 준비 상태를 확인합니다.

```sh
./prepare.sh
```

`prepare.sh`는 source tree와 Git index를 변경하지 않고 구조·도구·fingerprint를 확인합니다. 저장소 전체를 검사하는 `./verify.sh`는 아래 학습 순서를 마친 뒤 실행합니다. 이 명령은 curriculum과 재현 시나리오를 검사하며 학습자의 `workspace/diagnoses.json`을 대신 채점하지 않습니다.

## 학습 순서

이 브랜치에는 별도의 관찰 예제가 없습니다. `lab.py`가 만드는 사례는 답안을 보여 주는 example이 아니라 학습자가 직접 조사하는 exercise fixture입니다. [로드맵](docs/00-roadmap.md)에서 범위와 안전 경계를 확인한 뒤 다음 순서로 문서와 사례를 함께 진행합니다. 표의 exercise 명령과 `workspace/`·`reference/` 경로는 `exercises/system-investigation`을 기준으로 합니다.

<!-- guide-contract:learning-map:start -->
| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 0 | [로드맵](docs/00-roadmap.md) | — | — | — | 범위·안전 규칙·종료 능력 확인 | 1번 문서 |
| 1 | [터미널, 프로세스와 커널](docs/01-user-space-model/01-terminal-process-and-kernel.md) | — | 사례 01·05의 선행 모델 | — | 문서의 완료 기준 | 2번 문서; reference는 아직 열지 않음 |
| 2 | [파일, 경로와 메타데이터](docs/01-user-space-model/02-files-paths-and-metadata.md) | — | `02-dangling-symlink` | `workspace/diagnoses.json`의 `cases.02-dangling-symlink` | [사례별 반복](exercises/system-investigation/README.md#사례별-반복) | 3번 문서 |
| 3 | [스트림, 파일 디스크립터와 파이프](docs/01-user-space-model/03-streams-file-descriptors-and-pipes.md) | — | `04-deleted-open-file` | `workspace/diagnoses.json`의 `cases.04-deleted-open-file` | [사례별 반복](exercises/system-investigation/README.md#사례별-반복) | 4번 문서 |
| 4 | [사용자, 권한과 환경](docs/01-user-space-model/04-users-permissions-and-environment.md) | — | `01-command-resolution` | `workspace/diagnoses.json`의 `cases.01-command-resolution` | [사례별 반복](exercises/system-investigation/README.md#사례별-반복) | 5번 문서 |
| 5 | [프로세스, 시그널과 작업 제어](docs/02-process-and-resource-observation/01-processes-signals-and-jobs.md) | — | `03-waiting-for-input` | `workspace/diagnoses.json`의 `cases.03-waiting-for-input` | [사례별 반복](exercises/system-investigation/README.md#사례별-반복) | 6번 문서 |
| 6 | [프로세스 메모리 관찰](docs/02-process-and-resource-observation/02-process-memory-observation.md) | — | `09-reserved-not-resident` | `workspace/diagnoses.json`의 `cases.09-reserved-not-resident` | [사례별 반복](exercises/system-investigation/README.md#사례별-반복) | 7번 문서 |
| 7 | [네트워크 엔드포인트와 연결 진단](docs/02-process-and-resource-observation/03-network-endpoints-and-diagnosis.md) | — | `06-address-family-mismatch` | `workspace/diagnoses.json`의 `cases.06-address-family-mismatch` | [사례별 반복](exercises/system-investigation/README.md#사례별-반복) | 8번 문서 |
| 8 | [서비스 감독, 로그와 준비 상태](docs/03-services-and-troubleshooting/01-service-supervision-logs-and-readiness.md) | — | `05-working-directory`, `07-running-not-ready`, `08-signal-not-forwarded` | `workspace/diagnoses.json`의 해당 세 사례 | 각 사례에 [같은 반복](exercises/system-investigation/README.md#사례별-반복) 적용 | 9번 문서 |
| 9 | [시스템 문제 진단](docs/03-services-and-troubleshooting/02-system-troubleshooting.md) | — | 아홉 사례의 가설·근거·수정·회귀 조건 통합 검토 | `workspace/diagnoses.json` 전체 | `./check.sh workspace`와 실제 출력의 semantic review | 그 뒤에만 `reference/diagnoses.json` 수동 비교 → `./check.sh all` → 저장소 루트의 `./verify.sh` → [선택 학습 지도](docs/00-roadmap.md#선택-학습-지도) |
<!-- guide-contract:learning-map:end -->

작업 공간은 한 번만 만듭니다.

```sh
cd exercises/system-investigation
./create-workspace.sh
```

기존 `workspace/`는 덮어쓰지 않습니다. 직접 수정하는 파일은 `workspace/diagnoses.json`뿐입니다. 각 사례에서는 `create → symptom → status → 읽기 전용 조사와 최소 복구 → destroy`를 반복하고 해당 사례의 진단 기록을 채웁니다.

아홉 사례를 마친 뒤 다음 순서를 지킵니다.

```sh
./check.sh workspace
```

`STRUCTURE PASS`는 자동 검사 가능한 enum, 명령 형태와 필드 계약만 통과했다는 뜻입니다. 실제 사례 출력과 `expected_evidence`·`regression_checks`의 인과 관계를 직접 검토한 뒤에만 `reference/diagnoses.json`을 열어 사례별로 비교합니다.

```sh
./check.sh reference
./check.sh all
cd ../..
./verify.sh
```

`./check.sh reference`, `./check.sh all`, 루트 `./verify.sh`는 repository-owned 기준 답안·미완성 시작점·오답 거부 능력·재현 시나리오를 검증합니다. learner workspace 검사는 첫 번째 `./check.sh workspace`와 수동 semantic review가 담당합니다.

## 안전 범위

- 관리자 권한을 요구하지 않습니다.
- 외부 주소를 사용하거나 scan하지 않습니다.
- 외부 Python package를 설치하지 않습니다.
- 사례는 지정한 작업 디렉터리와 loopback만 사용합니다.
- 사용자 `workspace/`는 준비·검증 과정에서 자동 삭제하지 않습니다.
- `sudo`, 광범위한 재귀 삭제, `chmod 777`, 첫 대응으로 사용하는 `kill -9`를 해결책으로 제시하지 않습니다.

macOS와 Linux는 같은 목적의 관찰 도구가 다를 수 있습니다. 출력 형식을 외우기보다 각 명령이 어떤 상태를 증명하는지 확인합니다.
