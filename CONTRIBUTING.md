# 기여 안내

문서, 예제와 검사는 같은 계약을 가리켜야 한다. 설명만 추가하거나 reference만 통과시키지 말고, 학습자가 출발하는 skeleton과 실패·경계 검사를 함께 확인한다.

## 구조 원칙

- 학습 경로와 범위는 `docs/00-roadmap.md`에서 시작한다.
- 필수 설명은 `docs/`, 실행 가능한 관찰 코드는 `examples/`, 직접 구현할 문제는 `exercises/`에 둔다.
- 각 exercise는 `README.md`, `skeleton/`, `reference/`, `tests/`를 가진다.
- `skeleton`은 최소 한 개의 필수 검사에 실패해야 하고, `reference`는 전체 검사에 통과해야 한다.
- 애플리케이션 DB 경로와 DBMS 내부구조 경로가 공유하는 용어는 같은 의미로 사용한다.
- 웹 애플리케이션의 첫 SQL, Spring 연결법, 분산 transaction과 호스트 운영을 이 저장소에서 다시 완전하게 가르치지 않는다.

## 문서를 고칠 때

- 한국어 `-다체`를 사용한다.
- 명령, API, 타입과 식별자는 원래 표기를 유지하고 백틱으로 구분한다.
- 새 문서는 최소한 `학습 목표`, `연결 연습`, `완료 기준`을 포함한다.
- 정상 경로뿐 아니라 실패 후 상태, 소유권과 비보장 범위를 설명한다.
- 성능 수치는 DBMS 버전, 데이터 규모, parameter 분포와 cache 조건 없이 일반화하지 않는다.
- 다른 문서에서 소유한 개념은 짧게 연결하고 같은 설명을 복제하지 않는다.
- 내부 링크는 저장소 상대경로로 작성하고 `python3 scripts/validate.py`로 검사한다.

## Exercise를 고칠 때

- 검사는 소스 문자열보다 실제 결과와 상태를 우선 확인한다.
- SQL exercise는 별도 임시 PostgreSQL database에서 실행되어야 한다.
- Python reference는 표준 라이브러리만으로 재현 가능해야 한다.
- 임시 파일, container와 database는 성공·실패 경로 모두에서 정리한다.
- concurrency 검사는 `sleep`에만 의존하지 말고 공유 conflict 지점과 최종 불변식을 검사한다.
- skeleton이 우연히 통과하지 않도록 알려진 잘못된 구현을 실제로 거부하는지 확인한다.

## 학습 구현 주석을 고칠 때

- 하나의 독립 example과 하나의 exercise `reference/` project가 각각 번호 범위 하나를 소유한다. 파일마다 번호를 다시 시작하지 않는다.
- 번호는 Git의 과거 작성 이력이 아니라 권장 construction order다. 가장 가까운 learner-facing README의 index와 source anchor가 같은 범위를 설명해야 한다.
- 주석은 책임, state/resource owner, invariant, failure state와 다음 단계의 의존성을 설명한다. 모든 함수나 단순 boilerplate에 기계적으로 붙이지 않는다.
- `skeleton/`, tests, fixture, validator, prepare/verify, generated file, lockfile과 exact manifest에는 학습 구현 marker를 넣지 않는다.
- Project bootstrap 단계는 실제 generator·package/framework 초기화가 있을 때만 사용한다. Workspace 복사, Docker image 준비, build와 검증 명령은 bootstrap 단계가 아니다.
- Marker를 추가하거나 옮기면 `python3 scripts/validate.py`와 validator mutant suite로 scope별 유일성·연속성과 금지 위치를 함께 확인한다.

## 변경 확인

저장소 루트의 공개 명령 네 가지는 다음과 같다.

```bash
make prepare
make check
VERIFY_LOG=/tmp/database-systems-verify.log make verify
make clean
```

`make prepare`는 source를 변경하지 않고 고정 이미지와 fingerprint marker만 준비한다. `make check`는 Docker 없이 가능한 빠른 검사를, `make verify`는 외부 임시 복사본에서 구조, 예제, Python exercise와 실제 PostgreSQL exercise를 모두 검사한다. `make clean`은 명시된 생성물만 지우며 준비 cache와 learner workspace는 보존한다.
`VERIFY_LOG`를 생략하면 저장소 밖 `/tmp`에 실행별 로그를 만들며, 직접 지정한 경로는 저장소 밖 절대 경로여야 한다.

커밋 전에는 추적 범위와 공백 오류를 확인한다.

```bash
git status --short
git diff --check
git diff --staged
```
