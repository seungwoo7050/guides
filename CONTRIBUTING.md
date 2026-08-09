# 기여 안내

문서, 예제, 연습과 검사는 같은 데이터 계약을 가리켜야 한다. 도구 이름이나 성공 화면만 추가하지 말고, 입력 snapshot, record identity, 시간 의미, publish 경계와 실패 뒤 상태를 함께 확인한다.

## 구조 원칙

- 학습 경로와 비소유 범위는 `docs/00-roadmap.md`에서 시작한다.
- 필수 설명은 `docs/`, 작은 상태 모델은 `examples/`, 직접 구현할 문제는 `exercises/`, 운영 checklist와 공식 자료는 `reference/`에 둔다.
- 코드 exercise는 `README.md`, `skeleton/`, `reference/`, `tests/`를 가진다.
- `skeleton`은 최소 한 개의 의미 검사에 실패하고, `reference`는 같은 검사에 통과해야 한다.
- Capstone은 완성 구현 대신 설계 계약, artifact template, failure matrix와 review rubric을 제공할 수 있다.
- DBMS 내부구조, 서비스 Saga, 분산 합의, 모델 학습과 플랫폼 운영을 이 저장소에서 다시 완전히 가르치지 않는다.

## 문서를 고칠 때

- 한국어 `-다체`를 사용한다.
- 명령, API, 타입과 식별자는 원래 표기를 유지하고 백틱으로 구분한다.
- 개념 문서는 `학습 목표`, `핵심 모델`, `실패 모드`, `검증 질문`, `연결 연습`, `완료 기준`을 포함한다.
- “exactly-once”, “실시간”, “정합”, “완료” 같은 표현은 관측 경계와 비보장을 함께 적는다.
- 성능 수치는 engine·version·data shape·partition·cache·cluster 조건 없이 일반화하지 않는다.
- 다른 브랜치가 소유한 원리는 링크하고, 데이터 엔지니어링에서 달라지는 적용 경계만 설명한다.
- 외부 자료는 공식 specification 또는 프로젝트 문서를 우선하고 `reference/official-sources.md`에 검토 날짜를 남긴다.

## Exercise를 고칠 때

- 문자열 존재보다 결과 record와 상태를 검사한다.
- 입력 순서, 중복, late event, restart와 partial publish를 최소 하나 이상 포함한다.
- test fixture는 작고 결정적이어야 하며 wall clock과 네트워크에 의존하지 않는다.
- reference는 Python 표준 라이브러리만으로 재현 가능하게 유지한다.
- 임시 파일은 성공·실패 모두에서 정리하고 source tree를 수정하지 않는다.
- skeleton이 우연히 통과하지 않도록 알려진 잘못된 구현을 실제로 거부한다.

## 변경 확인

```bash
make prepare
make check
VERIFY_LOG=/tmp/data-engineering-verify.log make verify
make clean

git status --short
git diff --check
git diff --staged
```

`make verify`는 source 바이트와 mode가 검증 전후 같음을 확인한다. 검증을 위해 생성하는 workspace, log와 임시 출력은 저장소 밖 또는 명시된 ignored 경로에 둔다.
