# 웹 인프라 기초와 공개 운영 가이드

브라우저 또는 `curl`의 요청이 공개 DNS와 TLS, Nginx, 애플리케이션 런타임, 데이터베이스를 거쳐 응답으로 돌아오기까지의 경계를 직접 구성하고 검증합니다. 로컬 Docker Compose 스택에서 시작해, 하나의 Linux 호스트에 공개 서비스를 배포하고 관찰·백업·복원·rollback·사고 대응까지 수행할 수 있는 운영 기준선으로 확장합니다.

처음에는 [`docs/00-roadmap.md`](docs/00-roadmap.md)를 읽으세요. 대상 독자, 선행 환경, 두 학습 구간, 실습 방식과 과정 종료 조건을 한 문서에서 확인할 수 있습니다.

## 과정이 만드는 능력

과정을 마치면 다음 작업을 수행할 수 있어야 합니다.

- HTTP 요청, 프로세스, 포트와 프로토콜 실패를 구분합니다.
- Docker image·container, Compose network·volume과 상태 수명을 구분합니다.
- Nginx, TLS, PHP-FPM과 MariaDB로 작은 다중 서비스 스택을 구성합니다.
- 데이터베이스와 애플리케이션 초기화를 반복 실행 가능한 계약으로 만듭니다.
- 로그, 상태 검사, DNS, 연결, 권한과 저장 상태를 이용해 장애 계층을 좁힙니다.
- 공개 서비스의 운영 목표, 신뢰 경계, RPO·RTO와 수용할 잔여 위험을 선언합니다.
- Linux 호스트, SSH, 방화벽, Docker daemon 권한과 운영 경로를 점검합니다.
- DNS와 ACME 인증서의 발급·갱신·reload·만료 감시 수명을 검증합니다.
- exact image digest, SBOM, provenance와 호환 범위를 release manifest로 묶습니다.
- 배포를 잠그고 preflight·migration·readiness·외부 smoke 뒤에만 release를 확정합니다.
- 비밀값을 versioned 상태로 회전하고 실패한 후보가 current가 되지 않게 합니다.
- 외부 probe, 구조화 로그, 안정적인 metric과 경보를 운영 계약에 연결합니다.
- 일관된 backup을 호스트 밖에 보관하고 빈 환경에 안전하게 복원합니다.
- 용량 고갈과 지원 종료 위험을 증거·담당자·기한·검증·rollback으로 연결합니다.
- 사고 중 사실과 가설을 분리하고, 증거를 지우지 않는 가역적 완화를 수행합니다.
- 기존 호스트 없이 exact release·외부 backup·versioned secret으로 서비스를 재구축합니다.

## 범위

공개 운영 구간의 기준선은 다음과 같습니다.

```text
하나의 Linux 호스트
+ 하나의 공개 도메인
+ Docker Compose 기반 서비스
+ 공인 TLS와 자동 갱신
+ registry의 immutable image digest
+ CI/CD와 rollback
+ 외부 관측·경보
+ 호스트 밖 backup과 restore drill
+ 사고 대응 runbook
```

이 과정은 Kubernetes, 다중 호스트 고가용성, multi-region, managed cloud 제품 전체, 조직 보안 인증 절차를 완전하게 다루지 않습니다. 단일 호스트 장애는 잔여 위험으로 남기며, 이를 감추는 대신 복구 가능한 상태와 측정 가능한 RPO·RTO를 만듭니다.

## 읽는 순서

### Part I. 요청에서 로컬 스택까지

| 순서 | 문서 | 핵심 경계 |
|---:|---|---|
| 1 | [웹 요청과 서버의 기본 구조](docs/01-web-request-and-server.md) | DNS·TCP·TLS·HTTP와 서버 프로세스 |
| 2 | [Docker 이미지와 컨테이너](docs/02-docker-image-and-container.md) | image, container와 PID 1 수명 |
| 3 | [Compose, 네트워크와 저장소](docs/03-compose-network-and-storage.md) | 서비스 이름, 공개 포트와 volume |
| 4 | [Nginx, TLS와 PHP-FPM](docs/04-nginx-tls-and-php-fpm.md) | HTTPS gateway와 FastCGI runtime |
| 5 | [데이터베이스 컨테이너의 생명주기](docs/05-database-lifecycle.md) | 초기화, 영속화, backup과 restore |
| 6 | [멱등한 애플리케이션 초기화](docs/06-idempotent-app-bootstrap.md) | 재시도 가능한 bootstrap과 부분 실패 |
| 7 | [운영, 장애 진단과 복구](docs/07-operations-debugging-and-recovery.md) | 최초 실패와 2차 증상 구분 |

### Part II. 공개 운영 기준선

| 순서 | 문서 | 핵심 결과 |
|---:|---|---|
| 8 | [운영 계약과 위협 모델](docs/08-production-contract-and-threat-model.md) | 서비스 경계, RPO·RTO, 잔여 위험 |
| 9 | [Linux 호스트 준비와 강화](docs/09-linux-host-provisioning-and-hardening.md) | SSH, 권한, 방화벽, 운영 경로 |
| 10 | [DNS, ACME와 공개 TLS](docs/10-dns-acme-and-public-tls.md) | 권한 DNS, 인증서 수명과 갱신 |
| 11 | [이미지, registry와 release 산출물](docs/11-image-registry-and-release-artifacts.md) | digest, SBOM, provenance, 호환성 |
| 12 | [CI/CD, 배포와 rollback](docs/12-ci-cd-deployment-and-rollback.md) | 안전한 상태 전이와 확정 지점 |
| 13 | [운영 비밀값과 설정](docs/13-production-secrets-and-configuration.md) | versioned secret과 회전 |
| 14 | [관측성과 경보](docs/14-observability-and-alerting.md) | 외부 probe, log, metric, alert |
| 15 | [백업, 복원과 재해 복구](docs/15-backup-restore-and-disaster-recovery.md) | 일관된 artifact와 복원 훈련 |
| 16 | [용량, 자원 제한과 업데이트](docs/16-capacity-resource-limits-and-updates.md) | headroom, 고갈 예측, 지원 수명 |
| 17 | [사고 대응과 runbook](docs/17-incident-response-and-runbooks.md) | 역할, 증거, 완화, 복구, 사후 조치 |
| 18 | [공개 서비스 재구축 Capstone](docs/18-production-rebuild-capstone.md) | 새 호스트에서의 종단 간 재구축 |

앞 장의 상태와 용어를 다음 장에서 이어서 사용합니다. Part II는 Part I의 로컬 스택을 “인터넷에서 접속된다”는 수준이 아니라, 변경·장애·데이터 손실 뒤에도 설명하고 복구할 수 있는 시스템으로 바꿉니다.

## 실습 구조

07을 제외한 실습은 추적되는 시작 상태와 완료 뒤 비교할 기준 구현을 제공합니다. `skeleton/`은 저장소 검증기가 의도된 실패를 확인하는 canonical start이므로 직접 수정하지 않습니다. 다음 명령으로 각 실습의 ignored `workspace/`를 한 번만 만든 뒤 그 안에서 작업합니다.

```sh
python3 scripts/new-workspace.py exercises/01-request-and-process
```

```text
exercises/NN-name/
├── README.md
├── skeleton/
├── workspace/   # 생성 후 학습자가 수정; Git에서 제외
├── reference/
└── verify.sh
```

각 exercise 디렉터리의 `./verify.sh workspace`는 학습자의 결과만 검사합니다. 인자를 생략해도 `workspace`를 선택하므로 답안이 대신 통과하는 일이 없습니다. 먼저 자신의 결과와 설명을 완성한 뒤에만 같은 exercise의 `reference/` source와 `./verify.sh reference`를 비교합니다. Root `reference/`는 답안이 아니라 학습 중 찾아보는 빠른 참고 문서입니다.

07은 구현 답안이 없는 분석형 예외입니다. 정상 스택에 오류를 한 가지씩 주입하고 `workspace/evidence.md`에 관찰과 복구 판단을 기록합니다. 08·17·18의 `reference/`도 유일한 정답 code가 아니라 자동 검사를 통과하는 expected evidence 예시입니다.

### 문서에서 다음 단계까지

각 행을 위에서 아래로 수행합니다. 별도 `examples/`는 없으며 02의 `breakages/`와 07의 scenario가 좁은 실패 관찰 자료입니다.

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---:|---|---|---|---|---|---|
| 01 | [웹 요청과 서버](docs/01-web-request-and-server.md) | — | [요청·프로세스](exercises/01-request-and-process/README.md) | `exercises/01-request-and-process/workspace/server.py` | `exercises/01-request-and-process/verify.sh workspace` | `exercises/01-request-and-process/reference/` → 02 |
| 02 | [Docker image와 container](docs/02-docker-image-and-container.md) | [`breakages/`](exercises/02-container/breakages/) PID 1 실패 | [컨테이너](exercises/02-container/README.md) | `exercises/02-container/workspace/Dockerfile` | `exercises/02-container/verify.sh workspace` | `exercises/02-container/reference/` → 03 |
| 03 | [Compose network와 storage](docs/03-compose-network-and-storage.md) | — | [Compose](exercises/03-compose/README.md) | `exercises/03-compose/workspace/compose.yaml` | `exercises/03-compose/verify.sh workspace` | `exercises/03-compose/reference/` → 04 |
| 04 | [Nginx·TLS·PHP-FPM](docs/04-nginx-tls-and-php-fpm.md) | — | [gateway/runtime](exercises/04-gateway-runtime/README.md) | `exercises/04-gateway-runtime/workspace/`의 FPM·Nginx 설정 | `exercises/04-gateway-runtime/verify.sh workspace` | `exercises/04-gateway-runtime/reference/` → 05 |
| 05 | [DB lifecycle](docs/05-database-lifecycle.md) | — | [데이터베이스](exercises/05-database/README.md) | `exercises/05-database/workspace/`의 DB 설정·entrypoint | `exercises/05-database/verify.sh workspace` | `exercises/05-database/reference/` → PHP/PDO 참고 자료 |
| 06 | [PHP/PDO 기초](reference/php-pdo-bootstrap.md) → [멱등 초기화](docs/06-idempotent-app-bootstrap.md) | — | [앱 초기화](exercises/06-app-bootstrap/README.md) | `exercises/06-app-bootstrap/workspace/app/` | `exercises/06-app-bootstrap/verify.sh workspace` | `exercises/06-app-bootstrap/reference/` → 07 |
| 07 | [장애 진단과 복구](docs/07-operations-debugging-and-recovery.md) | [6개 fault scenario](exercises/07-troubleshooting/scenarios/) | [장애 조사](exercises/07-troubleshooting/README.md) | `exercises/07-troubleshooting/workspace/evidence.md` | `exercises/07-troubleshooting/verify.sh scenarios` + `exercises/07-troubleshooting/verify.sh workspace` | 수동 인과 검토 → 08 |
| 08 | [운영 계약](docs/08-production-contract-and-threat-model.md) | — | [운영 계약](exercises/08-production-contract/README.md) | `exercises/08-production-contract/workspace/contract.yaml` | `exercises/08-production-contract/verify.sh workspace` | expected evidence `exercises/08-production-contract/reference/` → 09 |
| 09 | [Linux host 강화](docs/09-linux-host-provisioning-and-hardening.md) | — | [host 감사](exercises/09-host-hardening/README.md) | `exercises/09-host-hardening/workspace/audit.py` | `exercises/09-host-hardening/verify.sh workspace` | `exercises/09-host-hardening/reference/` → 10 |
| 10 | [DNS·ACME·TLS](docs/10-dns-acme-and-public-tls.md) | — | [TLS lifecycle](exercises/10-public-tls/README.md) | `exercises/10-public-tls/workspace/tls-lifecycle.sh` | `exercises/10-public-tls/verify.sh workspace` | `exercises/10-public-tls/reference/` → 11 |
| 11 | [release 산출물](docs/11-image-registry-and-release-artifacts.md) | — | [release artifact](exercises/11-release-artifact/README.md) | `exercises/11-release-artifact/workspace/{Dockerfile,release.yaml}` | `exercises/11-release-artifact/verify.sh workspace` | `exercises/11-release-artifact/reference/` → 12 |
| 12 | [배포와 rollback](docs/12-ci-cd-deployment-and-rollback.md) | — | [배포 상태 기계](exercises/12-deployment-rollback/README.md) | `exercises/12-deployment-rollback/workspace/deploy.py` | `exercises/12-deployment-rollback/verify.sh workspace` | `exercises/12-deployment-rollback/reference/` → 13 |
| 13 | [운영 secret](docs/13-production-secrets-and-configuration.md) | — | [secret rotation](exercises/13-secret-rotation/README.md) | `exercises/13-secret-rotation/workspace/rotate.py` | `exercises/13-secret-rotation/verify.sh workspace` | `exercises/13-secret-rotation/reference/` → 14 |
| 14 | [관측성과 경보](docs/14-observability-and-alerting.md) | — | [관측 service](exercises/14-observability/README.md) | `exercises/14-observability/workspace/app.py` | `exercises/14-observability/verify.sh workspace` | `exercises/14-observability/reference/` → 15 |
| 15 | [backup과 DR](docs/15-backup-restore-and-disaster-recovery.md) | — | [backup/restore](exercises/15-disaster-recovery/README.md) | `exercises/15-disaster-recovery/workspace/backup.py` | `exercises/15-disaster-recovery/verify.sh workspace` | `exercises/15-disaster-recovery/reference/` → 16 |
| 16 | [용량과 update](docs/16-capacity-resource-limits-and-updates.md) | — | [용량 계획](exercises/16-capacity-and-updates/README.md) | `exercises/16-capacity-and-updates/workspace/plan.py` | `exercises/16-capacity-and-updates/verify.sh workspace` | `exercises/16-capacity-and-updates/reference/` → 17 |
| 17 | [사고 대응](docs/17-incident-response-and-runbooks.md) | [사고 대응 runbook 색인](docs/runbooks/00-index.md) | [사고 기록](exercises/17-incident-response/README.md) | `exercises/17-incident-response/workspace/response.yaml` | `exercises/17-incident-response/verify.sh workspace` | expected evidence `exercises/17-incident-response/reference/` → 18 |
| 18 | [재구축 Capstone](docs/18-production-rebuild-capstone.md) | [host rebuild runbook](docs/runbooks/09-host-rebuild.md) | [재구축 계획](exercises/18-production-rebuild/README.md) | `exercises/18-production-rebuild/workspace/rebuild-plan.yaml` | `exercises/18-production-rebuild/verify.sh workspace` | synthetic `exercises/18-production-rebuild/reference/` → 폐기 VPS 실행·외부 증거 → 종료 |

## 필요한 환경

`prepare.sh`는 저장소 내부 Python 의존성과 검증용 Docker 이미지를 자동으로 준비합니다. 다음 시스템 도구 자체는 관리자 권한과 운영체제 정책에 영향을 주므로 자동 설치하지 않습니다.

- POSIX 호환 셸
- Python 3.10 이상과 `venv`
- GNU Make
- `tar`, `curl`, OpenSSL
- Docker Engine 또는 Docker Desktop
- Docker Compose v2
- Docker Buildx 0.14 이상(`default-load` 지원)

```sh
python3 --version
openssl version
curl --version
docker --version
docker compose version
docker buildx version
```

Linux, macOS와 WSL2에서 실행할 수 있습니다. Docker daemon이 Linux container를 실행할 수 있어야 합니다.

## 준비와 전체 검증

저장소 루트에서 repository 검증 의존성을 준비합니다.

```sh
./prepare.sh
```

`prepare.sh`는 다음 작업만 수행합니다.

- 정확히 알려진 구형 최종화 파일과 이전 검증 부산물을 제거합니다.
- 셸 검증기의 실행 권한을 정리합니다.
- `.verify/venv`에 고정된 Python 의존성을 설치합니다.
- 실습 Docker image와 Buildx 실행 환경을 준비합니다.
- 준비 상태를 `.verify/prepared.json`에 기록합니다.

소스, 학습자 구현과 운영체제 패키지는 자동으로 변경하지 않습니다. `GUIDE_PREPARE_PULL=0 ./prepare.sh`는 필요한 image가 로컬 Docker daemon에 모두 있을 때 daemon pull만 생략합니다. 전용 Buildx builder의 cache가 비어 있으면 실제 build 단계에서는 registry 접근이 여전히 필요할 수 있으므로, 이 옵션이 완전한 오프라인 검증을 보장하지는 않습니다.

준비가 끝나면 저장소 전체를 한 번에 검사합니다.

```sh
./verify.sh
```

`verify.sh`는 원본 저장소를 직접 빌드하지 않습니다. 임시 작업공간과 검증 전용 Buildx builder를 만들고 다음을 차례로 확인합니다.

1. 최종 디렉터리 구조, 문서 링크, 설정 형식과 스크립트 문법
2. 정적 검증기가 알려진 잘못된 구조를 실제로 거부하는지
3. workspace 생성기·07 evidence checker의 방향성
4. 01–06 reference 통과와 skeleton 실패, 07 장애 시나리오
5. 08–18 reference 통과와 skeleton 실패
6. 상태형 실습의 반복 실행 가능성
7. container, network, volume, run image와 전용 build cache의 정리

전체 로그는 성공·실패와 관계없이 저장소 밖의 임시 디렉터리에 남고 마지막에 `VERIFY LOG` 경로가 출력됩니다. `VERIFY_LOG=/저장소/밖/원하는/절대/경로 ./verify.sh`로 위치를 바꿀 수 있으며 parent 디렉터리는 미리 만들어 두어야 합니다. 저장소 내부 경로와 기존 파일·symlink는 소스 보호를 위해 거부합니다. `.verify/venv`는 준비된 의존성이므로 남기지만, 빌드 결과와 검증 실행 부산물은 성공·실패·중단 여부와 관계없이 정리합니다.

문제를 좁힐 때는 내부 범위를 별도로 실행할 수 있습니다.

```sh
make static
make meta
make verify-production
make verify-foundations
make verify-repeatability
```

Repository 자료와 자동 검사기의 정식 판정은 항상 `./verify.sh`의 결과를 사용합니다. 학습 과정 완료에는 각 workspace 결과와 자기 설명이 필요하며, 18단계는 아래 실제 환경 훈련까지 완료해야 합니다.

## 실제 공개 환경에서의 사용

08–18의 자동 검사는 위험한 운영 순서와 누락된 증거 계약을 로컬에서 찾습니다. 실제 DNS, 공인 인증서, 외부 backup, registry, VPS와 경보 전달을 대신하지는 않습니다. 자동 검사를 통과한 뒤에만 폐기 가능한 실습 도메인과 호스트에서 [`docs/18-production-rebuild-capstone.md`](docs/18-production-rebuild-capstone.md)의 훈련을 수행합니다.

실제 secret, 개인키, production backup과 provider credential은 저장소에 넣지 않습니다. 명령을 복사하기 전에 대상 호스트·Compose project·volume·registry를 다시 확인합니다.

## 데이터 삭제 주의

검증기는 실행마다 고유한 Compose project와 Buildx builder를 사용하고 자신이 만든 자원만 정리합니다. 공유 Docker cache나 다른 프로젝트의 image·container·volume을 전역 정리하지 않습니다.

다음 명령은 unrelated image, rollback artifact와 volume까지 삭제할 수 있으므로 일반 정리 명령으로 사용하지 마세요.

```sh
docker system prune -a --volumes
```

사고 대응 중에는 증거와 rollback 산출물을 보존한 뒤, 무엇이 공간을 사용하고 있는지 확인하고 대상을 명시해 정리합니다.

## Runbook과 참고 자료

아래 root `reference/`는 exercise 답안이 아니라 필요할 때 조회하는 quick reference입니다. Exercise의 `reference/`는 자신의 workspace가 통과한 뒤에만 비교합니다.

- [운영 runbook 색인](docs/runbooks/00-index.md)
- [용어집](reference/glossary.md)
- [명령 빠른 참조](reference/command-reference.md)
- [장애 진단 표](reference/troubleshooting-matrix.md)
- [PHP와 PDO 애플리케이션 초기화 기초](reference/php-pdo-bootstrap.md)

문서와 예제의 라이선스는 저장소 루트의 [라이선스 안내](LICENSE.md)에서 확인할 수 있습니다.
