# 누적 C++20 renderer project

이 프로젝트는 실습 01–08이 공유하는 공개 CLI, starter/reference 선택과 fixture를 제공합니다.

```sh
cmake -S exercises/08-renderer-capstone/project -B build/reference \
  -DCG_IMPLEMENTATION=reference -DCG_GPU=auto
cmake --build build/reference
ctest --test-dir build/reference --output-on-failure
```

`CG_GPU=off`는 CPU와 lifecycle simulator만 구성하고, `required`는 SDL3를 찾지 못하면 configure 단계에서 실패합니다. learner `workspace/`는 `scripts/new-workspace.sh`로 한 번 생성하며 build나 검증이 삭제하지 않습니다.
