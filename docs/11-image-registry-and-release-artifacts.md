# 이미지, registry와 release 산출물

개발 호스트에서 `docker compose up --build`가 성공했다는 사실은 production에 무엇을 배포했는지 증명하지 못합니다. 배포 시점마다 호스트에서 다시 빌드하면 같은 commit이라도 base image, package repository, build argument와 네트워크 상태에 따라 결과가 달라질 수 있습니다.

운영 배포의 기본 단위는 소스 디렉터리가 아니라 다음 묶음입니다.

```text
변경할 수 없는 container image digest
+ source revision
+ build provenance와 SBOM
+ 환경별 공개 설정
+ 필요한 secret 이름
+ schema·configuration 호환 범위
+ 배포·검증·rollback 절차
```

이 장의 목표는 “어떤 tag를 사용했다”가 아니라 **정확히 어떤 바이트를 어디에서 만들고 검증해 배포했는지** 추적 가능한 release를 만드는 것입니다.

대응 실습은 [`exercises/11-release-artifact`](../exercises/11-release-artifact/)입니다.

## 1. 한 번 빌드하고 같은 산출물을 승격하기

안전한 기본 흐름은 다음과 같습니다.

```text
source revision 고정
→ 격리된 CI에서 image build
→ 자동 검사
→ registry push
→ digest 기록
→ staging에서 같은 digest 검증
→ production에 같은 digest 배포
```

staging에서 검증한 뒤 production에서 다시 build하지 않습니다. 다시 build하면 다른 산출물을 검증하게 됩니다.

환경 차이는 image를 다시 만드는 대신 실행 시점 설정과 secret으로 주입합니다. 단, 프런트엔드처럼 build 시점에 값이 고정되는 경우 어떤 값이 산출물에 포함됐는지 manifest에 기록하고 민감한 값을 넣지 않습니다.

## 2. Tag와 digest

### Tag

```text
ghcr.io/example/app:1.4.2
ghcr.io/example/app:main
```

Tag는 사람이 읽기 좋은 이름이지만 registry 정책에 따라 다른 image를 가리키도록 변경할 수 있습니다.

### Digest

```text
ghcr.io/example/app@sha256:0123...
```

Digest는 image manifest 내용에 기반한 식별자입니다. 배포와 rollback 기록에는 digest를 사용합니다.

권장 사용:

```text
사람과 release 탐색: semantic tag + commit tag
실제 배포 정본: digest
```

예:

```json
{
  "component": "app",
  "image": "ghcr.io/example/app@sha256:0123456789abcdef...",
  "display_tags": ["1.4.2", "git-a1b2c3d"]
}
```

Tag를 삭제해도 digest가 registry retention 정책으로 함께 지워질 수 있습니다. rollback 기간과 registry 보존 정책을 연결합니다.

## 3. Dockerfile의 운영 계약

### 명시적인 base image

```dockerfile
FROM python:3.14.6-alpine3.24
```

`latest`를 사용하지 않습니다. 버전 tag도 시간이 지나며 다른 digest를 가리킬 수 있으므로 완전 재현성이 필요하면 base digest까지 기록합니다.

```dockerfile
FROM python:3.14.6-alpine3.24@sha256:...
```

Digest 고정은 자동 업데이트를 막습니다. 따라서 오래된 base를 영원히 유지하지 않도록 갱신 자동화와 검증 절차가 필요합니다.

### Multi-stage build

빌드 도구와 runtime을 분리합니다.

```dockerfile
FROM toolchain AS build
# compile or package

FROM runtime
COPY --from=build /out/app /usr/local/bin/app
```

목표는 단순히 image 크기를 줄이는 것이 아닙니다.

- compiler와 package manager를 runtime에서 제거
- 불필요한 credential과 source 제거
- runtime 공격 표면 축소
- 산출물 경계 명확화

### 비root 사용자

애플리케이션이 root 권한을 요구하지 않으면 명시적인 사용자로 실행합니다.

```dockerfile
RUN addgroup -S app && adduser -S -G app app
USER app
```

단순히 `USER`를 추가하기 전에 읽기·쓰기 경로의 owner와 permission을 맞춥니다.

### 변경 가능한 파일 최소화

image layer는 코드와 기본 공개 설정을 포함합니다. 다음은 실행 시점 상태입니다.

- secret
- 업로드
- database
- session 또는 cache
- runtime log
- 임시 파일

실행 시점 상태를 image 안에 굽지 않습니다.

### PID 1과 종료

exec 형식 `ENTRYPOINT`·`CMD`를 사용하고 종료 신호가 실제 애플리케이션 프로세스에 전달되는지 확인합니다.

```dockerfile
ENTRYPOINT ["/usr/local/bin/app"]
```

shell wrapper가 필요하면 마지막에 `exec`를 사용하고, 자식 프로세스 정리 책임을 검증합니다.

## 4. Build secret과 runtime secret

Dockerfile의 `ARG`와 `ENV`에 민감한 값을 넣지 않습니다. 값이 최종 환경 변수에서 제거돼도 build cache나 image history에 남을 수 있습니다.

나쁜 예:

```dockerfile
ARG PRIVATE_TOKEN
RUN curl -H "Authorization: Bearer $PRIVATE_TOKEN" ...
```

BuildKit의 secret mount처럼 build 단계에 일시적으로 제공되고 layer에 기록되지 않는 방식을 사용합니다. 그래도 빌드 명령이 secret을 출력하거나 생성 파일에 남기지 않는지 확인합니다.

runtime secret은 13장에서 별도로 다룹니다.

## 5. OCI label과 산출물 식별

image 자체에서 최소 provenance를 확인할 수 있도록 표준 label을 사용합니다.

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/example/service" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE"
```

label은 CI가 전달한 값을 신뢰하므로 서명이나 attestation을 대신하지 않습니다. 그러나 실행 중인 image와 source revision을 빠르게 연결합니다.

```sh
docker image inspect \
  --format '{{json .Config.Labels}}' \
  ghcr.io/example/app@sha256:...
```

## 6. SBOM과 provenance

### SBOM

Software Bill of Materials는 image에 포함된 package와 component 목록을 제공합니다. 취약점 공지가 나왔을 때 어떤 release가 영향을 받는지 찾는 데 사용합니다.

SBOM은 다음 질문에 답해야 합니다.

- 어떤 package가 들어 있는가?
- 버전과 package manager는 무엇인가?
- 어떤 image digest를 대상으로 생성했는가?
- 언제 어떤 도구로 생성했는가?

SBOM이 있다고 취약점이 자동으로 해결되는 것은 아닙니다. scanner 결과, 위험 승인과 base image 갱신 절차가 필요합니다.

### Build provenance

Provenance는 누가, 어디에서, 어떤 source와 build 정의로 산출물을 만들었는지 나타냅니다. 지원되는 CI와 registry에서는 attestation을 image와 함께 게시하고 배포 전에 검증할 수 있습니다.

검증할 질문:

- 신뢰하는 repository와 workflow에서 만들었는가?
- 예상 source revision인가?
- 대상 image digest와 attestation subject가 같은가?
- build definition이 허용된 경로인가?

처음부터 강제 정책을 만들기 어렵다면 먼저 생성·보존·수동 검증을 구현한 뒤 배포 gate로 승격합니다.

## 7. Registry의 역할과 권한

Registry는 단순 저장 공간이 아니라 production 복구 원본입니다.

필요한 정책:

- CI는 대상 repository에 push할 수 있습니다.
- production host는 pull만 할 수 있습니다.
- 사람이 tag를 임의로 덮어쓸 수 있는 권한을 제한합니다.
- 삭제와 retention 권한을 별도로 관리합니다.
- 취약점 검사와 서명·attestation 보존 정책을 압니다.
- rollback 기간 동안 이전 digest가 남습니다.

production host에 registry 관리자 credential을 저장하지 않습니다. 가능한 경우 read-only token 또는 짧은 수명 credential을 사용합니다.

## 8. Release manifest

한 release의 모든 구성요소와 호환 조건을 구조화된 파일로 기록합니다.

예:

```yaml
schema_version: 1
release_id: 2026-08-07.1
source_revision: a1b2c3d4e5f6
created_at: 2026-08-07T10:30:00Z
components:
  gateway:
    image: ghcr.io/example/gateway@sha256:...
  app:
    image: ghcr.io/example/app@sha256:...
database:
  schema_min: 17
  schema_max: 18
configuration:
  schema: 3
required_secrets:
  - db_password_v2
verification:
  smoke_paths:
    - /healthz
    - /api/notes
rollback:
  compatible_to_release: 2026-08-01.2
```

Manifest는 실제 secret 값을 포함하지 않습니다.

### Manifest의 정본성

다음 중 하나를 정합니다.

- release artifact와 함께 registry 또는 object storage에 보관
- Git의 별도 deployment repository에 commit
- CI가 서명한 artifact로 보관

production host의 현재 파일만 정본으로 삼지 않습니다. 호스트가 사라져도 release를 재구성할 수 있어야 합니다.

## 9. 애플리케이션과 schema 호환성

image rollback이 가능해도 database schema가 이미 비호환 상태로 변경됐다면 이전 image가 동작하지 않을 수 있습니다.

Manifest에 다음을 기록합니다.

- 최소·최대 schema version
- migration 전후 호환 가능한 application release
- 공개 설정 schema version
- secret 이름과 형식 version
- rollback 가능한 마지막 release

12장에서 expand-contract migration과 rollback 순서를 다룹니다.

## 10. Image 검사 단계

CI에서 최소한 다음을 수행합니다.

```text
Dockerfile lint 또는 정책 검사
→ application test
→ image build
→ image 내부 사용자·entrypoint·label 검사
→ 취약점 scan
→ SBOM 생성
→ provenance 생성
→ registry push
→ digest 확인
→ staging smoke test
```

검사 실패를 무시한 채 “참고용 결과”로만 남긴다면 어떤 위험을 허용하는지 명시합니다. severity 숫자 하나만으로 자동 차단하지 말고, exploitability, public exposure와 수정 가능성을 포함한 정책을 정합니다.

## 11. Production에서 source build를 피하는 이유

호스트에서 다음을 수행하는 방식은 단순해 보입니다.

```sh
git pull
docker compose build
docker compose up -d
```

그러나 다음 문제가 있습니다.

- host에 source와 build 도구가 필요합니다.
- 배포 순간 외부 package repository에 의존합니다.
- 검증한 image와 실제 배포 image가 달라질 수 있습니다.
- 실패한 build가 현재 작업 디렉터리를 어지럽힐 수 있습니다.
- 정확한 rollback digest가 남지 않을 수 있습니다.

운영 host는 release manifest를 읽고 이미지를 pull해 실행하는 역할에 집중합니다.

## 12. 보존과 정리

무제한 보존도, 무조건 최신 몇 개만 남기는 것도 위험합니다.

보존 기준:

- 현재 release
- 즉시 rollback 가능한 이전 release
- 진행 중 incident에서 필요한 release
- 규제·감사 기간
- 해당 DB schema와 호환되는 마지막 release
- 재해 복구 훈련에서 사용한 release

삭제 전 manifest와 deployment history에서 참조 여부를 확인합니다.

## 13. 실습

[`exercises/11-release-artifact`](../exercises/11-release-artifact/)은 작은 application image와 release manifest를 제공합니다. 자동 검사는 다음을 확인합니다.

- base image가 `latest`가 아닌가?
- runtime이 비root 사용자인가?
- exec 형식 entrypoint인가?
- source revision·version OCI label이 있는가?
- secret을 `ARG`·`ENV`에 넣지 않았는가?
- release manifest가 tag가 아니라 digest를 정본으로 사용하는가?
- SBOM·provenance 생성과 검증 정책이 선언되어 있는가?
- rollback 대상과 schema 호환 범위가 있는가?

이 실습은 실제 registry 제품을 강제하지 않습니다. 산출물 계약이 registry 구현과 분리되어 있는지 검사합니다.

## 14. 공식 확인 자료

- Docker build attestations: <https://docs.docker.com/build/metadata/attestations/>
- Docker SBOM attestations: <https://docs.docker.com/build/metadata/attestations/sbom/>
- Docker build secrets: <https://docs.docker.com/build/building/secrets/>
- OCI image annotations: <https://github.com/opencontainers/image-spec/blob/main/annotations.md>
- GitHub artifact attestations: <https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations>

다음 장에서는 이 release 산출물을 한 번에 하나씩 production에 적용하고, 실패하면 안전하게 이전 상태로 되돌리는 배포 상태 기계를 만듭니다.
