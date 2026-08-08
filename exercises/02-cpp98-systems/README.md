# C++98 시스템 실습

이 디렉터리는 [`docs/02-cpp98-systems`](../../docs/02-cpp98-systems/00-roadmap.md)의 객체·STL·POSIX 네트워크 과정과 대응한다. 모든 실습은 `-std=c++98` 제약을 유지하며, Modern C++ 실습과 같은 구현 방식을 억지로 흉내 내지 않는다.

## 시작하기 전에

새 checkout 또는 overlay 적용 뒤에는 저장소 루트에서 먼저 준비한다.

```sh
./prepare.sh
```

`prepare.sh`는 이동 전 경로와 이전 빌드 부산물을 정리하고, compiler·Make·CMake·Python 및 POSIX 실행 조건을 확인한다. 소스 구현이나 정답 코드를 자동으로 변경하지 않는다.

## 진행 순서

1. [객체 모델과 명령 서비스](object-model/command-service/01-procedural/README.md)
2. [템플릿과 고정 크기 배열](generic-programming/template-array/README.md)
3. [직접 구현하는 작은 vector](generic-programming/mini-vector/README.md)
4. [STL 문제 해결](generic-programming/stl-problems/README.md)
5. [논블로킹 line server](networking/line-server/README.md)
6. [단계형 HTTP 서버](networking/http-server/README.md)

가능한 실습은 `skeleton`과 `reference`를 분리한다. 해당 README의 계약을 읽고 skeleton을 먼저 구현한 뒤 공개 검사를 실행한다. reference는 자신의 구현과 검증을 마친 뒤 책임 배치, 실패 후 상태와 자원 정리 방식을 비교하는 정본이다.

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
