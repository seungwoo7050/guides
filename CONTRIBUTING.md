# 기여 안내

문서, Spring 구성과 자동 검증은 같은 계약을 가리켜야 한다. 설명만 고치거나 reference만 통과시키지 말고, 변경한 경계의 정상·실패·복구 상태를 함께 확인한다.

## 범위를 유지한다

이 저장소는 Spring Boot의 프레임워크 구현을 소유한다.

- Java·JVM·Maven 기초는 `guide-java`가 소유한다.
- SQL 의미론·격리·저장구조는 `guide-database-systems`가 소유한다.
- 멱등성·Outbox·재전달·retry의 일반 원리는 `guide-distributed-services`가 소유한다.
- host·DNS·TLS·배포·수집·복구는 `guide-web-infrastructure`가 소유한다.

외부 영역이 Spring 적용에 필요하면 최소 모델만 설명하고, 이 저장소에서 같은 이론을 독립 과정으로 다시 확장하지 않는다.

## 문서를 고친다

- 문서는 한국어 `-다체`로 작성한다.
- API, annotation, 설정 키와 식별자는 원래 표기를 유지하고 백틱으로 구분한다.
- 안정된 원리와 Spring Boot 버전에 종속된 사용법을 구분한다.
- 문서에 새 경로를 추가하면 `docs/00-roadmap.md`의 읽기 순서와 실습 대응표도 갱신한다.
- 필수 설명을 `reference/`나 루트 README에만 두지 않는다.
- 검증하지 않은 성능, 전달 보장과 장애 복구를 단정하지 않는다.

## 실습을 고친다

각 실습은 문제를 설명하는 README와 `skeleton`, `reference`를 가진다.

- skeleton은 compile되어야 하며 알려진 계약 위반 때문에 test가 실패해야 한다.
- dependency 누락, compile 오류와 Docker 부재를 의도한 학습 실패로 사용하지 않는다.
- reference에는 `TODO`, `FIXME`, 임시 반환값을 남기지 않는다.
- HTTP status뿐 아니라 DB·Redis·Outbox·외부 호출과 metric의 최종 상태를 검사한다.
- 동시성 검사는 `sleep`에 의존하지 않고 latch·barrier와 모든 `Future` 결과를 사용한다.
- Testcontainers와 background thread는 성공·실패 경로 모두에서 정리한다.

새 실습을 추가하면 root POM, `prepare.sh`, `verify.sh`와 `scripts/validate.py`의 모듈·실패 계약을 함께 갱신한다.

## 변경을 검증한다

일반 clone과 linked worktree를 포함한 모든 checkout에서 다음 두 명령이 정본이다.

```sh
./prepare.sh
./verify.sh
```

`prepare.sh`는 도구를 확인하고 namespaced Maven cache와 immutable Docker image를 준비한다. source, mode, symlink와 Git index를 변경하거나 정답을 판정하지 않는다. `verify.sh`는 준비가 끝난 현재 tree를 외부 임시 사본에서 offline Maven으로 전체 검사하며 원본 구조나 의존성을 변경하지 않는다.

문서·구조만 빠르게 확인할 때는 다음 명령을 사용할 수 있다.

```sh
python3 scripts/validate.py
```

커밋 전에는 추적 범위와 공백 오류를 확인한다.

```sh
git status --short
git diff --check
git diff --staged
```

빌드 결과, dependency cache, 컨테이너 데이터, 임시 로그와 검증 보고서는 커밋하지 않는다.

## 버전을 변경한다

Spring Boot, Maven Wrapper, Testcontainers 또는 Docker image를 바꾸면 [버전과 개발 환경](docs/90-appendix/01-version-and-environment.md)의 기준도 함께 수정한다. POM만 변경하지 말고 모든 reference 통과, 모든 skeleton의 의도한 실패와 깨끗한 checkout에서의 `./prepare.sh && ./verify.sh`를 다시 확인한다.
