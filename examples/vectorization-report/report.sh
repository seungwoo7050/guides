#!/bin/sh
set -eu

cc=${CC:-cc}
mkdir -p build
version=$($cc --version 2>/dev/null | head -n 1 || true)
printf '컴파일러: %s\n' "$version"

macros=$($cc -dM -E - </dev/null 2>/dev/null || true)
if printf '%s\n' "$macros" | grep -q '__clang__'; then
  "$cc" -O3 -std=c11 -Wall -Wextra -Werror -pedantic \
    -Rpass=loop-vectorize -Rpass-missed=loop-vectorize \
    vector_sum.c -lm -o build/vector_sum 2>build/vectorization.txt
  cat build/vectorization.txt
elif printf '%s\n' "$macros" | grep -q '__GNUC__'; then
  "$cc" -O3 -std=c11 -Wall -Wextra -Werror -pedantic \
    -fopt-info-vec-all \
    vector_sum.c -lm -o build/vector_sum 2>build/vectorization.txt
  cat build/vectorization.txt
else
  printf '%s\n' '이 컴파일러에 맞는 벡터화 보고서 옵션을 설정하지 않았습니다.'
  "$cc" -O3 -std=c11 -Wall -Wextra -Werror -pedantic \
    vector_sum.c -lm -o build/vector_sum
fi
./build/vector_sum
