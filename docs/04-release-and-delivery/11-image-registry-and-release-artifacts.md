# 이미지, 레지스트리와 릴리스 산출물

개발 호스트에서 `docker compose up --build`가 성공했다는 사실만으로 운영 환경에 무엇을 배포했는지 증명할 수는 없습니다. 배포할 때마다 호스트에서 다시 빌드하면 같은 커밋이라도 베이스 이미지, 패키지 저장소, 빌드 인자, 네트워크 상태에 따라 결과가 달라질 수 있습니다.

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

이 장의 목표는 “어떤 태그를 사용했다”가 아니라 **정확히 어떤 바이트를 어디에서 만들고 검증해 배포했는지** 추적 가능한 릴리스를 만드는 것입니다.

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

스테이징에서 검증한 뒤 운영 환경에서 다시 빌드하지 않습니다. 다시 빌드하면 검증한 산출물과 다른 산출물을 배포하게 될 수 있습니다.

환경 차이는 이미지를 다시 만드는 대신 실행 시점 설정과 비밀값으로 주입합니다. 단, 프런트엔드처럼 빌드 시점에 값이 고정되는 경우 어떤 값이 산출물에 포함됐는지 매니페스트에 기록하고 민감한 값은 넣지 않습니다.

## 2. 태그와 다이제스트

### 태그

```text
ghcr.io/example/app:1.4.2
ghcr.io/example/app:main
```

태그는 사람이 읽기 좋은 이름이지만 레지스트리 정책에 따라 다른 이미지를 가리키도록 변경할 수 있습니다.

### 다이제스트

```text
ghcr.io/example/app@sha256:0123...
```

다이제스트는 이미지 매니페스트 내용에 기반한 식별자입니다. 배포와 롤백 기록에는 다이제스트를 사용합니다.

권장 사용:

```text
사람이 릴리스를 찾고 식별: semantic tag + commit tag
실제 배포 기준: 다이제스트
```

예:

```json
{
  "component": "app",
  "image": "ghcr.io/example/app@sha256:0123456789abcdef...",
  "display_tags": ["1.4.2", "git-a1b2c3d"]
}
```

태그를 삭제하면 레지스트리 보존 정책에 따라 다이제스트가 함께 정리될 수 있습니다. 롤백 가능 기간과 레지스트리 보존 정책을 연결합니다.

## 3. Dockerfile의 운영 계약

### 명시적인 베이스 이미지

```dockerfile
FROM python:3.14.6-alpine3.24
```

`latest`를 사용하지 않습니다. 버전 태그도 시간이 지나면서 다른 다이제스트를 가리킬 수 있으므로 완전한 재현성이 필요하면 베이스 이미지 다이제스트까지 기록합니다.

```dockerfile
FROM python:3.14.6-alpine3.24@sha256:...
```

다이제스트 고정은 자동 업데이트를 막습니다. 오래된 베이스 이미지를 영구히 유지하지 않도록 갱신 자동화와 검증 절차가 필요합니다.

### 멀티스테이지 빌드

빌드 도구와 런타임을 분리합니다.

```dockerfile
FROM toolchain AS build
# compile or package

FROM runtime
COPY --from=build /out/app /usr/local/bin/app
```

목표는 단순히 이미지 크기를 줄이는 것이 아닙니다.

- 컴파일러와 패키지 관리자를 런타임에서 제거
- 불필요한 자격 증명과 소스 제거
- 런타임 공격 표면 축소
- 산출물 경계 명확화

### 비root 사용자

애플리케이션이 root 권한을 요구하지 않으면 명시적인 사용자로 실행합니다.

```dockerfile
RUN addgroup -S app && adduser -S -G app app
USER app
```

단순히 `USER`를 추가하기 전에 읽기·쓰기 경로의 소유자와 권한을 맞춥니다.

### 변경 가능한 파일 최소화

이미지 레이어는 코드와 기본 공개 설정을 포함합니다. 다음은 실행 시점 상태입니다.

- 비밀값
- 업로드
- 데이터베이스
- 세션 또는 캐시
- 런타임 로그
- 임시 파일

실행 시점 상태를 이미지 안에 굽지 않습니다.

### PID 1과 종료

배열 형식 `ENTRYPOINT`·`CMD`를 사용하고 종료 신호가 실제 애플리케이션 프로세스에 전달되는지 확인합니다.

```dockerfile
ENTRYPOINT ["/usr/local/bin/app"]
```

셸 래퍼가 필요하면 마지막에 `exec`를 사용하고 자식 프로세스 정리 책임을 검증합니다.

## 4. 빌드 비밀값과 런타임 비밀값

Dockerfile의 `ARG`와 `ENV`에 민감한 값을 넣지 않습니다. 최종 환경변수에서 값을 제거해도 빌드 캐시나 이미지 이력에 남을 수 있습니다.

나쁜 예:

```dockerfile
ARG PRIVATE_TOKEN
RUN curl -H "Authorization: Bearer $PRIVATE_TOKEN" ...
```

BuildKit의 비밀값 마운트처럼 빌드 단계에 일시적으로 제공되고 레이어에 기록되지 않는 방식을 사용합니다. 그래도 빌드 명령이 비밀값을 출력하거나 생성 파일에 남기지 않는지 확인합니다.

런타임 비밀값은 13장에서 별도로 다룹니다.

## 5. OCI 레이블과 산출물 식별

이미지 자체에서 최소한의 출처 정보를 확인할 수 있도록 표준 레이블을 사용합니다.

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/example/service" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.version="$VERSION" \
      org.opencontainers.image.created="$BUILD_DATE"
```

레이블은 CI가 전달한 값을 신뢰하므로 서명이나 attestation을 대신하지 않습니다. 하지만 실행 중인 이미지와 소스 리비전을 빠르게 연결하는 데 유용합니다.

```sh
docker image inspect \
  --format '{{json .Config.Labels}}' \
  ghcr.io/example/app@sha256:...
```

## 6. SBOM과 빌드 출처 정보

### SBOM

Software Bill of Materials는 이미지에 포함된 패키지와 구성요소 목록을 제공합니다. 취약점 공지가 나왔을 때 어떤 릴리스가 영향을 받는지 찾는 데 사용합니다.

SBOM은 다음 질문에 답해야 합니다.

- 어떤 패키지가 들어 있는가?
- 버전과 패키지 관리자는 무엇인가?
- 어떤 이미지 다이제스트를 대상으로 생성했는가?
- 언제 어떤 도구로 생성했는가?

SBOM이 있다고 취약점이 자동으로 해결되는 것은 아닙니다. 스캐너 결과, 위험 승인, 베이스 이미지 갱신 절차가 필요합니다.

### Build provenance

Provenance는 누가, 어디에서, 어떤 소스와 빌드 정의로 산출물을 만들었는지 나타냅니다. 지원되는 CI와 레지스트리에서는 attestation을 이미지와 함께 게시하고 배포 전에 검증할 수 있습니다.

검증할 질문:

- 신뢰하는 저장소와 workflow에서 만들었는가?
- 예상 소스 리비전인가?
- 대상 이미지 다이제스트와 attestation subject가 같은가?
- 빌드 정의가 허용된 경로인가?

처음부터 강제 정책을 만들기 어렵다면 먼저 생성·보존·수동 검증을 구현한 뒤 배포 게이트로 승격합니다.

## 7. 레지스트리의 역할과 권한

레지스트리는 단순 저장 공간이 아니라 운영 복구 원본 중 하나입니다.

필요한 정책:

- CI는 대상 저장소에 push할 수 있습니다.
- 운영 호스트는 pull만 할 수 있습니다.
- 사람이 태그를 임의로 덮어쓸 수 있는 권한을 제한합니다.
- 삭제와 보존 정책 권한을 별도로 관리합니다.
- 취약점 검사와 서명·attestation 보존 정책을 압니다.
- 롤백 기간 동안 이전 다이제스트가 남습니다.

운영 호스트에 레지스트리 관리자 자격 증명을 저장하지 않습니다. 가능한 경우 read-only 토큰 또는 짧은 수명의 자격 증명을 사용합니다.

## 8. 릴리스 매니페스트

한 릴리스의 모든 구성요소와 호환 조건을 구조화된 파일로 기록합니다.

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

매니페스트에는 실제 비밀값을 포함하지 않습니다.

### 매니페스트의 기준 원본

다음 중 하나를 정합니다.

- 릴리스 산출물과 함께 레지스트리 또는 객체 저장소에 보관
- Git의 별도 배포 저장소에 커밋
- CI가 서명한 산출물로 보관

운영 호스트의 현재 파일만 기준 원본으로 삼지 않습니다. 호스트가 사라져도 릴리스를 재구성할 수 있어야 합니다.

## 9. 애플리케이션과 스키마 호환성

이미지 롤백이 가능해도 데이터베이스 스키마가 이미 비호환 상태로 변경됐다면 이전 이미지가 동작하지 않을 수 있습니다.

매니페스트에 다음을 기록합니다.

- 최소·최대 스키마 버전
- 마이그레이션 전후 호환 가능한 애플리케이션 릴리스
- 공개 설정 스키마 버전
- 비밀값 이름과 형식 버전
- 롤백 가능한 마지막 릴리스

12장에서 expand-contract 마이그레이션과 롤백 순서를 다룹니다.

## 10. 이미지 검사 단계

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

검사 실패를 무시한 채 “참고용 결과”로만 남긴다면 어떤 위험을 허용하는지 명시합니다. 심각도 숫자 하나만으로 자동 차단하지 말고 악용 가능성, 외부 노출 범위, 수정 가능성을 포함한 정책을 정합니다.

## 11. 운영 환경에서 소스 빌드를 피하는 이유

호스트에서 다음을 수행하는 방식은 단순해 보입니다.

```sh
git pull
docker compose build
docker compose up -d
```

그러나 다음 문제가 있습니다.

- 호스트에 소스와 빌드 도구가 필요합니다.
- 배포 순간 외부 패키지 저장소에 의존합니다.
- 검증한 이미지와 실제 배포 이미지가 달라질 수 있습니다.
- 실패한 빌드가 현재 작업 디렉터리를 어지럽힐 수 있습니다.
- 정확한 롤백 다이제스트가 남지 않을 수 있습니다.

운영 호스트는 릴리스 매니페스트를 읽고 이미지를 pull해 실행하는 역할에 집중합니다.

## 12. 보존과 정리

무제한 보존도, 무조건 최신 몇 개만 남기는 것도 위험합니다.

보존 기준:

- 현재 릴리스
- 즉시 롤백 가능한 이전 릴리스
- 진행 중인 사고에서 필요한 릴리스
- 규제·감사 기간
- 해당 DB 스키마와 호환되는 마지막 릴리스
- 재해 복구 훈련에서 사용한 릴리스

삭제 전에 매니페스트와 배포 이력에서 참조 여부를 확인합니다.

## 13. 실습

[`exercises/11-release-artifact`](../exercises/11-release-artifact/)은 작은 애플리케이션 이미지와 릴리스 매니페스트를 제공합니다. 자동 검사는 다음을 확인합니다.

- 베이스 이미지가 `latest`가 아닌가?
- 런타임이 비root 사용자인가?
- 배열 형식 entrypoint인가?
- 소스 리비전·버전 OCI 레이블이 있는가?
- 비밀값을 `ARG`·`ENV`에 넣지 않았는가?
- 릴리스 매니페스트가 태그가 아니라 다이제스트를 배포 기준으로 사용하는가?
- SBOM·provenance 생성과 검증 정책이 선언되어 있는가?
- 롤백 대상과 스키마 호환 범위가 있는가?

이 실습은 특정 레지스트리 제품을 강제하지 않습니다. 산출물 계약이 레지스트리 구현과 분리되어 있는지 검사합니다.

## 14. 공식 확인 자료

- Docker build attestations: <https://docs.docker.com/build/metadata/attestations/>
- Docker SBOM attestations: <https://docs.docker.com/build/metadata/attestations/sbom/>
- Docker build secrets: <https://docs.docker.com/build/building/secrets/>
- OCI image annotations: <https://github.com/opencontainers/image-spec/blob/main/annotations.md>
- GitHub artifact attestations: <https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations>

다음 장에서는 이 릴리스 산출물을 한 번에 하나씩 운영 환경에 적용하고 실패하면 안전하게 이전 상태로 되돌리는 배포 상태 머신을 만듭니다.
