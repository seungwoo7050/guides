# C++ 학습 로드맵

## 목표

이 문서는 저장소 전체 학습 순서와 두 C++ 트랙의 경계를 먼저 고정하기 위한 초기 roadmap입니다.

## Track A — Modern C++

C++20을 기준으로 다음 순서로 확장합니다.

1. program, build, CMake target
2. value, lifetime, copy, move
3. RAII와 resource ownership
4. class responsibility와 polymorphism
5. error model과 `optional`·`variant`
6. algorithms, ranges, templates, concepts
7. concurrency, time, filesystem
8. testing, debugging, tooling
9. local job runner capstone

독립 project는 strong value model, file owner, query pipeline과 local job runner로 연결할 예정입니다.

## Track B — C++98 systems

C++98과 POSIX 환경을 기준으로 다음 순서로 확장합니다.

1. program과 type model
2. lifetime, value, ownership
3. object responsibility
4. inheritance와 polymorphism
5. error, validation, casts
6. templates, iterators, STL
7. STL 기반 문제 해결
8. POSIX socket과 event loop
9. object-oriented HTTP server

독립 project는 command service, generic container/algorithm project, line server와 HTTP server로 연결할 예정입니다.

## 공통 원칙

- Modern C++의 기본 설계를 C++98에 억지로 복제하지 않습니다.
- C++98의 직접 resource management를 Modern C++의 기본값으로 제시하지 않습니다.
- 모든 project는 ownership, failure boundary, validation과 test contract를 명시합니다.
