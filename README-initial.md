# C++ 개발 가이드

이 저장소는 목적이 다른 C++ 개발 환경을 두 트랙으로 나누어 정리합니다.

- **Modern C++**: C++20, CMake, 값 의미론, RAII, 표준 라이브러리와 동시성을 사용해 일반 애플리케이션을 구성합니다.
- **C++98 systems**: C++98 제약 아래 객체 수명, STL, POSIX socket, event loop와 HTTP server를 직접 설계합니다.

두 트랙 모두 문법 암기보다 다음 항목을 중심으로 다룹니다.

- 값과 자원의 ownership
- 객체와 resource lifetime
- 실패 시 보존해야 하는 invariant
- component responsibility와 public contract
- build와 test를 포함한 독립적인 project boundary

최종 저장소는 다음 구조를 목표로 합니다.

```text
README.md
docs/
exercises/
.gitignore
```

`docs/`는 개념과 설계를 설명하고, `exercises/`는 독립적으로 build·run·test할 수 있는 completed project를 제공합니다.
