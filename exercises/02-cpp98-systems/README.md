# C++98 시스템 실습

이 디렉터리는 [`docs/02-cpp98-systems`](../../docs/02-cpp98-systems/00-roadmap.md)의 객체·STL·POSIX 네트워크 과정과 대응한다. 모든 실습은 `-std=c++98` 제약을 유지하며, Modern C++ 실습과 같은 구현 방식을 억지로 흉내 내지 않는다.

## 시작하기 전에

새 checkout 또는 overlay 적용 뒤에는 저장소 루트에서 먼저 준비한다.

```sh
./prepare.sh
```

`prepare.sh`는 이동 전 경로와 이전 빌드 부산물을 정리하고, compiler·Make·CMake·Python 및 POSIX 실행 조건을 확인한다. 소스 구현이나 정답 코드를 자동으로 변경하지 않는다.

## 진행 순서

1. 객체 모델과 명령 서비스
   1. [`01-procedural`](object-model/command-service/01-procedural/README.md)
   2. [`02-value-ownership`](object-model/command-service/02-value-ownership/README.md)
   3. [`03-responsibilities`](object-model/command-service/03-responsibilities/README.md)
   4. [`04-polymorphism`](object-model/command-service/04-polymorphism/README.md)
   5. [`05-errors`](object-model/command-service/05-errors/README.md)
2. [템플릿과 고정 크기 배열](generic-programming/template-array/README.md)
3. 선택 심화: [직접 구현하는 작은 vector](generic-programming/mini-vector/README.md)
4. [STL 문제 해결](generic-programming/stl-problems/README.md): `date-lookup` → `rpn` → `sorter`
5. [논블로킹 line server](networking/line-server/README.md)
6. [단계형 HTTP 서버](networking/http-server/README.md)
   1. [`01-parser`](networking/http-server/01-parser/README.md)
   2. [`02-config-router`](networking/http-server/02-config-router/README.md)
   3. [`03-nonblocking-server`](networking/http-server/03-nonblocking-server/README.md)
   4. [`04-cgi-process`](networking/http-server/04-cgi-process/README.md)
   5. [`05-integrated-server`](networking/http-server/05-integrated-server/README.md)

`mini-vector`는 주 경로의 완료 조건이 아니다. 저장 공간과 부분 생성 롤백을 더 깊게 보고 싶을 때 [STL 내부 구조 appendix](../../docs/90-appendix/04-stl-internals.md)와 함께 수행한다.

가능한 실습은 `skeleton`과 `reference`를 분리한다. 정본 skeleton을 직접 수정하지 않고 저장소 루트에서 다음 명령으로 non-overwriting 학습 공간을 만든다.

```sh
make workspace TRACK=cpp98
```

`.workspace/02-cpp98-systems` 안의 해당 `skeleton/`만 수정하고 다음 형식으로 완료 계약을 검사한다.

```sh
make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/01-procedural
```

각 README의 `make observe`는 필수가 아니다. 먼저 결과를 예상하고 reference source를 열지 않은 채 실행 결과만 보는 black-box oracle이다. 자신의 skeleton 구현과 learner 검증을 마친 뒤에만 reference source를 열어 책임 배치, 실패 후 상태와 자원 정리 방식을 비교한다. `03-responsibilities`의 `observe`는 예외적으로 reference가 아니라 리팩터링 전 `skeleton/legacy.cpp`를 실행한다.

## 문서와 실습의 ordered mapping

| 순서 | 문서 | 관찰 예제 | 직접 수행 | 수정 위치 | 검증 | 완료 뒤 비교·다음 |
|---|---|---|---|---|---|---|
| 1 | doc 01 프로그램·타입 | 선택 black-box oracle | `01-procedural` | `.workspace/02-cpp98-systems/object-model/command-service/01-procedural/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/01-procedural` | `reference/` → 2 |
| 2 | doc 02 수명·소유권 | 선택 black-box oracle | `02-value-ownership` | `.workspace/02-cpp98-systems/object-model/command-service/02-value-ownership/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/02-value-ownership` | `reference/` → 3 |
| 3 | doc 03 책임 | legacy 시작점 | `03-responsibilities` | `.workspace/02-cpp98-systems/object-model/command-service/03-responsibilities/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/03-responsibilities` | `reference/` → 4 |
| 4 | doc 04 다형성 | 선택 black-box oracle | `04-polymorphism` | `.workspace/02-cpp98-systems/object-model/command-service/04-polymorphism/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/04-polymorphism` | `reference/` → 5 |
| 5 | doc 05 오류 | 선택 black-box oracle | `05-errors` | `.workspace/02-cpp98-systems/object-model/command-service/05-errors/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=object-model/command-service/05-errors` | `reference/` → 6 |
| 6 | doc 06 템플릿·반복자·STL | template-array demo | template-array; mini-vector는 선택 심화 | `.workspace/02-cpp98-systems/generic-programming/<exercise>/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=generic-programming/<exercise>` | 각 `reference/` → 7 |
| 7 | doc 07 STL 문제 해결 | 세 선택 black-box oracle | date-lookup → rpn → sorter | `.workspace/02-cpp98-systems/generic-programming/stl-problems/<problem>/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=generic-programming/stl-problems/<problem>` | 각 `reference/` → 8 |
| 8 | doc 08 POSIX socket·event loop | 선택 black-box line server | line-server | `.workspace/02-cpp98-systems/networking/line-server/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=networking/line-server` | `reference/` → 9 |
| 9 | doc 09 객체지향 HTTP 서버 | parser/router demo와 선택 black-box oracle | HTTP 01 → 02 → 03 → 04 → 05 | `.workspace/02-cpp98-systems/networking/http-server/<stage>/skeleton/` | `make cpp98-exercise-test CPP98_EXERCISE=networking/http-server/<stage>` | 각 `reference/`, 05 뒤 종료 |

## 개별 피드백

저장소 루트에서 C++98 트랙만 빠르게 검사할 수 있다.

```sh
make skeleton-build
make test
make failure-check
make sanitize
make cpp98-verify
```

- `skeleton-build`: 제공된 출발점과 공개 build graph가 유효한지 확인한다.
- `test`: reference의 정상 계약을 검사한다.
- `failure-check`: 복사·할당·commit 실패, compile-fail, 비가상 소멸, FD 누수와 HTTP 실패 경로를 검사한다.
- `sanitize`: 지원 compiler에서 C++98 reference를 ASan·UBSan으로 검사한다.

개별 target은 수정 중 빠른 피드백을 위한 도구다. 최종 저장소 완료 판정은 루트의 단일 진입점을 사용한다.

```sh
./verify.sh
```

`verify.sh`는 임시 복사본에서 C++98 skeleton build, reference, 실패 주입, line server 부하, 지원되는 sanitizer와 정리 상태를 함께 확인한다. 성공·실패·중단 여부와 관계없이 검증 중 생성한 실행 파일, object, dependency 파일과 Python cache를 제거한다.
